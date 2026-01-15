from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from database import Database
from services.users_service import UsersService
from services.telegram_service import TelegramService
from models.user import UserBalanceUpdate, UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def get_users_service():
    return UsersService(Database.db)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_users(service: UsersService = Depends(get_users_service)):
    """Get all users"""
    users = await service.get_all_users()
    return users


@router.get("/{telegram_id}", response_model=Dict[str, Any])
async def get_user(
    telegram_id: str,
    service: UsersService = Depends(get_users_service)
):
    """Get user by telegram_id"""
    user = await service.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/balance", response_model=Dict[str, Any])
async def update_balance(
    update: UserBalanceUpdate,
    service: UsersService = Depends(get_users_service)
):
    """Update user balance (add or subtract)"""
    # Get user before update to check old balance
    old_user = await service.get_user(update.telegram_id)
    old_balance = old_user.get('balance', 0) if old_user else 0
    
    user = await service.update_balance(
        telegram_id=update.telegram_id,
        amount=update.amount,
        reason=update.reason
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send Telegram notification
    try:
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        from config import get_settings
        
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        new_balance = user.get('balance', 0)
        
        if update.amount > 0:
            # Balance added
            message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💰 *БАЛАНС ПОПОЛНЕН*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"▫️ Сумма: *+${update.amount:.2f}*\n"
                f"▫️ Причина: {update.reason or 'Пополнение баланса'}\n\n"
                f"▫️ Было: ${old_balance:.2f}\n"
                f"▫️ Стало: *${new_balance:.2f}*\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            # Add buttons for balance top-up
            keyboard = [
                [InlineKeyboardButton("📦 Продолжить заказ", callback_data="create_label")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            # Balance deducted
            message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💸 *СПИСАНИЕ СРЕДСТВ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"▫️ Сумма: *-${abs(update.amount):.2f}*\n"
                f"▫️ Причина: {update.reason or 'Списание средств'}\n\n"
                f"▫️ Было: ${old_balance:.2f}\n"
                f"▫️ Стало: *${new_balance:.2f}*\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=int(update.telegram_id),
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info(f"Balance notification sent to {update.telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send balance notification: {e}")
        # Don't fail the request if notification fails
    
    return user


@router.get("/{telegram_id}/balance-history", response_model=List[Dict[str, Any]])
async def get_balance_history(
    telegram_id: str,
    limit: int = 50,
    service: UsersService = Depends(get_users_service)
):
    """Get balance change history for a user"""
    history = await service.get_balance_history(telegram_id, limit)
    return history
