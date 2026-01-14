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
import random

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
    REVIEW_SUMMARY,
    EDIT_SECTION,
    SELECT_CARRIER,
    SELECT_SERVICE,
    CONFIRM,
) = range(19)

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
    
    def get_progress_bar(self, step: int) -> str:
        """Generate progress bar for steps"""
        total_steps = 4
        filled = "🟦" * step
        empty = "⬜" * (total_steps - step)
        return f"{filled}{empty}"
    
    def generate_random_phone(self) -> str:
        """Generate random US phone number"""
        # Generate phone in format: (XXX) XXX-XXXX
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        return f"({area_code}) {exchange}-{number}"
    
    async def start_create(self, update: Update, context) -> int:
        """Start the label creation process"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *СОЗДАНИЕ SHIPPING LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Здравствуйте! Я помогу Вам создать shipping label.\n\n"
            f"Прогресс: {self.get_progress_bar(1)} (Шаг 1/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ШАГ 1: АДРЕС ОТПРАВИТЕЛЯ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 1.1:* Полное имя\n\n"
            "Пожалуйста, введите полное имя отправителя:"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_NAME
    
    async def start_create_callback(self, update: Update, context) -> int:
        """Start the label creation process from callback button"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *СОЗДАНИЕ SHIPPING LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Здравствуйте! Я помогу Вам создать shipping label.\n\n"
            f"Прогресс: {self.get_progress_bar(1)} (Шаг 1/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ШАГ 1: АДРЕС ОТПРАВИТЕЛЯ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 1.1:* Полное имя\n\n"
            "Пожалуйста, введите полное имя отправителя:"
        )
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_NAME
    
    # ===== SHIP FROM ADDRESS =====
    
    async def ship_from_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromName'] = update.message.text
        
        text = (
            "✅ *Имя отправителя сохранено*\n\n"
            "▫️ *Подшаг 1.2:* Адрес\n\n"
            "Введите адрес отправителя:\n"
            "_(Улица, номер дома, квартира)_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_ADDRESS
    
    async def ship_from_address(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromAddressLine1'] = update.message.text
        
        text = (
            "✅ *Адрес сохранен*\n\n"
            "▫️ *Подшаг 1.3:* Город\n\n"
            "Введите название города:"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_CITY
    
    async def ship_from_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipFromCity'] = update.message.text
        
        text = (
            "✅ *Город сохранен*\n\n"
            "▫️ *Подшаг 1.4:* Штат\n\n"
            "Введите код штата (2 буквы):\n"
            "_Например: CA, NY, TX, FL_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_STATE
    
    async def ship_from_state(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        state = update.message.text.strip().upper()
        
        if len(state) != 2 or not state.isalpha():
            text = (
                "❌ *Некорректный формат*\n\n"
                "Код штата должен состоять из 2 букв.\n"
                "_Например: CA, NY, TX_\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_STATE
        
        data = self.get_user_data(user_id)
        data['shipFromState'] = state
        
        text = (
            "✅ *Штат сохранен*\n\n"
            "▫️ *Подшаг 1.5:* ZIP код\n\n"
            "Введите почтовый индекс (5 цифр):\n"
            "_Например: 94102, 10001, 78701_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_ZIP
    
    async def ship_from_zip(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            text = (
                "❌ *Некорректный формат*\n\n"
                "ZIP код должен содержать ровно 5 цифр.\n"
                "_Например: 94102_\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_ZIP
        
        data = self.get_user_data(user_id)
        data['shipFromPostalCode'] = zip_code
        
        text = (
            "✅ *ZIP код сохранен*\n\n"
            "▫️ *Подшаг 1.6:* Телефон (опционально)\n\n"
            "Введите контактный телефон отправителя или нажмите кнопку:"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_from_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_PHONE
    
    async def ship_from_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        phone = update.message.text.strip()
        if phone.lower() not in ['пропустить', 'skip']:
            data['shipFromPhone'] = phone
        else:
            # Generate random phone if user types skip
            data['shipFromPhone'] = self.generate_random_phone()
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *ШАГ 1 ЗАВЕРШЕН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(2)} (Шаг 2/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ШАГ 2: АДРЕС ПОЛУЧАТЕЛЯ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 2.1:* Полное имя\n\n"
            "Введите полное имя получателя:"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_NAME
    
    async def skip_from_phone_callback(self, update: Update, context) -> int:
        """Handle skip button for from phone"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        # Generate random phone
        random_phone = self.generate_random_phone()
        data['shipFromPhone'] = random_phone
        
        text = (
            f"✅ *Телефон сохранен:* {random_phone}\n"
            "_(сгенерирован автоматически)_\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *ШАГ 1 ЗАВЕРШЕН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(2)} (Шаг 2/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ШАГ 2: АДРЕС ПОЛУЧАТЕЛЯ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 2.1:* Полное имя\n\n"
            "Введите полное имя получателя:"
        )
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_NAME
    
    # ===== SHIP TO ADDRESS =====
    
    async def ship_to_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToName'] = update.message.text
        
        text = (
            "✅ *Имя получателя сохранено*\n\n"
            "▫️ *Подшаг 2.2:* Адрес\n\n"
            "Введите адрес получателя:\n"
            "_(Улица, номер дома, квартира)_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_ADDRESS
    
    async def ship_to_address(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToAddressLine1'] = update.message.text
        
        text = (
            "✅ *Адрес сохранен*\n\n"
            "▫️ *Подшаг 2.3:* Город\n\n"
            "Введите название города:"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_CITY
    
    async def ship_to_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        data['shipToCity'] = update.message.text
        
        text = (
            "✅ *Город сохранен*\n\n"
            "▫️ *Подшаг 2.4:* Штат\n\n"
            "Введите код штата (2 буквы):\n"
            "_Например: CA, NY, TX, FL_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_STATE
    
    async def ship_to_state(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        state = update.message.text.strip().upper()
        
        if len(state) != 2 or not state.isalpha():
            text = (
                "❌ *Некорректный формат*\n\n"
                "Код штата должен состоять из 2 букв.\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_STATE
        
        data = self.get_user_data(user_id)
        data['shipToState'] = state
        
        text = (
            "✅ *Штат сохранен*\n\n"
            "▫️ *Подшаг 2.5:* ZIP код\n\n"
            "Введите почтовый индекс (5 цифр):"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_ZIP
    
    async def ship_to_zip(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            text = (
                "❌ *Некорректный формат*\n\n"
                "ZIP код должен содержать ровно 5 цифр.\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_ZIP
        
        data = self.get_user_data(user_id)
        data['shipToPostalCode'] = zip_code
        
        text = (
            "✅ *ZIP код сохранен*\n\n"
            "▫️ *Подшаг 2.6:* Телефон (опционально)\n\n"
            "Введите контактный телефон получателя или нажмите кнопку:"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_to_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_PHONE
    
    async def ship_to_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        phone = update.message.text.strip()
        if phone.lower() not in ['пропустить', 'skip']:
            data['shipToPhone'] = phone
        else:
            # Generate random phone if user types skip
            data['shipToPhone'] = self.generate_random_phone()
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *ШАГ 2 ЗАВЕРШЕН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(3)} (Шаг 3/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *ШАГ 3: ПАРАМЕТРЫ ПОСЫЛКИ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 3.1:* Вес посылки\n\n"
            "Введите вес в унциях:\n"
            "_(1 фунт = 16 унций)_\n"
            "_Например: 16_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return PACKAGE_WEIGHT
    
    async def skip_to_phone_callback(self, update: Update, context) -> int:
        """Handle skip button for to phone"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        # Generate random phone
        random_phone = self.generate_random_phone()
        data['shipToPhone'] = random_phone
        
        text = (
            f"✅ *Телефон сохранен:* {random_phone}\n"
            "_(сгенерирован автоматически)_\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *ШАГ 2 ЗАВЕРШЕН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(3)} (Шаг 3/4)\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *ШАГ 3: ПАРАМЕТРЫ ПОСЫЛКИ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▫️ *Подшаг 3.1:* Вес посылки\n\n"
            "Введите вес в унциях:\n"
            "_(1 фунт = 16 унций)_\n"
            "_Например: 16_"
        )
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
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
            text = (
                "❌ *Некорректное значение*\n\n"
                "Вес должен быть положительным числом.\n"
                "_Например: 16 или 24.5_\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return PACKAGE_WEIGHT
        
        pounds = weight / 16
        text = (
            f"✅ *Вес сохранен* ({weight} oz ≈ {pounds:.2f} lbs)\n\n"
            "▫️ *Подшаг 3.2:* Размеры посылки\n\n"
            "Введите размеры через пробел в дюймах:\n"
            "*Длина Ширина Высота*\n\n"
            "_Например: 12 8 6_"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
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
            text = (
                "❌ *Некорректный формат*\n\n"
                "Введите 3 положительных числа через пробел.\n"
                "_Формат: Длина Ширина Высота_\n"
                "_Например: 12 8 6_\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return PACKAGE_DIMENSIONS
        
        # Show review summary
        await self.show_review_summary(update.message, user_id)
        return REVIEW_SUMMARY
    
    async def show_review_summary(self, message, user_id: str):
        """Show summary with edit options"""
        data = self.get_user_data(user_id)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *ПРОВЕРКА ДАННЫХ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Пожалуйста, проверьте введенные данные перед выбором перевозчика.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ОТПРАВИТЕЛЬ*\n"
            f"▫️ Имя: {data.get('shipFromName')}\n"
            f"▫️ Адрес: {data.get('shipFromAddressLine1')}\n"
            f"▫️ Город: {data.get('shipFromCity')}, {data.get('shipFromState')} {data.get('shipFromPostalCode')}\n"
        )
        
        if data.get('shipFromPhone'):
            text += f"▫️ Телефон: {data.get('shipFromPhone')}\n"
        
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ПОЛУЧАТЕЛЬ*\n"
            f"▫️ Имя: {data.get('shipToName')}\n"
            f"▫️ Адрес: {data.get('shipToAddressLine1')}\n"
            f"▫️ Город: {data.get('shipToCity')}, {data.get('shipToState')} {data.get('shipToPostalCode')}\n"
        )
        
        if data.get('shipToPhone'):
            text += f"▫️ Телефон: {data.get('shipToPhone')}\n"
        
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *ПОСЫЛКА*\n"
            f"▫️ Вес: {data.get('packageWeight')} oz ({data.get('packageWeight')/16:.2f} lbs)\n"
            f"▫️ Размеры: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} дюймов\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать отправителя", callback_data="edit_from")],
            [InlineKeyboardButton("✏️ Редактировать получателя", callback_data="edit_to")],
            [InlineKeyboardButton("✏️ Редактировать посылку", callback_data="edit_package")],
            [InlineKeyboardButton("✅ Всё верно, продолжить", callback_data="continue_to_carrier")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_edit_choice(self, update: Update, context) -> int:
        """Handle edit section choice"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        edit_choice = query.data
        
        if edit_choice == "continue_to_carrier":
            # Continue to carrier selection
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *ДАННЫЕ ПОДТВЕРЖДЕНЫ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Прогресс: {self.get_progress_bar(4)} (Шаг 4/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🚚 *ШАГ 4: ВЫБОР ПЕРЕВОЗЧИКА*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Подшаг 4.1:* Компания-перевозчик\n\n"
                "Выберите компанию для доставки:"
            )
            
            keyboard = [
                [InlineKeyboardButton("📦 USPS (US Postal Service)", callback_data="carrier_usps")],
                [InlineKeyboardButton("✈️ FedEx", callback_data="carrier_fedex")],
                [InlineKeyboardButton("🚚 UPS", callback_data="carrier_ups")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SELECT_CARRIER
        
        # Show edit options for the selected section
        if edit_choice == "edit_from":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✏️ *РЕДАКТИРОВАНИЕ ОТПРАВИТЕЛЯ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Что хотите изменить?"
            )
            keyboard = [
                [InlineKeyboardButton("📝 Имя и адрес", callback_data="edit_from_address")],
                [InlineKeyboardButton("📍 Город и штат", callback_data="edit_from_location")],
                [InlineKeyboardButton("📞 Телефон", callback_data="edit_from_phone")],
                [InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review")]
            ]
        elif edit_choice == "edit_to":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✏️ *РЕДАКТИРОВАНИЕ ПОЛУЧАТЕЛЯ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Что хотите изменить?"
            )
            keyboard = [
                [InlineKeyboardButton("📝 Имя и адрес", callback_data="edit_to_address")],
                [InlineKeyboardButton("📍 Город и штат", callback_data="edit_to_location")],
                [InlineKeyboardButton("📞 Телефон", callback_data="edit_to_phone")],
                [InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review")]
            ]
        elif edit_choice == "edit_package":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✏️ *РЕДАКТИРОВАНИЕ ПОСЫЛКИ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Что хотите изменить?"
            )
            keyboard = [
                [InlineKeyboardButton("⚖️ Вес", callback_data="edit_weight")],
                [InlineKeyboardButton("📏 Размеры", callback_data="edit_dimensions")],
                [InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return EDIT_SECTION
    
    async def handle_specific_edit(self, update: Update, context) -> int:
        """Handle specific field edit choice"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        edit_type = query.data
        
        if edit_type == "back_to_review":
            # Go back to review summary
            await self.show_review_summary(query.message, user_id)
            return REVIEW_SUMMARY
        
        # Handle different edit types
        if edit_type == "edit_from_address":
            await query.message.reply_text(
                "✏️ *Редактирование имени отправителя*\n\n"
                "Введите новое имя отправителя:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_NAME
        elif edit_type == "edit_from_location":
            await query.message.reply_text(
                "✏️ *Редактирование города отправителя*\n\n"
                "Введите новый город:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_CITY
        elif edit_type == "edit_from_phone":
            text = "✏️ *Редактирование телефона отправителя*\n\nВведите новый телефон или нажмите кнопку:"
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_from_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_PHONE
        
        elif edit_type == "edit_to_address":
            await query.message.reply_text(
                "✏️ *Редактирование имени получателя*\n\n"
                "Введите новое имя получателя:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_NAME
        elif edit_type == "edit_to_location":
            await query.message.reply_text(
                "✏️ *Редактирование города получателя*\n\n"
                "Введите новый город:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_CITY
        elif edit_type == "edit_to_phone":
            text = "✏️ *Редактирование телефона получателя*\n\nВведите новый телефон или нажмите кнопку:"
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_to_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_PHONE
        
        elif edit_type == "edit_weight":
            await query.message.reply_text(
                "✏️ *Редактирование веса*\n\n"
                "Введите новый вес в унциях:\n"
                "_(1 фунт = 16 унций)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_WEIGHT
        elif edit_type == "edit_dimensions":
            await query.message.reply_text(
                "✏️ *Редактирование размеров*\n\n"
                "Введите новые размеры через пробел:\n"
                "*Длина Ширина Высота*\n"
                "_Например: 12 8 6_",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_DIMENSIONS
        
        return EDIT_SECTION
    
    # ===== CARRIER SELECTION =====
    
    async def select_carrier(self, update: Update, context) -> int:
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        carrier = query.data.replace("carrier_", "")
        data['carrier'] = carrier
        
        carrier_names = {
            'usps': 'USPS (US Postal Service)',
            'fedex': 'FedEx',
            'ups': 'UPS'
        }
        
        # Service options based on carrier
        service_options = {
            'usps': [
                ('Priority Mail (2-3 дня)', 'usps_priority_mail'),
                ('First Class Mail (3-5 дней)', 'usps_first_class_mail'),
                ('Ground Advantage (2-5 дней)', 'usps_ground_advantage'),
            ],
            'fedex': [
                ('FedEx Ground (1-5 дней)', 'fedex_ground'),
                ('FedEx 2Day', 'fedex_2_day'),
                ('FedEx Priority Overnight', 'fedex_priority_overnight'),
            ],
            'ups': [
                ('UPS Ground (1-5 дней)', 'ups_ground'),
                ('UPS 2nd Day Air', 'ups_2nd_day_air'),
                ('UPS Next Day Air', 'ups_next_day_air'),
            ]
        }
        
        text = (
            f"✅ *Выбрано:* {carrier_names[carrier]}\n\n"
            "▫️ *Подшаг 4.2:* Тип доставки\n\n"
            "Выберите скорость доставки:"
        )
        
        keyboard = [
            [InlineKeyboardButton(label, callback_data=f"service_{code}")]
            for label, code in service_options[carrier]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
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
        
        # Service names for display
        service_names = {
            'usps_priority_mail': 'Priority Mail',
            'usps_first_class_mail': 'First Class Mail',
            'usps_ground_advantage': 'Ground Advantage',
            'fedex_ground': 'FedEx Ground',
            'fedex_2_day': 'FedEx 2Day',
            'fedex_priority_overnight': 'FedEx Priority Overnight',
            'ups_ground': 'UPS Ground',
            'ups_2nd_day_air': 'UPS 2nd Day Air',
            'ups_next_day_air': 'UPS Next Day Air',
        }
        
        # Show confirmation
        summary = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *ПОДТВЕРЖДЕНИЕ ЗАКАЗА*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Пожалуйста, проверьте введенные данные:\n\n"
            "📍 *ОТПРАВИТЕЛЬ*\n"
            f"▫️ Имя: {data.get('shipFromName')}\n"
            f"▫️ Адрес: {data.get('shipFromAddressLine1')}\n"
            f"▫️ Город: {data.get('shipFromCity')}, {data.get('shipFromState')} {data.get('shipFromPostalCode')}\n"
        )
        
        if data.get('shipFromPhone'):
            summary += f"▫️ Телефон: {data.get('shipFromPhone')}\n"
        
        summary += (
            f"\n📍 *ПОЛУЧАТЕЛЬ*\n"
            f"▫️ Имя: {data.get('shipToName')}\n"
            f"▫️ Адрес: {data.get('shipToAddressLine1')}\n"
            f"▫️ Город: {data.get('shipToCity')}, {data.get('shipToState')} {data.get('shipToPostalCode')}\n"
        )
        
        if data.get('shipToPhone'):
            summary += f"▫️ Телефон: {data.get('shipToPhone')}\n"
        
        summary += (
            f"\n📦 *ПОСЫЛКА*\n"
            f"▫️ Вес: {data.get('packageWeight')} oz ({data.get('packageWeight')/16:.2f} lbs)\n"
            f"▫️ Размеры: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} дюймов\n"
            f"\n🚚 *ДОСТАВКА*\n"
            f"▫️ Перевозчик: {data.get('carrier').upper()}\n"
            f"▫️ Сервис: {service_names.get(service_code, service_code)}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить и создать лейбл", callback_data="confirm_yes")],
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
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ *ЗАКАЗ ОТМЕНЕН*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Создание лейбла отменено.\n\n"
                "Нажмите кнопку ниже, чтобы вернуться в главное меню:"
            )
            
            keyboard = [
                [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            self.clear_user_data(user_id)
            return ConversationHandler.END
        
        # Create the label
        await query.edit_message_text(
            "⏳ *Создаю лейбл...*\n\nПожалуйста, подождите.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        data = self.get_user_data(user_id)
        data['telegram_user_id'] = user_id
        data['telegram_username'] = username
        
        try:
            # Call orders service to create label
            result = await self.orders_service.create_order(data)
            
            success_message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *ЛЕЙБЛ СОЗДАН УСПЕШНО!*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 *Информация о доставке:*\n\n"
                f"▫️ Tracking номер:\n`{result.get('trackingNumber', 'N/A')}`\n\n"
                f"▫️ Перевозчик: {data.get('carrier').upper()}\n"
                f"▫️ Стоимость: ${result.get('cost', 0):.2f}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔗 Скачать PDF лейбл можно в веб-дашборде:\n"
                "https://shipbot-labels.preview.emergentagent.com\n\n"
                "Спасибо за использование нашего сервиса!"
            )
            
            await query.edit_message_text(success_message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error creating label: {e}", exc_info=True)
            # Use plain text for error messages to avoid Markdown parsing issues
            error_text = str(e).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
            error_message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ ОШИБКА\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Не удалось создать лейбл.\n\n"
                f"Причина: {error_text}\n\n"
                "Пожалуйста, попробуйте еще раз:\n/create"
            )
            await query.edit_message_text(error_message)
        
        self.clear_user_data(user_id)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context) -> int:
        """Cancel the conversation"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ *СОЗДАНИЕ ОТМЕНЕНО*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Вы отменили создание лейбла.\n\n"
            "Нажмите кнопку ниже, чтобы вернуться в главное меню:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler"""
        return ConversationHandler(
            entry_points=[
                CommandHandler('create', self.start_create),
                CallbackQueryHandler(self.start_create_callback, pattern="^start_create$")
            ],
            states={
                SHIP_FROM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_name)],
                SHIP_FROM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_address)],
                SHIP_FROM_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_city)],
                SHIP_FROM_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_state)],
                SHIP_FROM_ZIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_zip)],
                SHIP_FROM_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_from_phone),
                    CallbackQueryHandler(self.skip_from_phone_callback, pattern="^skip_from_phone$")
                ],
                
                SHIP_TO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_name)],
                SHIP_TO_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_address)],
                SHIP_TO_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_city)],
                SHIP_TO_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_state)],
                SHIP_TO_ZIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_zip)],
                SHIP_TO_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.ship_to_phone),
                    CallbackQueryHandler(self.skip_to_phone_callback, pattern="^skip_to_phone$")
                ],
                
                PACKAGE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.package_weight)],
                PACKAGE_DIMENSIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.package_dimensions)],
                
                SELECT_CARRIER: [CallbackQueryHandler(self.select_carrier, pattern="^carrier_")],
                SELECT_SERVICE: [CallbackQueryHandler(self.select_service, pattern="^service_")],
                CONFIRM: [CallbackQueryHandler(self.confirm_and_create, pattern="^confirm_")],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
