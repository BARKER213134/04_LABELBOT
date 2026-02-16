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
        import traceback
        
        print(f"[BALANCE] Preparing to send notification to {update.telegram_id}")
        
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        new_balance = user.get('balance', 0)
        
        # Check if user has a pending order (waiting for payment)
        db = Database.db
        pending_order = await db.orders.find_one({
            "telegram_user_id": update.telegram_id,
            "status": "pending"
        })
        
        print(f"[BALANCE] Has pending order: {bool(pending_order)}")
        
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
            # Show "Continue order" button ONLY if user has pending order
            if pending_order:
                keyboard = [
                    [InlineKeyboardButton("📦 Продолжить заказ", callback_data="create_label")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
                ]
            else:
                keyboard = [
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
        
        print(f"[BALANCE] Sending message to chat_id={update.telegram_id}")
        
        result = await bot.send_message(
            chat_id=int(update.telegram_id),
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        print(f"[BALANCE] Notification sent successfully to {update.telegram_id}, message_id={result.message_id}")
    except Exception as e:
        print(f"[BALANCE] Failed to send notification: {e}")
        print(f"[BALANCE] Full traceback: {traceback.format_exc()}")
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
