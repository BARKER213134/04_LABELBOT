from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
import logging
from config import get_settings

logger = logging.getLogger(__name__)

class TelegramService:
    """Service for Telegram bot interactions"""
    
    def __init__(self, environment='sandbox'):
        """
        Initialize Telegram service with appropriate bot based on environment
        
        Args:
            environment: 'sandbox' or 'production'
        """
        settings = get_settings()
        # Выбираем токен в зависимости от ShipEngine environment
        if environment == 'production':
            bot_token = settings.telegram_bot_token_prod
            logger.info("Using PRODUCTION Telegram bot")
        else:
            bot_token = settings.telegram_bot_token
            logger.info("Using SANDBOX Telegram bot")
        
        self.bot = Bot(token=bot_token)
        self.environment = environment
    
    async def send_welcome_message(self, chat_id: int, balance: float = None):
        """Send welcome message with instructions"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
        
        balance_text = f"💰 Баланс: *${balance:.2f}*\n\n" if balance is not None else ""
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *WHITE LABEL SHIPPING BOT*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{balance_text}"
            "Создавайте shipping labels для:\n"
            "USPS • FedEx • UPS\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton("📦 Создать Label", callback_data="start_create")],
            [InlineKeyboardButton("📋 Шаблоны", callback_data="templates_menu")],
            [InlineKeyboardButton("💰 Баланс", callback_data="check_balance")],
            [InlineKeyboardButton("↩️ Refund Label", callback_data="refund_info")],
            [InlineKeyboardButton("📖 FAQ", callback_data="faq_info")],
            [InlineKeyboardButton("❓ Помощь", url="https://t.me/White_Label_Shipping_Bot_Agent")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Add persistent keyboard with Main Menu button
        persistent_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("🏠 Главное меню")]],
            resize_keyboard=True,
            is_persistent=True
        )
        
        # First send message to set persistent keyboard
        await self.bot.send_message(
            chat_id=chat_id,
            text="🏠",
            reply_markup=persistent_keyboard
        )
        
        # Delete the temp message
        # Then send welcome with inline buttons
        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def send_carrier_selection(self, chat_id: int):
        """Send carrier selection menu"""
        keyboard = [
            [InlineKeyboardButton("📦 USPS", callback_data="carrier_usps")],
            [InlineKeyboardButton("✈️ FedEx", callback_data="carrier_fedex")],
            [InlineKeyboardButton("🚚 UPS", callback_data="carrier_ups")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=chat_id,
            text="Выберите перевозчика:",
            reply_markup=reply_markup
        )
    
    async def send_label_created(self, chat_id: int, order_data: dict):
        """Send label creation confirmation"""
        text = (
            f"✅ *Лейбл создан успешно\\!*\n\n"
            f"📋 Tracking: `{order_data.get('trackingNumber', 'N/A')}`\n"
            f"💰 Стоимость: ${order_data.get('labelCost', 0):.2f}\n"
            f"🏢 Перевозчик: {order_data.get('carrier', 'N/A').upper()}\n\n"
            f"Скачать лейбл можно в веб\\-дашборде"
        )
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None):
        """Send a message to a user"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode or ParseMode.MARKDOWN
            )
            logger.info(f"Message sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            raise