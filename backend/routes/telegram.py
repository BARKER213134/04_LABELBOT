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

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Bot applications for both environments
_sandbox_app = None
_production_app = None
_bot_loading = False
_bot_lock = asyncio.Lock()
_current_environment = None

# Deduplication cache for processed update IDs (last 1000 updates)
_processed_updates = {}
_MAX_CACHED_UPDATES = 1000


async def _get_current_environment(db=None) -> str:
    """Get current environment from database settings"""
    try:
        if db is None:
            db = Database.db
        if db is None:
            return "production"  # Default to production
        
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
    
    # Log environment change
    if _current_environment != environment:
        logger.warning(f"[BOT] Environment changed: {_current_environment} -> {environment}")
        _current_environment = environment
    
    # Return cached app or load new one
    if environment == "production":
        if _production_app is None:
            await _load_bot_for_environment("production")
        return _production_app
    else:
        if _sandbox_app is None:
            await _load_bot_for_environment("sandbox")
        return _sandbox_app


def _is_duplicate_update(update_id: int) -> bool:
    """Check if update was already processed (deduplication)"""
    global _processed_updates
    
    current_time = time.time()
    
    # Cleanup old entries (older than 5 minutes)
    if len(_processed_updates) > _MAX_CACHED_UPDATES:
        cutoff = current_time - 300  # 5 minutes
        _processed_updates = {
            uid: ts for uid, ts in _processed_updates.items() 
            if ts > cutoff
        }
    
    # Check if already processed
    if update_id in _processed_updates:
        return True
    
    # Mark as processed
    _processed_updates[update_id] = current_time
    return False


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Webhook handler - responds immediately to Telegram
    Dynamically uses environment from DB settings
    """
    try:
        update_data = await request.json()
        update_id = update_data.get("update_id")
        
        # Deduplicate updates FIRST - before any processing
        if update_id and _is_duplicate_update(update_id):
            return JSONResponse(content={"status": "ok"})
        
        # Get bot application for current environment (reads from DB)
        app = await _get_bot_app(db)
        
        if app is None:
            logger.error("[BOT] No bot application available")
            return JSONResponse(content={"status": "error", "message": "Bot not loaded"})
        
        # Process update
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
    
    except (TimedOut, NetworkError):
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(content={"status": "ok"})


@router.get("/preload")
async def preload_bot(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Endpoint to trigger bot preloading for current environment"""
    environment = await _get_current_environment(db)
    await _load_bot_for_environment(environment)
    
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
