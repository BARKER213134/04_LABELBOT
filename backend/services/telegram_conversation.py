from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Conversation states
(
    SHIP_FROM_NAME,
    SHIP_FROM_ADDRESS,
    SHIP_FROM_CITY,
    SHIP_FROM_STATE,
    SHIP_FROM_ZIP,
    SHIP_FROM_PHONE,
    SHIP_TO_NAME,
    SHIP_TO_ADDRESS,
    SHIP_TO_CITY,
    SHIP_TO_STATE,
    SHIP_TO_ZIP,
    SHIP_TO_PHONE,
    PACKAGE_WEIGHT,
    PACKAGE_DIMENSIONS,
    SELECT_CARRIER,
    SELECT_SERVICE,
    CONFIRM,
) = range(17)

class TelegramConversationHandler:
    """Handler for multi-step label creation conversation"""
    
    def __init__(self, db, orders_service):
        self.db = db
        self.orders_service = orders_service
        self.user_data: Dict[str, Dict[str, Any]] = {}
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user's conversation data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        return self.user_data[user_id]
    
    def clear_user_data(self, user_id: str):
        """Clear user's conversation data"""
        if user_id in self.user_data:
            del self.user_data[user_id]
    
    async def start_create(self, update: Update, context) -> int:
        """Start the label creation process"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        await update.message.reply_text(
            "🚀 *Создание нового лейбла*\\n\\n"
            "Давайте начнем! Я проведу вас через все шаги.\n\n"
            "📍 *Шаг 1 из 4: Адрес отправителя*\\n\\n"
            "Введите имя отправителя:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return SHIP_FROM_NAME
    
    # ===== SHIP FROM ADDRESS =====
    
    async def ship_from_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromName'] = update.message.text
        
        await update.message.reply_text(
            "✅ Отлично!\n\n"
            "Теперь введите адрес отправителя \\(улица, дом\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_FROM_ADDRESS
    
    async def ship_from_address(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromAddressLine1'] = update.message.text
        
        await update.message.reply_text("Введите город:")
        return SHIP_FROM_CITY
    
    async def ship_from_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromCity'] = update.message.text
        
        await update.message.reply_text(
            "Введите штат \\(2 буквы, например: CA, NY, TX\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_FROM_STATE
    
    async def ship_from_state(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        state = update.message.text.strip().upper()
        
        if len(state) != 2:
            await update.message.reply_text(
                "❌ Штат должен быть 2 буквы \\(например: CA\\). Попробуйте еще раз:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_STATE
        
        data = self.get_user_data(user_id)
        data['shipFromState'] = state
        
        await update.message.reply_text("Введите ZIP код:")
        return SHIP_FROM_ZIP
    
    async def ship_from_zip(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            await update.message.reply_text(
                "❌ ZIP код должен быть 5 цифр. Попробуйте еще раз:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_ZIP
        
        data = self.get_user_data(user_id)
        data['shipFromPostalCode'] = zip_code
        
        await update.message.reply_text(
            "Введите телефон отправителя \\(или напишите 'skip' чтобы пропустить\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_FROM_PHONE
    
    async def ship_from_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        phone = update.message.text.strip()
        if phone.lower() != 'skip':
            data['shipFromPhone'] = phone
        
        await update.message.reply_text(
            "✅ *Адрес отправителя сохранен!*\n\n"
            "📍 *Шаг 2 из 4: Адрес получателя*\n\n"
            "Введите имя получателя:",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_TO_NAME
    
    # ===== SHIP TO ADDRESS =====
    
    async def ship_to_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToName'] = update.message.text
        
        await update.message.reply_text(
            "Введите адрес получателя \\(улица, дом\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_TO_ADDRESS
    
    async def ship_to_address(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToAddressLine1'] = update.message.text
        
        await update.message.reply_text("Введите город:")
        return SHIP_TO_CITY
    
    async def ship_to_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToCity'] = update.message.text
        
        await update.message.reply_text(
            "Введите штат \\(2 буквы\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_TO_STATE
    
    async def ship_to_state(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        state = update.message.text.strip().upper()
        
        if len(state) != 2:
            await update.message.reply_text(
                "❌ Штат должен быть 2 буквы. Попробуйте еще раз:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_STATE
        
        data = self.get_user_data(user_id)
        data['shipToState'] = state
        
        await update.message.reply_text("Введите ZIP код:")
        return SHIP_TO_ZIP
    
    async def ship_to_zip(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            await update.message.reply_text(
                "❌ ZIP код должен быть 5 цифр. Попробуйте еще раз:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_ZIP
        
        data = self.get_user_data(user_id)
        data['shipToPostalCode'] = zip_code
        
        await update.message.reply_text(
            "Введите телефон получателя \\(или 'skip'\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return SHIP_TO_PHONE
    
    async def ship_to_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        phone = update.message.text.strip()
        if phone.lower() != 'skip':
            data['shipToPhone'] = phone
        
        await update.message.reply_text(
            "✅ *Адрес получателя сохранен!*\n\n"
            "📦 *Шаг 3 из 4: Параметры посылки*\n\n"
            "Введите вес в унциях \\(например: 16 для 1 фунта\\):",
            parse_mode=ParseMode.MARKDOWN
        )
        return PACKAGE_WEIGHT
    
    # ===== PACKAGE DETAILS =====
    
    async def package_weight(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        try:
            weight = float(update.message.text.strip())
            if weight <= 0:
                raise ValueError()
            data['packageWeight'] = weight
        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректный вес \\(число больше 0\\):",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_WEIGHT
        
        await update.message.reply_text(
            "Введите размеры посылки в дюймах через пробел:\n"
            "Длина Ширина Высота \\(например: 12 8 6\\)",
            parse_mode=ParseMode.MARKDOWN
        )
        return PACKAGE_DIMENSIONS
    
    async def package_dimensions(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        try:
            dimensions = update.message.text.strip().split()
            if len(dimensions) != 3:
                raise ValueError()
            
            length, width, height = [float(d) for d in dimensions]
            if any(d <= 0 for d in [length, width, height]):
                raise ValueError()
            
            data['packageLength'] = length
            data['packageWidth'] = width
            data['packageHeight'] = height
        except ValueError:
            await update.message.reply_text(
                "❌ Введите 3 числа через пробел \\(Длина Ширина Высота\\). Попробуйте еще раз:",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_DIMENSIONS
        
        # Show carrier selection
        keyboard = [
            [InlineKeyboardButton("📦 USPS", callback_data="carrier_usps")],
            [InlineKeyboardButton("✈️ FedEx", callback_data="carrier_fedex")],
            [InlineKeyboardButton("🚚 UPS", callback_data="carrier_ups")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ *Параметры посылки сохранены!*\n\n"
            "🚚 *Шаг 4 из 4: Выбор перевозчика*\n\n"
            "Выберите перевозчика:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_CARRIER
    
    # ===== CARRIER SELECTION =====
    
    async def select_carrier(self, update: Update, context) -> int:
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        carrier = query.data.replace("carrier_", "")
        data['carrier'] = carrier
        
        # Service options based on carrier
        service_options = {
            'usps': [
                ('Priority Mail', 'usps_priority_mail'),
                ('First Class Mail', 'usps_first_class_mail'),
                ('Ground Advantage', 'usps_ground_advantage'),
            ],
            'fedex': [
                ('FedEx Ground', 'fedex_ground'),
                ('FedEx 2Day', 'fedex_2_day'),
                ('FedEx Overnight', 'fedex_priority_overnight'),
            ],
            'ups': [
                ('UPS Ground', 'ups_ground'),
                ('UPS 2nd Day Air', 'ups_2nd_day_air'),
                ('UPS Next Day Air', 'ups_next_day_air'),
            ]
        }
        
        keyboard = [
            [InlineKeyboardButton(label, callback_data=f"service_{code}")]
            for label, code in service_options[carrier]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Выбран: *{carrier.upper()}*\n\n"
            f"Теперь выберите тип доставки:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_SERVICE
    
    async def select_service(self, update: Update, context) -> int:
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        service_code = query.data.replace("service_", "")
        data['serviceCode'] = service_code
        
        # Show confirmation
        summary = (
            "📋 *Подтверждение заказа*\n\n"
            f"*От:* {data.get('shipFromName')}\n"
            f"{data.get('shipFromAddressLine1')}\n"
            f"{data.get('shipFromCity')}, {data.get('shipFromState')} {data.get('shipFromPostalCode')}\n\n"
            f"*Кому:* {data.get('shipToName')}\n"
            f"{data.get('shipToAddressLine1')}\n"
            f"{data.get('shipToCity')}, {data.get('shipToState')} {data.get('shipToPostalCode')}\n\n"
            f"*Посылка:*\n"
            f"Вес: {data.get('packageWeight')} oz\n"
            f"Размеры: {data.get('packageLength')}x{data.get('packageWidth')}x{data.get('packageHeight')} in\n\n"
            f"*Перевозчик:* {data.get('carrier').upper()}\n"
            f"*Сервис:* {service_code.replace('_', ' ').title()}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Создать лейбл", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            summary,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return CONFIRM
    
    async def confirm_and_create(self, update: Update, context) -> int:
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username
        
        if query.data == "confirm_no":
            await query.edit_message_text(
                "❌ Создание лейбла отменено.\n\n"
                "Используйте /create чтобы начать заново.",
                parse_mode=ParseMode.MARKDOWN
            )
            self.clear_user_data(user_id)
            return ConversationHandler.END
        
        # Create the label
        await query.edit_message_text("⏳ Создаю лейбл...", parse_mode=ParseMode.MARKDOWN)
        
        data = self.get_user_data(user_id)
        data['telegram_user_id'] = user_id
        data['telegram_username'] = username
        
        try:
            # Call orders service to create label
            result = await self.orders_service.create_order(data)
            
            success_message = (
                "✅ *Лейбл создан успешно!*\n\n"
                f"📋 Tracking: `{result.get('trackingNumber', 'N/A')}`\n"
                f"💰 Стоимость: ${result.get('cost', 0):.2f}\n"
                f"🚚 Перевозчик: {data.get('carrier').upper()}\n\n"
                f"🔗 Скачать лейбл можно в веб-дашборде"
            )
            
            await query.edit_message_text(success_message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error creating label: {e}", exc_info=True)
            await query.edit_message_text(
                f"❌ Ошибка при создании лейбла: {str(e)}\n\n"
                f"Попробуйте еще раз: /create",
                parse_mode=ParseMode.MARKDOWN
            )
        
        self.clear_user_data(user_id)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context) -> int:
        """Cancel the conversation"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        await update.message.reply_text(
            "❌ Создание лейбла отменено.\n\n"
            "Используйте /create чтобы начать заново.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler"""
        return ConversationHandler(
            entry_points=[CommandHandler('create', self.start_create)],
            states={
                SHIP_FROM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_name)],
                SHIP_FROM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_address)],
                SHIP_FROM_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_city)],
                SHIP_FROM_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_state)],
                SHIP_FROM_ZIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_zip)],
                SHIP_FROM_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_phone)],
                
                SHIP_TO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_name)],
                SHIP_TO_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_address)],
                SHIP_TO_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_city)],
                SHIP_TO_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_state)],
                SHIP_TO_ZIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_zip)],
                SHIP_TO_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_phone)],
                
                PACKAGE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.package_weight)],
                PACKAGE_DIMENSIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.package_dimensions)],
                
                SELECT_CARRIER: [CallbackQueryHandler(self.select_carrier, pattern="^carrier_")],
                SELECT_SERVICE: [CallbackQueryHandler(self.select_service, pattern="^service_")],
                CONFIRM: [CallbackQueryHandler(self.confirm_and_create, pattern="^confirm_")],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
