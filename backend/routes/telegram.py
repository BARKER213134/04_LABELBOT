from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from telegram import Update
from telegram.error import TimedOut, NetworkError
from config import get_settings, Settings
from database import get_database
import logging
import asyncio
import time

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Pre-loaded bot application
_cached_bot_app = None
_bot_loading = False

# Deduplication cache for processed update IDs (last 1000 updates)
_processed_updates = {}
_MAX_CACHED_UPDATES = 1000

async def _preload_bot():
    """Preload bot application in background"""
    global _cached_bot_app, _bot_loading
    if _cached_bot_app is None and not _bot_loading:
        _bot_loading = True
        try:
            from telegram_bot_app import get_or_create_app
            _cached_bot_app = await get_or_create_app("production")
            logger.info("Bot application preloaded")
        except Exception as e:
            logger.error(f"Failed to preload bot: {e}")
        finally:
            _bot_loading = False

async def _get_bot_app():
    """Get cached bot app or load it"""
    global _cached_bot_app
    if _cached_bot_app is None:
        from telegram_bot_app import get_or_create_app
        _cached_bot_app = await get_or_create_app("production")
    return _cached_bot_app

# Start preloading bot in background when module loads
def _start_preload():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_preload_bot())
    except:
        pass

_start_preload()


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
    Unified webhook handler for Telegram bot
    Processes synchronously to maintain conversation state
    """
    try:
        update_data = await request.json()
        update_id = update_data.get("update_id")
        
        # Deduplicate updates - Telegram may retry if response is slow
        if update_id and _is_duplicate_update(update_id):
            logger.debug(f"Duplicate update {update_id} ignored")
            return JSONResponse(content={"status": "ok"})
        
        # Get cached bot application
        app = await _get_bot_app()
        
        # Process update synchronously to maintain conversation state
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
    
    except (TimedOut, NetworkError) as e:
        logger.warning(f"Telegram timeout: {e}")
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(content={"status": "ok", "error": str(e)})


@router.get("/preload")
async def preload_bot():
    """Endpoint to trigger bot preloading"""
    await _preload_bot()
    return {"status": "ok", "bot_loaded": _cached_bot_app is not None}
