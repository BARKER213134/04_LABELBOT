from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
import logging
from config import get_settings

logger = logging.getLogger(__name__)

class TelegramService:
    """Service for Telegram bot interactions"""
    
    def __init__(self, use_production=False):
        settings = get_settings()
        # Выбираем токен в зависимости от окружения
        if use_production:
            bot_token = settings.telegram_bot_token_prod
        else:
            bot_token = settings.telegram_bot_token
        self.bot = Bot(token=bot_token)
        self.is_production = use_production
    
    async def send_welcome_message(self, chat_id: int):
        """Send welcome message with instructions"""
        text = (
            "🚀 *Добро пожаловать в ShipBot\\!*\\n\\n"
            "Я помогу вам создать shipping labels для:\\n"
            "📦 USPS\\n"
            "✈️ FedEx\\n"
            "🚚 UPS\\n\\n"
            "*Доступные команды:*\\n"
            "/create \\- Создать новый лейбл\\n"
            "/help \\- Показать помощь\\n\\n"
            "💡 Для полного функционала используйте веб\\-дашборд:\\n"
            "https://shipbot\\-labels\\.preview\\.emergentagent\\.com"
        )
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
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