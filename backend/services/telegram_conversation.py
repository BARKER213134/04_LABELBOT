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
from typing import Dict, Any, List
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
    SELECT_RATE,
    CONFIRM,
    TEMPLATE_USE,
    TEMPLATE_EDIT,
    TEMPLATE_SAVE_NAME,
) = range(21)

class TelegramConversationHandler:
    """Handler for multi-step label creation conversation"""
    
    def __init__(self, db, orders_service, shipengine_service=None, users_service=None, templates_service=None):
        self.db = db
        self.orders_service = orders_service
        self.shipengine_service = shipengine_service
        self.users_service = users_service
        self.templates_service = templates_service
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
    
    async def _ensure_user(self, update: Update) -> Dict[str, Any]:
        """Ensure user exists in database and return user data"""
        if not self.users_service:
            return {}
        
        tg_user = update.effective_user
        user = await self.users_service.get_or_create_user(
            telegram_id=str(tg_user.id),
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name
        )
        return user
    
    async def start_create(self, update: Update, context) -> int:
        """Start the label creation process"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        # Ensure user exists
        db_user = await self._ensure_user(update)
        balance = db_user.get('balance', 0.0) if db_user else 0.0
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *СОЗДАНИЕ SHIPPING LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Ваш баланс: *${balance:.2f}*\n\n"
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
        
        # Ensure user exists
        db_user = await self._ensure_user(update)
        balance = db_user.get('balance', 0.0) if db_user else 0.0
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *СОЗДАНИЕ SHIPPING LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Ваш баланс: *${balance:.2f}*\n\n"
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
        
        # Check if we're in edit mode - editing only name
        if data.get('editing_field') == 'from_name_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing address chain
        if data.get('editing_field') == 'from_address':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'from_city_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing location chain (city -> state -> zip)
        if data.get('editing_field') == 'from_location':
            text = (
                "✅ *Штат сохранен*\n\n"
                "▫️ ZIP код\n\n"
                "Введите почтовый индекс (5 цифр):"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_ZIP
        
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
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'from_location':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'from_phone':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'from_phone':
            data['editing_field'] = None
            await query.message.reply_text(
                f"✅ *Телефон сохранен:* {random_phone}\n_(сгенерирован автоматически)_",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(query.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing only name
        if data.get('editing_field') == 'to_name_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing address only
        if data.get('editing_field') == 'to_address':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing city only
        if data.get('editing_field') == 'to_city_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode - editing location chain (city -> state -> zip)
        if data.get('editing_field') == 'to_location':
            text = (
                "✅ *Штат сохранен*\n\n"
                "▫️ ZIP код\n\n"
                "Введите почтовый индекс (5 цифр):"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_ZIP
        
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
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'to_location':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'to_phone':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'to_phone':
            data['editing_field'] = None
            await query.message.reply_text(
                f"✅ *Телефон сохранен:* {random_phone}\n_(сгенерирован автоматически)_",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(query.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'weight':
            data['editing_field'] = None
            pounds = weight / 16
            await update.message.reply_text(
                f"✅ *Вес сохранен* ({weight} oz ≈ {pounds:.2f} lbs)",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
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
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'dimensions':
            data['editing_field'] = None
            await update.message.reply_text(
                f"✅ *Размеры сохранены* ({length}×{width}×{height} дюймов)",
                parse_mode=ParseMode.MARKDOWN
            )
        
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
        
        edit_choice = query.data
        
        if edit_choice == "continue_to_carrier":
            user_id = str(update.effective_user.id)
            data = self.get_user_data(user_id)
            
            # Show loading message
            await query.edit_message_text(
                "⏳ *Получаю тарифы...*\n\nПожалуйста, подождите.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Fetch rates from ShipEngine
            try:
                rates = await self._fetch_rates(data)
                
                if not rates:
                    text = (
                        "❌ *Тарифы не найдены*\n\n"
                        "К сожалению, не удалось получить тарифы для данного маршрута.\n"
                        "Пожалуйста, проверьте адреса и попробуйте снова."
                    )
                    keyboard = [[InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review_from_rates")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                    return SELECT_RATE
                
                # Store rates in user data
                data['available_rates'] = rates
                
                # Show rates
                await self._show_rates(query, user_id, rates)
                return SELECT_RATE
                
            except Exception as e:
                logger.error(f"Error fetching rates: {e}")
                text = (
                    "❌ *Ошибка получения тарифов*\n\n"
                    f"Причина: {str(e)}\n\n"
                    "Попробуйте позже или проверьте данные."
                )
                keyboard = [[InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review_from_rates")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                return SELECT_RATE
        
        # Show edit options for the selected section
        if edit_choice == "edit_from":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✏️ *РЕДАКТИРОВАНИЕ ОТПРАВИТЕЛЯ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Что хотите изменить?"
            )
            keyboard = [
                [InlineKeyboardButton("📝 Адрес", callback_data="edit_from_address")],
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
                [InlineKeyboardButton("📝 Адрес", callback_data="edit_to_address")],
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
        else:
            # Fallback for unknown edit choice
            text = (
                "❌ Сессия устарела.\n\n"
                "Пожалуйста, начните создание лейбла заново:"
            )
            keyboard = [
                [InlineKeyboardButton("📦 Создать лейбл", callback_data="start_create")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return EDIT_SECTION
    
    async def _fetch_rates(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch rates from ShipEngine"""
        if not self.shipengine_service:
            raise ValueError("ShipEngine service not configured")
        
        shipment_data = {
            "ship_from": {
                "name": data.get('shipFromName'),
                "address_line1": data.get('shipFromAddressLine1'),
                "city_locality": data.get('shipFromCity'),
                "state_province": data.get('shipFromState'),
                "postal_code": data.get('shipFromPostalCode'),
                "country_code": "US",
                "phone": data.get('shipFromPhone', ''),
            },
            "ship_to": {
                "name": data.get('shipToName'),
                "address_line1": data.get('shipToAddressLine1'),
                "city_locality": data.get('shipToCity'),
                "state_province": data.get('shipToState'),
                "postal_code": data.get('shipToPostalCode'),
                "country_code": "US",
                "phone": data.get('shipToPhone', ''),
            },
            "packages": [{
                "weight": {
                    "value": data.get('packageWeight'),
                    "unit": "ounce"
                },
                "dimensions": {
                    "length": data.get('packageLength'),
                    "width": data.get('packageWidth'),
                    "height": data.get('packageHeight'),
                    "unit": "inch"
                }
            }]
        }
        
        return await self.shipengine_service.get_rates(shipment_data)
    
    async def _show_rates(self, query, user_id: str, rates: List[Dict[str, Any]]):
        """Display available rates with prices - 4 per carrier"""
        # Carrier display settings
        carrier_config = {
            'stamps_com': {'icon': '📦', 'name': 'USPS'},
            'usps': {'icon': '📦', 'name': 'USPS'},
            'fedex': {'icon': '✈️', 'name': 'FedEx'},
            'ups': {'icon': '🚚', 'name': 'UPS'},
        }
        
        # Popular services to prioritize (in order of priority)
        popular_services = {
            'stamps_com': ['usps_ground_advantage', 'usps_priority_mail', 'usps_first_class_mail', 'usps_priority_mail_express'],
            'usps': ['usps_ground_advantage', 'usps_priority_mail', 'usps_first_class_mail', 'usps_priority_mail_express'],
            'fedex': ['fedex_ground', 'fedex_home_delivery', 'fedex_2day', 'fedex_express_saver'],
            'ups': ['ups_ground', 'ups_3_day_select', 'ups_2nd_day_air', 'ups_next_day_air_saver'],
        }
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💰 *ДОСТУПНЫЕ ТАРИФЫ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(4)} (Шаг 4/4)\n\n"
            "Выберите тариф доставки:\n"
            "_Цены включают все сборы_\n\n"
        )
        
        # Group rates by carrier
        rates_by_carrier = {}
        for rate in rates:
            carrier_code = rate.get('carrier_code', '').lower()
            if carrier_code not in rates_by_carrier:
                rates_by_carrier[carrier_code] = []
            rates_by_carrier[carrier_code].append(rate)
        
        keyboard = []
        rate_index = 0
        data = self.get_user_data(user_id)
        data['rate_map'] = {}
        
        # Process each carrier
        for carrier_code in ['stamps_com', 'fedex', 'ups']:
            carrier_rates = rates_by_carrier.get(carrier_code, [])
            if not carrier_rates:
                continue
            
            config = carrier_config.get(carrier_code, {'icon': '📦', 'name': carrier_code})
            popular = popular_services.get(carrier_code, [])
            
            # Sort rates: prioritize popular services, then by price
            def rate_sort_key(r):
                service_code = r.get('service_code', '')
                try:
                    priority = popular.index(service_code)
                except ValueError:
                    priority = 999
                return (priority, r.get('total_amount', 999))
            
            sorted_carrier_rates = sorted(carrier_rates, key=rate_sort_key)
            
            # Take top 4 rates for this carrier
            for rate in sorted_carrier_rates[:4]:
                service_type = rate.get('service_type', rate.get('service_code', ''))
                total_price = rate.get('total_amount', 0)
                delivery_days = rate.get('delivery_days', '')
                
                # Format delivery time
                delivery_text = f" ({delivery_days} дн.)" if delivery_days else ""
                
                button_text = f"{config['icon']} {config['name']} {service_type}{delivery_text} - ${total_price:.2f}"
                
                # Store rate info
                rate_id = f"rate_{rate_index}"
                data['rate_map'][rate_id] = rate
                rate_index += 1
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=rate_id)])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад к проверке", callback_data="back_to_review_from_rates")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
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
        
        # Handle different edit types - set editing_field flag
        if edit_type == "edit_from_address":
            data['editing_field'] = 'from_address'
            await query.message.reply_text(
                "✏️ *Редактирование адреса отправителя*\n\n"
                "Введите новый адрес:\n"
                "_(Улица, номер дома, квартира)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_ADDRESS
        elif edit_type == "edit_from_location":
            data['editing_field'] = 'from_location'
            await query.message.reply_text(
                "✏️ *Редактирование города отправителя*\n\n"
                "Введите новый город:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_CITY
        elif edit_type == "edit_from_phone":
            data['editing_field'] = 'from_phone'
            text = "✏️ *Редактирование телефона отправителя*\n\nВведите новый телефон или нажмите кнопку:"
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_from_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_PHONE
        
        elif edit_type == "edit_to_address":
            data['editing_field'] = 'to_address'
            await query.message.reply_text(
                "✏️ *Редактирование адреса получателя*\n\n"
                "Введите новый адрес:\n"
                "_(Улица, номер дома, квартира)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_ADDRESS
        elif edit_type == "edit_to_location":
            data['editing_field'] = 'to_location'
            await query.message.reply_text(
                "✏️ *Редактирование города получателя*\n\n"
                "Введите новый город:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_CITY
        elif edit_type == "edit_to_phone":
            data['editing_field'] = 'to_phone'
            text = "✏️ *Редактирование телефона получателя*\n\nВведите новый телефон или нажмите кнопку:"
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустить (сгенерировать случайный)", callback_data="skip_to_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_PHONE
        
        elif edit_type == "edit_weight":
            data['editing_field'] = 'weight'
            await query.message.reply_text(
                "✏️ *Редактирование веса*\n\n"
                "Введите новый вес в унциях:\n"
                "_(1 фунт = 16 унций)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_WEIGHT
        elif edit_type == "edit_dimensions":
            data['editing_field'] = 'dimensions'
            await query.message.reply_text(
                "✏️ *Редактирование размеров*\n\n"
                "Введите новые размеры через пробел:\n"
                "*Длина Ширина Высота*\n"
                "_Например: 12 8 6_",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_DIMENSIONS
        
        return EDIT_SECTION
    
    # ===== RATE SELECTION =====
    
    async def select_rate(self, update: Update, context) -> int:
        """Handle rate selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        callback_data = query.data
        
        # Handle back to review
        if callback_data == "back_to_review_from_rates":
            await self.show_review_summary(query.message, user_id)
            return REVIEW_SUMMARY
        
        # Get selected rate
        rate_map = data.get('rate_map', {})
        selected_rate = rate_map.get(callback_data)
        
        if not selected_rate:
            text = "❌ Тариф не найден. Попробуйте снова."
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_review_from_rates")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SELECT_RATE
        
        # Store selected rate
        data['selected_rate'] = selected_rate
        data['carrier'] = selected_rate.get('carrier_code', '')
        data['serviceCode'] = selected_rate.get('service_code', '')
        data['rate_id'] = selected_rate.get('rate_id', '')
        data['total_cost'] = selected_rate.get('total_amount', 0)
        
        # Show confirmation
        carrier_name = selected_rate.get('carrier_friendly_name', selected_rate.get('carrier_code', ''))
        service_type = selected_rate.get('service_type', '')
        delivery_days = selected_rate.get('delivery_days', '')
        total_price = selected_rate.get('total_amount', 0)
        
        delivery_text = f" ({delivery_days} дней)" if delivery_days else ""
        
        summary = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *ПОДТВЕРЖДЕНИЕ ЗАКАЗА*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
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
            f"▫️ Перевозчик: {carrier_name}\n"
            f"▫️ Сервис: {service_type}{delivery_text}\n"
            f"\n💰 *СТОИМОСТЬ: ${total_price:.2f}*\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"✅ Оплатить ${total_price:.2f} и создать лейбл", callback_data="confirm_yes")],
            [InlineKeyboardButton("◀️ Выбрать другой тариф", callback_data="back_to_rates")],
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
        data = self.get_user_data(user_id)
        
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
        
        if query.data == "back_to_rates":
            # Go back to rate selection
            rates = data.get('available_rates', [])
            if rates:
                await self._show_rates(query, user_id, rates)
                return SELECT_RATE
            else:
                # Refetch rates if not available
                await query.edit_message_text(
                    "⏳ *Получаю тарифы...*\n\nПожалуйста, подождите.",
                    parse_mode=ParseMode.MARKDOWN
                )
                try:
                    rates = await self._fetch_rates(data)
                    data['available_rates'] = rates
                    await self._show_rates(query, user_id, rates)
                    return SELECT_RATE
                except Exception as e:
                    text = f"❌ Ошибка: {str(e)}"
                    await query.edit_message_text(text)
                    return CONFIRM
        
        # Create the label
        total_cost = data.get('total_cost', 0)
        
        # Check balance before creating label
        if self.users_service:
            has_balance = await self.users_service.check_balance(user_id, total_cost)
            if not has_balance:
                db_user = await self.users_service.get_user(user_id)
                current_balance = db_user.get('balance', 0) if db_user else 0
                
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *НЕДОСТАТОЧНО СРЕДСТВ*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Стоимость лейбла: ${total_cost:.2f}\n"
                    f"Ваш баланс: ${current_balance:.2f}\n\n"
                    f"Необходимо пополнить: ${(total_cost - current_balance):.2f}\n\n"
                    "Обратитесь к администратору для пополнения баланса."
                )
                keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                return ConversationHandler.END
        
        await query.edit_message_text(
            "⏳ *Создаю лейбл...*\n\nПожалуйста, подождите.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        data['telegram_user_id'] = user_id
        data['telegram_username'] = username
        
        try:
            # Call orders service to create label
            result = await self.orders_service.create_order(data)
            
            # Deduct from user balance
            if self.users_service:
                await self.users_service.deduct_for_order(user_id, total_cost)
                db_user = await self.users_service.get_user(user_id)
                new_balance = db_user.get('balance', 0) if db_user else 0
            else:
                new_balance = 0
            
            carrier_name = data.get('selected_rate', {}).get('carrier_friendly_name', data.get('carrier', ''))
            
            # Store data for potential template save
            self.get_user_data(user_id)['last_order_data'] = data.copy()
            
            success_message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *ЛЕЙБЛ СОЗДАН УСПЕШНО!*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 *Информация о доставке:*\n\n"
                f"▫️ Tracking номер:\n`{result.get('trackingNumber', 'N/A')}`\n\n"
                f"▫️ Перевозчик: {carrier_name}\n"
                f"▫️ Стоимость: ${total_cost:.2f}\n"
                f"▫️ Остаток на балансе: ${new_balance:.2f}\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            keyboard = [
                [InlineKeyboardButton("💾 Сохранить как шаблон", callback_data="save_template")],
                [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
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
    
    async def save_template_prompt(self, update: Update, context) -> int:
        """Ask for template name"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💾 *СОХРАНИТЬ ШАБЛОН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Введите название для шаблона:\n"
            "_Например: Мой офис → Склад_"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return TEMPLATE_SAVE_NAME
    
    async def save_template_name(self, update: Update, context) -> int:
        """Save template with given name"""
        user_id = str(update.effective_user.id)
        template_name = update.message.text.strip()[:50]
        
        data = self.get_user_data(user_id)
        order_data = data.get('last_order_data', data)
        
        if self.templates_service:
            # Check limit
            count = await self.templates_service.get_templates_count(user_id)
            if count >= 10:
                text = (
                    "❌ *Достигнут лимит шаблонов*\n\n"
                    "У вас уже 10 шаблонов. Удалите один из существующих, чтобы создать новый."
                )
                keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                template = await self.templates_service.create_template(user_id, template_name, order_data)
                if template:
                    text = f"✅ Шаблон *{template_name}* сохранён!"
                else:
                    text = "❌ Ошибка сохранения шаблона"
                
                keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        self.clear_user_data(user_id)
        return ConversationHandler.END
    
    async def use_template(self, update: Update, context) -> int:
        """Use a template to create a new label"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        template_id = query.data.replace("tpl_use_", "")
        
        if not self.templates_service:
            await query.edit_message_text("❌ Сервис шаблонов недоступен")
            return ConversationHandler.END
        
        template = await self.templates_service.get_template(template_id)
        if not template:
            await query.edit_message_text("❌ Шаблон не найден")
            return ConversationHandler.END
        
        # Load template data into user_data
        template_data = self.templates_service.template_to_user_data(template)
        data = self.get_user_data(user_id)
        data.update(template_data)
        data['using_template'] = template_id
        
        # Increment use count
        await self.templates_service.increment_use_count(template_id)
        
        # Show review summary with template data
        await self.show_review_summary(query.message, user_id, from_template=True)
        return REVIEW_SUMMARY
    
    async def edit_template(self, update: Update, context) -> int:
        """Edit a template"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        template_id = query.data.replace("tpl_edit_", "")
        
        if not self.templates_service:
            await query.edit_message_text("❌ Сервис шаблонов недоступен")
            return ConversationHandler.END
        
        template = await self.templates_service.get_template(template_id)
        if not template:
            await query.edit_message_text("❌ Шаблон не найден")
            return ConversationHandler.END
        
        # Load template data into user_data
        template_data = self.templates_service.template_to_user_data(template)
        data = self.get_user_data(user_id)
        data.update(template_data)
        data['editing_template_id'] = template_id
        data['editing_template_name'] = template.get('name')
        
        # Show review summary for editing
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✏️ *РЕДАКТИРОВАНИЕ: {template.get('name')}*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        text += self._format_summary_text(data)
        
        keyboard = [
            [InlineKeyboardButton("✏️ Отправитель", callback_data="edit_from")],
            [InlineKeyboardButton("✏️ Получатель", callback_data="edit_to")],
            [InlineKeyboardButton("✏️ Посылка", callback_data="edit_package")],
            [InlineKeyboardButton("💾 Сохранить изменения", callback_data="save_template_changes")],
            [InlineKeyboardButton("◀️ Отмена", callback_data="templates_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return TEMPLATE_EDIT
    
    async def save_template_changes(self, update: Update, context) -> int:
        """Save template changes"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        template_id = data.get('editing_template_id')
        template_name = data.get('editing_template_name', 'Шаблон')
        
        if self.templates_service and template_id:
            await self.templates_service.update_template(template_id, data)
            text = f"✅ Шаблон *{template_name}* обновлён!"
        else:
            text = "❌ Ошибка сохранения"
        
        keyboard = [[InlineKeyboardButton("📋 К шаблонам", callback_data="templates_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        self.clear_user_data(user_id)
        return ConversationHandler.END
    
    def _format_summary_text(self, data: Dict[str, Any]) -> str:
        """Format summary text for display"""
        text = (
            "*Отправитель:*\n"
            f"▫️ {data.get('shipFromName', '-')}\n"
            f"▫️ {data.get('shipFromAddressLine1', '-')}\n"
            f"▫️ {data.get('shipFromCity', '-')}, {data.get('shipFromState', '-')} {data.get('shipFromPostalCode', '-')}\n"
        )
        if data.get('shipFromPhone'):
            text += f"▫️ ☎ {data.get('shipFromPhone')}\n"
        
        text += (
            f"\n*Получатель:*\n"
            f"▫️ {data.get('shipToName', '-')}\n"
            f"▫️ {data.get('shipToAddressLine1', '-')}\n"
            f"▫️ {data.get('shipToCity', '-')}, {data.get('shipToState', '-')} {data.get('shipToPostalCode', '-')}\n"
        )
        if data.get('shipToPhone'):
            text += f"▫️ ☎ {data.get('shipToPhone')}\n"
        
        weight = data.get('packageWeight', 0)
        text += (
            f"\n*Посылка:*\n"
            f"▫️ Вес: {weight} oz ({weight/16:.2f} lbs)\n"
            f"▫️ Размеры: {data.get('packageLength', 0)}×{data.get('packageWidth', 0)}×{data.get('packageHeight', 0)} дюймов\n"
        )
        
        return text
    
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
    
    async def reset_and_start(self, update: Update, context) -> int:
        """Reset conversation and show start menu"""
        user_id = str(update.effective_user.id)
        self.clear_user_data(user_id)
        
        # Import here to avoid circular import
        from services.telegram_service import TelegramService
        telegram_service = TelegramService()
        await telegram_service.send_welcome_message(update.effective_chat.id)
        
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
                
                REVIEW_SUMMARY: [
                    CallbackQueryHandler(self.handle_edit_choice, pattern="^(edit_from|edit_to|edit_package|continue_to_carrier)$")
                ],
                EDIT_SECTION: [
                    CallbackQueryHandler(self.handle_specific_edit, pattern="^(edit_from_address|edit_from_location|edit_from_phone|edit_to_address|edit_to_location|edit_to_phone|edit_weight|edit_dimensions|back_to_review)$")
                ],
                
                SELECT_RATE: [
                    CallbackQueryHandler(self.select_rate, pattern="^(rate_|back_to_review_from_rates)")
                ],
                CONFIRM: [
                    CallbackQueryHandler(self.confirm_and_create, pattern="^(confirm_|back_to_rates)$")
                ],
            },
            fallbacks=[
                CommandHandler('start', self.reset_and_start),
                CommandHandler('cancel', self.cancel),
            ],
        )
