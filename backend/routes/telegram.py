from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from telegram import Update
from services.telegram_service import TelegramService
from config import get_settings, Settings
from database import get_database
from datetime import datetime
import logging
import json

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# Store user session data
user_sessions = {}

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Webhook handler for Telegram bot (Sandbox)
    """
    return await handle_telegram_update(request, db, use_production=False)

@router.post("/webhook-prod")
async def telegram_webhook_prod(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Webhook handler for Telegram bot (Production)
    """
    return await handle_telegram_update(request, db, use_production=True)

async def handle_telegram_update(
    request: Request,
    db: AsyncIOMotorDatabase,
    use_production: bool = False
):
    """
    Handle Telegram webhook update
    """
    try:
        update_data = await request.json()
        bot_type = "PRODUCTION" if use_production else "SANDBOX"
        logger.info(f"[{bot_type}] Received webhook: {json.dumps(update_data)}")
        
        telegram_service = TelegramService(use_production=use_production)
        
        # Handle message
        if "message" in update_data:
            message = update_data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user_id = str(message["from"]["id"])
            username = message["from"].get("username", "unknown")
            
            # Update user in database
            await db.telegram_users.update_one(
                {"telegram_id": user_id},
                {
                    "$set": {
                        "telegram_id": user_id,
                        "username": username,
                        "first_name": message["from"].get("first_name"),
                        "last_name": message["from"].get("last_name"),
                        "last_interaction": datetime.utcnow().isoformat()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow().isoformat(),
                        "total_orders": 0
                    }
                },
                upsert=True
            )
            
            # Handle commands
            if text == "/start":
                await telegram_service.send_welcome_message(chat_id)
            elif text == "/create":
                await telegram_service.send_carrier_selection(chat_id)
                user_sessions[user_id] = {"step": "carrier", "data": {}}
            elif text == "/help":
                help_text = (
                    "📚 *Команды:*\n\n"
                    "/create \\- Создать новый лейбл\n"
                    "/help \\- Помощь"
                )
                await telegram_service.bot.send_message(
                    chat_id=chat_id,
                    text=help_text,
                    parse_mode="MarkdownV2"
                )
        
        # Handle callback queries (button clicks)
        elif "callback_query" in update_data:
            callback = update_data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            data = callback["data"]
            user_id = str(callback["from"]["id"])
            
            if data.startswith("carrier_"):
                carrier = data.replace("carrier_", "")
                if user_id in user_sessions:
                    user_sessions[user_id]["data"]["carrier"] = carrier
                    
                    await telegram_service.bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ Выбран: {carrier.upper()}\n\nДля завершения создания лейбла, перейдите в веб-дашборд или используйте API"
                    )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/send-label-notification")
async def send_label_notification(
    order_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Send label creation notification to Telegram user
    """
    try:
        telegram_service = TelegramService()
        telegram_user_id = order_data.get("telegram_user_id")
        
        if telegram_user_id:
            await telegram_service.send_label_created(
                chat_id=int(telegram_user_id),
                order_data=order_data
            )
            return {"success": True, "message": "Notification sent"}
        
        return {"success": False, "message": "No Telegram user ID"}
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {"success": False, "error": str(e)}