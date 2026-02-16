from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from telegram import Update
from telegram.error import TimedOut, NetworkError
from config import get_settings, Settings
from database import get_database, Database
import logging
import asyncio
import time
from datetime import datetime, timedelta

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Bot applications for both environments
_sandbox_app = None
_production_app = None
_bot_loading = False
_bot_lock = asyncio.Lock()
_current_environment = None

# Local cache for recent updates (in addition to MongoDB)
_local_update_cache = {}
_LOCAL_CACHE_SIZE = 500


async def _get_current_environment(db=None) -> str:
    """Get current environment from database settings"""
    try:
        if db is None:
            db = Database.db
        if db is None:
            return "production"
        
        config = await db.api_config.find_one({"_id": "api_config"})
        if config:
            return config.get("environment", "production")
        return "production"
    except Exception as e:
        logger.error(f"Error getting environment: {e}")
        return "production"


async def _load_bot_for_environment(environment: str):
    """Load bot application for specific environment"""
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
    """Get bot app for current environment from DB setting"""
    global _sandbox_app, _production_app, _current_environment
    
    environment = await _get_current_environment(db)
    
    if _current_environment != environment:
        logger.warning(f"[BOT] Environment changed: {_current_environment} -> {environment}")
        _current_environment = environment
    
    if environment == "production":
        if _production_app is None:
            await _load_bot_for_environment("production")
        return _production_app
    else:
        if _sandbox_app is None:
            await _load_bot_for_environment("sandbox")
        return _sandbox_app


async def _is_duplicate_update(update_id: int, db) -> bool:
    """
    Check if update was already processed - ATOMIC operation for multi-pod sync
    Uses find_one_and_update with upsert for atomicity
    """
    global _local_update_cache
    
    current_time = time.time()
    
    # Check local cache first (fast path)
    if update_id in _local_update_cache:
        return True
    
    # Clean local cache if too large
    if len(_local_update_cache) > _LOCAL_CACHE_SIZE:
        cutoff = current_time - 60
        _local_update_cache = {
            uid: ts for uid, ts in _local_update_cache.items() 
            if ts > cutoff
        }
    
    # ATOMIC check-and-insert using find_one_and_update
    try:
        result = await db.telegram_updates.find_one_and_update(
            {"_id": update_id},
            {
                "$setOnInsert": {
                    "_id": update_id,
                    "processed_at": datetime.utcnow()
                }
            },
            upsert=True,
            return_document=False  # Returns None if document was just created
        )
        
        # Add to local cache
        _local_update_cache[update_id] = current_time
        
        # If result is not None, document existed = duplicate
        if result is not None:
            return True
        
        # Document was just created = not duplicate
        return False
        
    except Exception as e:
        logger.error(f"[DEDUP] Error: {e}")
        # On any error, check local cache one more time
        return update_id in _local_update_cache


async def _cleanup_old_updates(db):
    """Cleanup old update records (run periodically)"""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=1)
        result = await db.telegram_updates.delete_many({
            "processed_at": {"$lt": cutoff}
        })
        if result.deleted_count > 0:
            logger.info(f"[DEDUP] Cleaned up {result.deleted_count} old update records")
    except Exception as e:
        logger.error(f"[DEDUP] Cleanup error: {e}")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Webhook handler - responds immediately to Telegram
    Uses MongoDB for update deduplication across pods
    """
    try:
        update_data = await request.json()
        update_id = update_data.get("update_id")
        
        # Log incoming update for debugging
        message = update_data.get("message", {})
        callback = update_data.get("callback_query", {})
        user_id = message.get("from", {}).get("id") or callback.get("from", {}).get("id")
        text = message.get("text", "")[:50] if message else ""
        callback_data = callback.get("data", "") if callback else ""
        
        logger.warning(f"[WEBHOOK] update_id={update_id}, user={user_id}, text='{text}', callback='{callback_data}'")
        
        # Deduplicate updates using MongoDB (multi-pod safe)
        if update_id and await _is_duplicate_update(update_id, db):
            logger.warning(f"[WEBHOOK] Duplicate update {update_id}, skipping")
            return JSONResponse(content={"status": "ok"})
        
        # Get bot application for current environment
        app = await _get_bot_app(db)
        
        if app is None:
            logger.error("[BOT] No bot application available")
            return JSONResponse(content={"status": "error", "message": "Bot not loaded"})
        
        # Process update
        update = Update.de_json(update_data, app.bot)
        logger.warning(f"[WEBHOOK] Processing update {update_id}...")
        await app.process_update(update)
        logger.warning(f"[WEBHOOK] Update {update_id} processed")
        
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
            logger.warning("[BOT] Database not ready, skipping preload")
            return
        
        environment = await _get_current_environment(db)
        await _load_bot_for_environment(environment)
        logger.warning(f"[BOT] Bot application preloaded successfully for {environment}")
    except Exception as e:
        logger.error(f"[BOT] Preload failed: {e}")


@router.get("/preload")
async def preload_bot(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Endpoint to trigger bot preloading for current environment"""
    environment = await _get_current_environment(db)
    await _load_bot_for_environment(environment)
    
    # Cleanup old updates periodically
    asyncio.create_task(_cleanup_old_updates(db))
    
    return {
        "status": "ok", 
        "environment": environment,
        "sandbox_loaded": _sandbox_app is not None,
        "production_loaded": _production_app is not None
    }


@router.get("/status")
async def bot_status(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get current bot status and environment"""
    environment = await _get_current_environment(db)
    
    return {
        "current_environment": environment,
        "sandbox_loaded": _sandbox_app is not None,
        "production_loaded": _production_app is not None
    }
