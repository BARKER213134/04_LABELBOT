from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from telegram import Update
from config import get_settings, Settings
from database import get_database
import logging

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Import bot application
from telegram_bot_app import get_or_create_app

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Unified webhook handler for Telegram bot
    Automatically uses correct bot based on ShipEngine environment
    """
    try:
        update_data = await request.json()
        logger.info(f"Received Telegram webhook")
        
        # Получаем текущий ShipEngine environment из базы данных
        env_config = await db.api_config.find_one({"_id": "api_config"})
        current_env = env_config.get("environment", "sandbox") if env_config else "sandbox"
        
        logger.info(f"Using {current_env.upper()} environment for Telegram bot")
        
        # Get appropriate bot application
        app = await get_or_create_app(current_env)
        
        # Process the update
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
