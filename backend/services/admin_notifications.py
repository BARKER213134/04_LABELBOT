"""
Admin Notifications Service
Sends notifications to admin about important events
"""
import logging
from telegram import Bot
from config import get_settings
from datetime import datetime

logger = logging.getLogger(__name__)

# Admin Telegram ID for notifications
ADMIN_TELEGRAM_ID = "7066790254"

async def notify_admin(message: str):
    """Send notification to admin"""
    try:
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        await bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Admin notification sent")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")


async def notify_new_user(telegram_id: str, username: str = None, first_name: str = None):
    """Notify admin about new user registration"""
    user_info = f"@{username}" if username else first_name or telegram_id
    
    message = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 *НОВЫЙ ПОЛЬЗОВАТЕЛЬ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"▫️ ID: `{telegram_id}`\n"
        f"▫️ Пользователь: {user_info}\n"
        f"▫️ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    await notify_admin(message)


async def notify_label_created(
    telegram_id: str,
    username: str = None,
    tracking_number: str = None,
    carrier: str = None,
    cost: float = 0,
    profit: float = 0
):
    """Notify admin about label creation"""
    user_info = f"@{username}" if username else telegram_id
    
    message = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 *СОЗДАН ЛЕЙБЛ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"▫️ Пользователь: {user_info}\n"
        f"▫️ ID: `{telegram_id}`\n"
        f"▫️ Tracking: `{tracking_number}`\n"
        f"▫️ Перевозчик: {carrier}\n"
        f"▫️ Стоимость: ${cost:.2f}\n"
        f"▫️ Прибыль: *${profit:.2f}*\n"
        f"▫️ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    await notify_admin(message)


async def notify_balance_topup(
    telegram_id: str,
    username: str = None,
    amount: float = 0,
    new_balance: float = 0,
    payment_method: str = "Crypto"
):
    """Notify admin about balance top-up"""
    user_info = f"@{username}" if username else telegram_id
    
    message = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 *ПОПОЛНЕНИЕ БАЛАНСА*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"▫️ Пользователь: {user_info}\n"
        f"▫️ ID: `{telegram_id}`\n"
        f"▫️ Сумма: *+${amount:.2f}*\n"
        f"▫️ Новый баланс: ${new_balance:.2f}\n"
        f"▫️ Метод: {payment_method}\n"
        f"▫️ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    await notify_admin(message)


async def notify_user_error(
    telegram_id: str,
    username: str = None,
    error_type: str = "Ошибка",
    error_message: str = "",
    context: str = ""
):
    """Notify admin about user error"""
    user_info = f"@{username}" if username else telegram_id
    
    # Truncate long error messages
    if len(error_message) > 200:
        error_message = error_message[:200] + "..."
    
    message = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ *{error_type.upper()}*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"▫️ Пользователь: {user_info}\n"
        f"▫️ ID: `{telegram_id}`\n"
    )
    
    if context:
        message += f"▫️ Контекст: {context}\n"
    
    message += (
        f"▫️ Ошибка: `{error_message}`\n"
        f"▫️ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    await notify_admin(message)


# Cache to avoid spamming low balance notifications
_last_low_balance_notification = None

async def notify_low_shipengine_balance(balance: float, threshold: float = 50.0):
    """Notify admin about low ShipEngine balance"""
    global _last_low_balance_notification
    
    # Don't spam - only notify once per hour
    if _last_low_balance_notification:
        time_diff = (datetime.now() - _last_low_balance_notification).total_seconds()
        if time_diff < 3600:  # 1 hour
            return
    
    _last_low_balance_notification = datetime.now()
    
    message = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *НИЗКИЙ БАЛАНС SHIPENGINE*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Текущий баланс: *${balance:.2f}*\n"
        f"📊 Порог: ${threshold:.2f}\n\n"
        "⚡ *Пополните баланс ShipEngine!*\n\n"
        f"▫️ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    await notify_admin(message)


async def check_and_notify_shipengine_balance():
    """Check ShipEngine balance and notify if low"""
    try:
        from services.shipengine_service import ShipEngineService, LOW_BALANCE_THRESHOLD
        from config import get_settings
        from database import Database
        
        settings = get_settings()
        db = Database.db
        
        # Get current environment
        api_config = await db.api_config.find_one({"key": "shipengine_environment"})
        env = api_config.get("value", "sandbox") if api_config else "sandbox"
        
        if env == "production":
            api_key = settings.shipengine_production_key
        else:
            api_key = settings.shipengine_sandbox_key
        
        if not api_key:
            return
        
        service = ShipEngineService(api_key=api_key)
        balance_info = await service.get_account_balance()
        
        if balance_info.get("low_balance"):
            await notify_low_shipengine_balance(
                balance=balance_info.get("balance", 0),
                threshold=LOW_BALANCE_THRESHOLD
            )
    except Exception as e:
        logger.error(f"Failed to check ShipEngine balance: {e}")
