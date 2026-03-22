from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from telegram import Update
from telegram.error import TimedOut, NetworkError
from config import get_settings, Settings
from database import get_database, Database
from services.security import (
    webhook_limiter, validate_telegram_webhook, 
    get_telegram_user_id, get_client_ip
)
import logging
import asyncio
import time
from datetime import datetime, timedelta

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Bot applications - cached globally
_sandbox_app = None
_production_app = None
_bot_loading = False
_bot_lock = asyncio.Lock()

# Environment cache
_cached_environment = None
_environment_cache_time = 0
_ENVIRONMENT_CACHE_TTL = 60

# Deduplication
_local_update_cache = {}
_LOCAL_CACHE_SIZE = 2000
_LOCAL_CACHE_TTL = 300

# Blocked IPs (for severe abuse)
_blocked_ips = set()

# Background tasks set (prevents garbage collection)
_processing_tasks = set()


def _is_duplicate_local(update_id: int) -> bool:
    """Fast local-only deduplication check"""
    global _local_update_cache
    
    current_time = time.time()
    
    if update_id in _local_update_cache:
        return True
    
    if len(_local_update_cache) > _LOCAL_CACHE_SIZE:
        cutoff = current_time - _LOCAL_CACHE_TTL
        _local_update_cache = {
            uid: ts for uid, ts in _local_update_cache.items() 
            if ts > cutoff
        }
    
    _local_update_cache[update_id] = current_time
    return False


async def _mark_update_processed(update_id: int, db):
    """Mark update as processed in MongoDB"""
    try:
        await db.telegram_updates.update_one(
            {"_id": update_id},
            {"$setOnInsert": {"_id": update_id, "processed_at": datetime.utcnow()}},
            upsert=True
        )
    except:
        pass


async def _get_current_environment_cached(db=None) -> str:
    """Get environment with caching"""
    global _cached_environment, _environment_cache_time
    
    current_time = time.time()
    
    if _cached_environment and (current_time - _environment_cache_time) < _ENVIRONMENT_CACHE_TTL:
        return _cached_environment
    
    try:
        if db is None:
            db = Database.db
        if db is None:
            return _cached_environment or "production"
        
        config = await db.api_config.find_one({"_id": "api_config"})
        _cached_environment = config.get("environment", "production") if config else "production"
        _environment_cache_time = current_time
        return _cached_environment
        
    except:
        return _cached_environment or "production"


async def _load_bot_for_environment(environment: str):
    """Load bot application"""
    global _sandbox_app, _production_app, _bot_loading
    
    async with _bot_lock:
        if _bot_loading:
            return
        
        _bot_loading = True
        try:
            from telegram_bot_app import get_or_create_app
            
            if environment == "production" and _production_app is None:
                logger.warning("[BOT] Loading production bot...")
                _production_app = await get_or_create_app("production")
                logger.warning("[BOT] Production bot loaded")
            elif environment == "sandbox" and _sandbox_app is None:
                logger.warning("[BOT] Loading sandbox bot...")
                _sandbox_app = await get_or_create_app("sandbox")
                logger.warning("[BOT] Sandbox bot loaded")
        except Exception as e:
            logger.error(f"[BOT] Failed to load {environment} bot: {e}")
        finally:
            _bot_loading = False


async def _get_bot_app(db=None):
    """Get bot app"""
    global _sandbox_app, _production_app
    
    environment = await _get_current_environment_cached(db)
    
    if environment == "production":
        if _production_app is None:
            await _load_bot_for_environment("production")
        return _production_app
    else:
        if _sandbox_app is None:
            await _load_bot_for_environment("sandbox")
        return _sandbox_app


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Secure webhook handler with:
    - Maintenance mode check
    - Rate limiting per user
    - Telegram update validation
    - Fast deduplication
    """
    try:
        # Get client IP for rate limiting fallback
        client_ip = get_client_ip(request)
        
        # Block known bad IPs
        if client_ip in _blocked_ips:
            return JSONResponse(content={"status": "ok"})
        
        update_data = await request.json()
        
        # Check maintenance mode
        from routes.admin import get_maintenance_mode, get_maintenance_whitelist
        is_maintenance = await get_maintenance_mode(db)
        
        if is_maintenance:
            # Check if user is in whitelist
            user_id = None
            username = None
            if "message" in update_data:
                user_id = update_data["message"].get("from", {}).get("id")
                username = update_data["message"].get("from", {}).get("username")
            elif "callback_query" in update_data:
                user_id = update_data["callback_query"].get("from", {}).get("id")
                username = update_data["callback_query"].get("from", {}).get("username")
            
            # Check whitelist - allow admins and whitelisted users
            whitelist = await get_maintenance_whitelist(db)
            admin_id = settings.admin_telegram_id if hasattr(settings, 'admin_telegram_id') else None
            
            is_whitelisted = False
            if user_id:
                if str(user_id) in whitelist or str(user_id) == str(admin_id):
                    is_whitelisted = True
            if username:
                if username.lower() in [u.lower() for u in whitelist]:
                    is_whitelisted = True
            
            if not is_whitelisted and user_id:
                try:
                    from telegram import Bot
                    from services.localization import get_user_language
                    
                    bot = Bot(token=settings.telegram_bot_token_prod)
                    
                    # Get user language
                    lang = await get_user_language(db, str(user_id))
                    
                    if lang == "en":
                        text = "🔧 *Bot is under maintenance*\n\nPlease wait. We'll be back soon!"
                    else:
                        text = "🔧 *Бот на техническом обслуживании*\n\nПожалуйста, подождите. Мы скоро вернёмся!"
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                return JSONResponse(content={"status": "ok"})
        
        # Validate Telegram update structure
        if not validate_telegram_webhook(settings.telegram_bot_token_prod, update_data):
            logger.warning(f"[SECURITY] Invalid webhook from {client_ip}")
            return JSONResponse(content={"status": "ok"})
        
        update_id = update_data.get("update_id")
        
        # Get user ID for rate limiting
        user_id = get_telegram_user_id(update_data)
        rate_limit_key = f"tg_{user_id}" if user_id != "unknown" else f"ip_{client_ip}"
        
        # Rate limiting (120 requests/minute per user)
        allowed, remaining = webhook_limiter.is_allowed(rate_limit_key)
        if not allowed:
            logger.warning(f"[SECURITY] Rate limit exceeded: {rate_limit_key}")
            return JSONResponse(content={"status": "ok"})
        
        # Deduplication
        if update_id and _is_duplicate_local(update_id):
            return JSONResponse(content={"status": "ok"})
        
        # Get bot application
        app = await _get_bot_app(db)
        
        if app is None:
            return JSONResponse(content={"status": "ok"})
        
        # Fire-and-forget: process update in background task
        # This ensures webhook returns instantly so K8s health checks never time out
        update = Update.de_json(update_data, app.bot)
        
        # Capture bot_app in a local variable to avoid closure issues
        bot_app = app
        
        async def _process_in_background(ba, upd, upd_id):
            try:
                await ba.process_update(upd)
            except (TimedOut, NetworkError):
                pass
            except Exception as e:
                logger.error(f"[WEBHOOK] BG error for update {upd_id}: {e}")
            finally:
                if upd_id:
                    try:
                        await _mark_update_processed(upd_id, Database.db)
                    except Exception:
                        pass
        
        task = asyncio.create_task(_process_in_background(bot_app, update, update_id))
        _processing_tasks.add(task)
        task.add_done_callback(_processing_tasks.discard)
        
        return JSONResponse(content={"status": "ok"})
    
    except (TimedOut, NetworkError):
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(content={"status": "ok"})


async def _preload_bot():
    """Preload bot during server startup"""
    try:
        db = Database.db
        if db is None:
            return
        
        environment = await _get_current_environment_cached(db)
        await _load_bot_for_environment(environment)
        logger.warning(f"[BOT] Bot preloaded for {environment}")
    except Exception as e:
        logger.error(f"[BOT] Preload failed: {e}")


@router.get("/preload")
async def preload_bot(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Preload bot endpoint"""
    environment = await _get_current_environment_cached(db)
    await _load_bot_for_environment(environment)
    
    return {
        "status": "ok", 
        "environment": environment,
        "sandbox_loaded": _sandbox_app is not None,
        "production_loaded": _production_app is not None
    }


@router.get("/status")
async def bot_status(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Bot status"""
    environment = await _get_current_environment_cached(db)
    
    return {
        "current_environment": environment,
        "sandbox_loaded": _sandbox_app is not None,
        "production_loaded": _production_app is not None,
        "cache_size": len(_local_update_cache)
    }


@router.post("/clear-env-cache")
async def clear_environment_cache():
    """Clear environment cache"""
    global _cached_environment, _environment_cache_time
    _cached_environment = None
    _environment_cache_time = 0
    return {"status": "ok"}
