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
