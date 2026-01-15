"""
Broadcast routes for mass messaging to Telegram users
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import Database
from telegram import Bot
from config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/broadcast", tags=["broadcast"])

class BroadcastMessage(BaseModel):
    message: str
    parse_mode: Optional[str] = "HTML"  # HTML or Markdown
    include_button: Optional[bool] = False
    button_text: Optional[str] = None
    button_url: Optional[str] = None

class BroadcastResult(BaseModel):
    total_users: int
    sent: int
    failed: int
    failed_users: List[str]

@router.post("/send", response_model=BroadcastResult)
async def send_broadcast(broadcast: BroadcastMessage):
    """Send broadcast message to all users"""
    settings = get_settings()
    
    # Get current environment to select correct bot token
    db = Database.db
    settings_doc = await db.settings.find_one({"key": "environment"})
    environment = settings_doc.get("value", "sandbox") if settings_doc else "sandbox"
    
    if environment == "production":
        bot_token = settings.telegram_bot_token_prod
    else:
        bot_token = settings.telegram_bot_token
    
    bot = Bot(token=bot_token)
    
    # Get all users with telegram_id
    users = await db.users.find({"telegram_id": {"$exists": True, "$ne": None}}).to_list(length=10000)
    
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    
    total_users = len(users)
    sent = 0
    failed = 0
    failed_users = []
    
    # Prepare message with optional button
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    reply_markup = None
    if broadcast.include_button and broadcast.button_text and broadcast.button_url:
        keyboard = [[InlineKeyboardButton(broadcast.button_text, url=broadcast.button_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send messages with rate limiting (30 messages per second max for Telegram)
    for user in users:
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=broadcast.message,
                parse_mode=broadcast.parse_mode,
                reply_markup=reply_markup
            )
            sent += 1
            logger.info(f"Broadcast sent to user {telegram_id}")
        except Exception as e:
            failed += 1
            failed_users.append(f"{telegram_id}: {str(e)[:50]}")
            logger.warning(f"Failed to send broadcast to {telegram_id}: {e}")
        
        # Rate limiting: 30 messages per second = ~33ms between messages
        await asyncio.sleep(0.035)
    
    logger.info(f"Broadcast completed: {sent}/{total_users} sent, {failed} failed")
    
    return BroadcastResult(
        total_users=total_users,
        sent=sent,
        failed=failed,
        failed_users=failed_users[:20]  # Limit to first 20 failures
    )

@router.get("/users-count")
async def get_users_count():
    """Get total number of users for broadcast"""
    db = Database.db
    count = await db.users.count_documents({"telegram_id": {"$exists": True, "$ne": None}})
    return {"count": count}
