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
    
    async def send_welcome_message(self, chat_id: int):
        """Send welcome message with instructions"""
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 *SHIPBOT - SHIPPING LABELS*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Здравствуйте!\n\n"
            "Добро пожаловать в профессиональный сервис создания shipping labels.\n\n"
            "📦 *Поддерживаемые перевозчики:*\n"
            "▫️ USPS (US Postal Service)\n"
            "▫️ FedEx\n"
            "▫️ UPS\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *ДОСТУПНЫЕ КОМАНДЫ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "/create - Создать новый shipping label\n"
            "/help - Справка по использованию\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Веб-дашборд:*\n"
            "Для расширенных возможностей используйте:\n"
            "https://shipbot-labels.preview.emergentagent.com"
        )
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
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