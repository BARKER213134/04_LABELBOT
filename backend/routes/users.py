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
        from services.localization import get_user_language
        
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        new_balance = user.get('balance', 0)
        
        # Get user language from telegram_users collection (where it's stored)
        db = Database.db
        lang = await get_user_language(db, update.telegram_id)
        
        # Check if user is actively waiting for balance to continue order
        pending_label = await db.pending_label_orders.find_one({
            "telegram_id": update.telegram_id,
            "waiting_for_balance": True
        })
        is_creating_label = pending_label is not None
        
        # DON'T delete pending order here - it will be deleted when user clicks "Continue order"
        
        if update.amount > 0:
            # Balance added
            if lang == "en":
                reason_text = update.reason or 'Balance top-up'
                message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💰 *BALANCE TOPPED UP*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"▫️ Amount: *+${update.amount:.2f}*\n"
                    f"▫️ Reason: {reason_text}\n\n"
                    f"▫️ Was: ${old_balance:.2f}\n"
                    f"▫️ Now: *${new_balance:.2f}*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
                continue_btn = "📦 Continue Order"
                menu_btn = "🏠 Main Menu"
            else:
                reason_text = update.reason or 'Пополнение баланса'
                message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💰 *БАЛАНС ПОПОЛНЕН*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"▫️ Сумма: *+${update.amount:.2f}*\n"
                    f"▫️ Причина: {reason_text}\n\n"
                    f"▫️ Было: ${old_balance:.2f}\n"
                    f"▫️ Стало: *${new_balance:.2f}*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
                continue_btn = "📦 Продолжить заказ"
                menu_btn = "🏠 Главное меню"
            
            # Show "Continue order" button ONLY if user is actively creating a label
            if is_creating_label:
                keyboard = [
                    [InlineKeyboardButton(continue_btn, callback_data="create_label")],
                    [InlineKeyboardButton(menu_btn, callback_data="back_to_menu")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton(menu_btn, callback_data="back_to_menu")]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            # Balance deducted
            if lang == "en":
                reason_text = update.reason or 'Balance deduction'
                message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💸 *BALANCE DEDUCTED*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"▫️ Amount: *-${abs(update.amount):.2f}*\n"
                    f"▫️ Reason: {reason_text}\n\n"
                    f"▫️ Was: ${old_balance:.2f}\n"
                    f"▫️ Now: *${new_balance:.2f}*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
                menu_btn = "🏠 Main Menu"
            else:
                reason_text = update.reason or 'Списание средств'
                message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💸 *СПИСАНИЕ СРЕДСТВ*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"▫️ Сумма: *-${abs(update.amount):.2f}*\n"
                    f"▫️ Причина: {reason_text}\n\n"
                    f"▫️ Было: ${old_balance:.2f}\n"
                    f"▫️ Стало: *${new_balance:.2f}*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
                menu_btn = "🏠 Главное меню"
            
            keyboard = [
                [InlineKeyboardButton(menu_btn, callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=int(update.telegram_id),
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.warning(f"[BALANCE] Notification sent to {update.telegram_id}")
    except Exception as e:
        logger.warning(f"[BALANCE] Failed to send notification to {update.telegram_id}: {e}")
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


@router.post("/{telegram_id}/ban")
async def ban_user(
    telegram_id: str,
    service: UsersService = Depends(get_users_service)
):
    """Ban a user and notify them"""
    from telegram import Bot
    from config import get_settings
    
    user = await service.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user status in database
    db = Database.db
    await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"is_banned": True}}
    )
    
    # Send notification to user
    try:
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚫 *АККАУНТ ЗАБЛОКИРОВАН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ваш аккаунт был заблокирован администратором.\n\n"
            "Если вы считаете, что это ошибка, "
            "свяжитесь с поддержкой.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await bot.send_message(
            chat_id=int(telegram_id),
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Ban notification sent to user {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send ban notification: {e}")
    
    return {"status": "success", "message": f"User {telegram_id} banned"}


@router.post("/{telegram_id}/unban")
async def unban_user(
    telegram_id: str,
    service: UsersService = Depends(get_users_service)
):
    """Unban a user and notify them"""
    from telegram import Bot
    from config import get_settings
    
    user = await service.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user status in database
    db = Database.db
    await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"is_banned": False}}
    )
    
    # Send notification to user
    try:
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *АККАУНТ РАЗБЛОКИРОВАН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ваш аккаунт был разблокирован.\n"
            "Вы снова можете пользоваться ботом!\n\n"
            "Нажмите /start чтобы начать.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await bot.send_message(
            chat_id=int(telegram_id),
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Unban notification sent to user {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send unban notification: {e}")
    
    return {"status": "success", "message": f"User {telegram_id} unbanned"}


@router.delete("/{telegram_id}")
async def delete_user(
    telegram_id: str,
    service: UsersService = Depends(get_users_service)
):
    """Delete a user and notify them"""
    from telegram import Bot
    from config import get_settings
    
    user = await service.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send notification before deletion
    try:
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🗑 *АККАУНТ УДАЛЁН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ваш аккаунт был удалён администратором.\n\n"
            "Все данные аккаунта удалены.\n"
            "Нажмите /start чтобы создать новый аккаунт.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await bot.send_message(
            chat_id=int(telegram_id),
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Delete notification sent to user {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send delete notification: {e}")
    
    # Delete user from database
    db = Database.db
    await db.users.delete_one({"telegram_id": telegram_id})
    
    # Also delete user's templates
    await db.templates.delete_many({"user_id": telegram_id})
    
    logger.info(f"User {telegram_id} deleted from database")
    
    return {"status": "success", "message": f"User {telegram_id} deleted"}
