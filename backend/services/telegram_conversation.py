from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode, ChatAction
import logging
from typing import Dict, Any, List
import random
from services.ai_messages import generate_thank_you_message

# Reduce logging for speed
logging.getLogger(__name__).setLevel(logging.WARNING)
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
    TOPUP_AMOUNT,
) = range(22)

# Cache for user balances
_balance_cache = {}

class TelegramConversationHandler:
    """Handler for multi-step label creation conversation"""
    
    def __init__(self, db, orders_service, shipengine_service=None, users_service=None, templates_service=None):
        self.db = db
        self.orders_service = orders_service
        self.shipengine_service = shipengine_service
        self.users_service = users_service
        self.templates_service = templates_service
        # Note: user_data is now managed by PTB persistence via context.user_data
        # This local dict is kept for backward compatibility but will be phased out
        self.user_data: Dict[str, Dict[str, Any]] = {}
    
    async def _check_user_banned(self, user_id: str) -> bool:
        """Check if user is banned"""
        if self.users_service:
            user = await self.users_service.get_user(user_id)
            if user and user.get('is_banned', False):
                return True
        return False
    
    async def _send_banned_message(self, update: Update) -> int:
        """Send banned message and end conversation"""
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚫 *ДОСТУП ЗАПРЕЩЁН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ваш аккаунт заблокирован.\n\n"
            "Свяжитесь с поддержкой для разблокировки.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user's conversation data (local cache - for backward compatibility)"""
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
    
    def validate_english_text(self, text: str, field_name: str = "текст") -> tuple[bool, str]:
        """Validate that text contains only English characters, numbers, and basic punctuation"""
        import re
        # Allow English letters, numbers, spaces, and common punctuation
        pattern = r'^[a-zA-Z0-9\s\.,\-\'\"#@&()/\\]+$'
        if not re.match(pattern, text):
            return False, f"Пожалуйста, введите {field_name} на английском языке (латиницей)"
        if len(text.strip()) < 1:
            return False, f"Поле {field_name} не может быть пустым"
        return True, ""
    
    def validate_name(self, name: str) -> tuple[bool, str]:
        """Validate name - English only, 2-50 characters"""
        is_english, msg = self.validate_english_text(name, "имя")
        if not is_english:
            return False, msg
        if len(name.strip()) < 2:
            return False, "Имя должно содержать минимум 2 символа"
        if len(name.strip()) > 50:
            return False, "Имя должно содержать максимум 50 символов"
        return True, ""
    
    def validate_address(self, address: str) -> tuple[bool, str]:
        """Validate address - English only, 5-100 characters"""
        is_english, msg = self.validate_english_text(address, "адрес")
        if not is_english:
            return False, msg
        if len(address.strip()) < 5:
            return False, "Адрес должен содержать минимум 5 символов"
        if len(address.strip()) > 100:
            return False, "Адрес должен содержать максимум 100 символов"
        return True, ""
    
    def validate_city(self, city: str) -> tuple[bool, str]:
        """Validate city - English only, 2-50 characters"""
        is_english, msg = self.validate_english_text(city, "город")
        if not is_english:
            return False, msg
        if len(city.strip()) < 2:
            return False, "Название города должно содержать минимум 2 символа"
        if len(city.strip()) > 50:
            return False, "Название города должно содержать максимум 50 символов"
        return True, ""
    
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
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
        # Clear previous data
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
        chat_id = update.effective_chat.id
        logger.warning(f"[HANDLER] start_create_callback: user={user_id}, chat={chat_id}, returning SHIP_FROM_NAME={SHIP_FROM_NAME}")
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
        # Clear previous data
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
        
        # Edit message to remove old buttons
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Failed to edit message for user {user_id}: {e}")
        
        # Save state to MongoDB for cross-pod sync
        await self._save_state(chat_id, user_id, SHIP_FROM_NAME)
        
        return SHIP_FROM_NAME
    
    async def _save_state(self, chat_id: int, user_id: str, state: int):
        """Save conversation state to MongoDB"""
        try:
            from database import Database
            await Database.db.ptb_conversations.update_one(
                {'name': 'label_creation', 'key': [chat_id, int(user_id)]},
                {'$set': {'name': 'label_creation', 'key': [chat_id, int(user_id)], 'state': state}},
                upsert=True
            )
            logger.warning(f"[STATE] Saved state={state} for user {user_id}")
        except Exception as e:
            logger.error(f"[STATE] Failed to save: {e}")
    
    # ===== SHIP FROM ADDRESS =====
    
    async def ship_from_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        logger.warning(f"[HANDLER] ship_from_name called for user {user_id}")
        
        data = self.get_user_data(user_id)
        name = update.message.text.strip()
        
        # Validate name
        is_valid, error_msg = self.validate_name(name)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите имя заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_NAME
        
        data['shipFromName'] = name
        
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
        await self._save_state(update.effective_chat.id, user_id, SHIP_FROM_ADDRESS)
        return SHIP_FROM_ADDRESS
    
    async def ship_from_address(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        address = update.message.text.strip()
        
        # Validate address
        is_valid, error_msg = self.validate_address(address)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите адрес заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_ADDRESS
        
        data['shipFromAddressLine1'] = address
        
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
        city = update.message.text.strip()
        
        # Validate city
        is_valid, error_msg = self.validate_city(city)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите город заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_CITY
        
        data['shipFromCity'] = city
        
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
                "ZIP код должен состоять из 5 цифр.\n"
                "_Например: 94102, 10001_\n\n"
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
    
    def validate_phone(self, phone: str) -> tuple[bool, str]:
        """Validate phone number - must have 10-15 digits"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        if len(digits_only) < 10:
            return False, "Телефон должен содержать минимум 10 цифр"
        if len(digits_only) > 15:
            return False, "Телефон должен содержать максимум 15 цифр"
        
        return True, digits_only
    
    async def ship_from_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        phone = update.message.text.strip()
        if phone.lower() not in ['пропустить', 'skip']:
            # Validate phone
            is_valid, result = self.validate_phone(phone)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ *{result}*\n\nПожалуйста, введите корректный номер телефона:",
                    parse_mode=ParseMode.MARKDOWN
                )
                return SHIP_FROM_PHONE
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
            # Edit the message to remove button and show confirmation
            await query.edit_message_text(
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
        
        # Edit the message to remove the skip button
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_NAME
    
    # ===== SHIP TO ADDRESS =====
    
    async def ship_to_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        name = update.message.text.strip()
        
        # Validate name
        is_valid, error_msg = self.validate_name(name)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите имя заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_NAME
        
        data['shipToName'] = name
        
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
        address = update.message.text.strip()
        
        # Validate address
        is_valid, error_msg = self.validate_address(address)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите адрес заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_ADDRESS
        
        data['shipToAddressLine1'] = address
        
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
        city = update.message.text.strip()
        
        # Validate city
        is_valid, error_msg = self.validate_city(city)
        if not is_valid:
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\nПожалуйста, введите город заново:",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_CITY
        
        data['shipToCity'] = city
        
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
        
        logger.warning(f"[DEBUG] ship_to_state called for user {user_id}, input: '{state}'")
        
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
        logger.warning(f"[DEBUG] ship_to_state completed for user {user_id}, returning SHIP_TO_ZIP")
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
            # Validate phone
            is_valid, result = self.validate_phone(phone)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ *{result}*\n\nПожалуйста, введите корректный номер телефона:",
                    parse_mode=ParseMode.MARKDOWN
                )
                return SHIP_TO_PHONE
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
            "Введите вес в фунтах (lbs):\n"
            "_Например: 1 или 2.5_"
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
            # Edit the message to remove button and show confirmation
            await query.edit_message_text(
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
            "Введите вес в фунтах (lbs):\n"
            "_Например: 1 или 2.5_"
        )
        
        # Edit the message to remove the skip button
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return PACKAGE_WEIGHT
    
    # ===== PACKAGE DETAILS =====
    
    async def package_weight(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        try:
            weight_lbs = float(update.message.text.strip())
            if weight_lbs <= 0:
                raise ValueError()
            # Convert pounds to ounces for API
            weight_oz = weight_lbs * 16
            data['packageWeight'] = weight_oz
            data['packageWeightLbs'] = weight_lbs
        except ValueError:
            text = (
                "❌ *Некорректное значение*\n\n"
                "Вес должен быть положительным числом.\n"
                "_Например: 1 или 2.5_\n\n"
                "Пожалуйста, попробуйте еще раз:"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return PACKAGE_WEIGHT
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'weight':
            data['editing_field'] = None
            await update.message.reply_text(
                f"✅ *Вес сохранен* ({weight_lbs} lbs)",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(update.message, user_id)
            return REVIEW_SUMMARY
        
        text = (
            f"✅ *Вес сохранен* ({weight_lbs} lbs)\n\n"
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
    
    async def show_review_summary(self, message, user_id: str, from_template: bool = False, edit_message: bool = False):
        """Show summary with edit options"""
        data = self.get_user_data(user_id)
        
        if from_template:
            header = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📋 *ДАННЫЕ ИЗ ШАБЛОНА*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Проверьте данные и отредактируйте при необходимости.\n\n"
            )
        else:
            header = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📋 *ПРОВЕРКА ДАННЫХ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Пожалуйста, проверьте введенные данные перед выбором перевозчика.\n\n"
            )
        
        text = header + (
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
        
        weight_lbs = data.get('packageWeightLbs', 0) or (data.get('packageWeight', 0) / 16)
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *ПОСЫЛКА*\n"
            f"▫️ Вес: {weight_lbs:.2f} lbs\n"
            f"▫️ Размеры: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} дюймов\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать отправителя", callback_data="edit_from")],
            [InlineKeyboardButton("✏️ Редактировать получателя", callback_data="edit_to")],
            [InlineKeyboardButton("✏️ Редактировать посылку", callback_data="edit_package")],
            [InlineKeyboardButton("💾 Сохранить как шаблон", callback_data="save_template")],
            [InlineKeyboardButton("✅ Всё верно, продолжить", callback_data="continue_to_carrier")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if edit_message:
            # Edit existing message (for callbacks)
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            # Send new message (for text input handlers)
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
                "company_name": "",
                "address_line1": data.get('shipFromAddressLine1'),
                "city_locality": data.get('shipFromCity'),
                "state_province": data.get('shipFromState'),
                "postal_code": data.get('shipFromPostalCode'),
                "country_code": "US",
                "phone": data.get('shipFromPhone', ''),
            },
            "ship_to": {
                "name": data.get('shipToName'),
                "company_name": "",
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
        
        # Get user balance
        user_balance = 0.0
        if self.users_service:
            db_user = await self.users_service.get_user(user_id)
            if db_user:
                user_balance = db_user.get('balance', 0.0)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💰 *ДОСТУПНЫЕ ТАРИФЫ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Прогресс: {self.get_progress_bar(4)} (Шаг 4/4)\n\n"
            f"💳 Ваш баланс: *${user_balance:.2f}*\n\n"
            "Выберите тариф доставки:\n\n"
        )
        
        # Group rates by carrier
        rates_by_carrier = {}
        for rate in rates:
            carrier_code = rate.get('carrier_code', '').lower()
            if carrier_code not in rates_by_carrier:
                rates_by_carrier[carrier_code] = []
            rates_by_carrier[carrier_code].append(rate)
        
        # Log available carriers for debugging
        logger.info(f"Available carriers in rates: {list(rates_by_carrier.keys())}")
        for carrier, carrier_rates in rates_by_carrier.items():
            logger.info(f"  {carrier}: {len(carrier_rates)} rates")
        
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
                
                button_text = f"{config['icon']} {config['name']} {service_type} - ${total_price:.2f}"
                
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
            # Go back to review summary - edit message to show summary
            await self.show_review_summary(query.message, user_id, edit_message=True)
            return REVIEW_SUMMARY
        
        # Handle different edit types - set editing_field flag
        if edit_type == "edit_from_address":
            data['editing_field'] = 'from_address'
            await query.edit_message_text(
                "✏️ *Редактирование адреса отправителя*\n\n"
                "Введите новый адрес:\n"
                "_(Улица, номер дома, квартира)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_ADDRESS
        elif edit_type == "edit_from_location":
            data['editing_field'] = 'from_location'
            await query.edit_message_text(
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
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_PHONE
        
        elif edit_type == "edit_to_address":
            data['editing_field'] = 'to_address'
            await query.edit_message_text(
                "✏️ *Редактирование адреса получателя*\n\n"
                "Введите новый адрес:\n"
                "_(Улица, номер дома, квартира)_",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_ADDRESS
        elif edit_type == "edit_to_location":
            data['editing_field'] = 'to_location'
            await query.edit_message_text(
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
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_PHONE
        
        elif edit_type == "edit_weight":
            data['editing_field'] = 'weight'
            await query.edit_message_text(
                "✏️ *Редактирование веса*\n\n"
                "Введите новый вес в фунтах (lbs):\n"
                "_Например: 1 или 2.5_",
                parse_mode=ParseMode.MARKDOWN
            )
            return PACKAGE_WEIGHT
        elif edit_type == "edit_dimensions":
            data['editing_field'] = 'dimensions'
            await query.edit_message_text(
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
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
        data = self.get_user_data(user_id)
        
        callback_data = query.data
        
        # Handle back to review
        if callback_data == "back_to_review_from_rates":
            # Remove buttons from old message
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
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
        
        # Remove buttons from rate selection message
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        # Store selected rate
        data['selected_rate'] = selected_rate
        
        # Normalize carrier code for our enum
        carrier_code = selected_rate.get('carrier_code', '').lower()
        carrier_mapping = {
            'stamps_com': 'stampscom',
            'stamps.com': 'stampscom',
            'usps': 'usps',
            'fedex': 'fedex',
            'ups': 'ups',
            'dhl': 'dhl',
        }
        data['carrier'] = carrier_mapping.get(carrier_code, carrier_code)
        data['carrier_id'] = selected_rate.get('carrier_id', '')
        data['serviceCode'] = selected_rate.get('service_code', '')
        data['rate_id'] = selected_rate.get('rate_id', '')
        data['total_cost'] = selected_rate.get('total_amount', 0)
        
        # Get user balance
        user_balance = 0.0
        if self.users_service:
            db_user = await self.users_service.get_user(user_id)
            if db_user:
                user_balance = db_user.get('balance', 0.0)
        
        # Show confirmation
        carrier_name = selected_rate.get('carrier_friendly_name', selected_rate.get('carrier_code', ''))
        service_type = selected_rate.get('service_type', '')
        total_price = selected_rate.get('total_amount', 0)
        
        # Check if balance is sufficient
        balance_status = "✅" if user_balance >= total_price else "❌"
        balance_after = user_balance - total_price
        
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
        
        weight_lbs = data.get('packageWeightLbs', 0) or (data.get('packageWeight', 0) / 16)
        summary += (
            f"\n📦 *ПОСЫЛКА*\n"
            f"▫️ Вес: {weight_lbs:.2f} lbs\n"
            f"▫️ Размеры: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} дюймов\n"
            f"\n🚚 *ДОСТАВКА*\n"
            f"▫️ Перевозчик: {carrier_name}\n"
            f"▫️ Сервис: {service_type}\n"
            f"\n💰 *СТОИМОСТЬ: ${total_price:.2f}*\n"
            f"💳 *Ваш баланс: ${user_balance:.2f}* {balance_status}\n"
        )
        
        if user_balance >= total_price:
            summary += f"▫️ После оплаты: ${balance_after:.2f}\n"
        else:
            needed = total_price - user_balance
            summary += f"▫️ Не хватает: ${needed:.2f}\n"
        
        summary += "\n━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [
            [InlineKeyboardButton(f"✅ Оплатить ${total_price:.2f} и создать лейбл", callback_data="confirm_yes")],
            [InlineKeyboardButton("◀️ Выбрать другой тариф", callback_data="back_to_rates")],
            [InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send confirmation as NEW message
        await query.message.reply_text(
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
        
        # Check if user is banned before creating label
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
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
                needed = total_cost - current_balance
                
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *НЕДОСТАТОЧНО СРЕДСТВ*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💵 Стоимость лейбла: *${total_cost:.2f}*\n"
                    f"💰 Ваш баланс: *${current_balance:.2f}*\n\n"
                    f"📊 Необходимо пополнить: *${needed:.2f}*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💳 *Пополните баланс криптой:*\n"
                    "▫️ BTC, ETH, USDT, LTC\n"
                    "▫️ Минимум: $10"
                )
                keyboard = [
                    [InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance")],
                    [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
                ]
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
            tracking_number = result.get('trackingNumber', 'N/A')
            label_url = result.get('labelDownloadUrl', '')
            
            # Store data for potential template save
            self.get_user_data(user_id)['last_order_data'] = data.copy()
            
            success_message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *ЛЕЙБЛ СОЗДАН УСПЕШНО!*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 *Информация о доставке:*\n\n"
                f"▫️ Tracking номер:\n`{tracking_number}`\n\n"
                f"▫️ Перевозчик: {carrier_name}\n"
                f"▫️ Стоимость: ${total_cost:.2f}\n"
                f"▫️ Остаток на балансе: ${new_balance:.2f}\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            keyboard = []
            # Add download button if URL available - use callback to send via Telegram
            if label_url:
                # Store label URL for download
                data['label_url'] = label_url
                data['tracking_number'] = tracking_number
                keyboard.append([InlineKeyboardButton(f"📥 Скачать {tracking_number}.pdf", callback_data="download_label")])
            keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
            # Send AI-generated thank you message as a separate message
            try:
                thank_you_msg = await generate_thank_you_message(carrier_name, tracking_number)
                await query.message.reply_text(
                    thank_you_msg,
                    parse_mode=None  # Plain text, no formatting
                )
            except Exception as ai_err:
                logger.warning(f"Failed to send AI thank you message: {ai_err}")
            
            # Don't clear data yet - user might want to download label
            # Data will be cleared after download or going to menu
            return CONFIRM
            
        except Exception as e:
            logger.error(f"Error creating label: {e}", exc_info=True)
            error_str = str(e)
            
            # Parse carrier-specific errors
            if "carrier error" in error_str.lower() or "FedEx" in error_str or "USPS" in error_str or "UPS" in error_str:
                carrier_name = data.get('selected_rate', {}).get('carrier_friendly_name', 'перевозчик')
                error_message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *ОШИБКА ПЕРЕВОЗЧИКА*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"⚠️ *{carrier_name}* не может создать лейбл\n"
                    "для указанных данных.\n\n"
                    "*Возможные причины:*\n"
                    "▫️ Некорректный адрес\n"
                    "▫️ Недоступный маршрут\n"
                    "▫️ Ограничения sandbox режима\n\n"
                    "*Рекомендация:*\n"
                    "Попробуйте выбрать другого перевозчика\n"
                    "(USPS обычно работает стабильнее)"
                )
                keyboard = [
                    [InlineKeyboardButton("🔄 Выбрать другой тариф", callback_data="back_to_rates")],
                    [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                # Stay in CONFIRM state so back_to_rates button works
                return CONFIRM
            else:
                # Generic error
                error_text = error_str.replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                if len(error_text) > 200:
                    error_text = error_text[:200] + "..."
                error_message = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *ОШИБКА*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Не удалось создать лейбл.\n\n"
                    f"Причина: {error_text}"
                )
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="back_to_rates")],
                    [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                # Stay in CONFIRM state so back_to_rates button works
                return CONFIRM
        
        return ConversationHandler.END
    
    async def back_to_review_from_template(self, update: Update, context) -> int:
        """Return to review summary from template save prompt"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        await self.show_review_summary(query.message, user_id, edit_message=True)
        return REVIEW_SUMMARY
    
    async def save_template_prompt(self, update: Update, context) -> int:
        """Ask for template name"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        logger.info(f"save_template_prompt called for user {user_id}")
        
        # Check if we have data
        data = self.get_user_data(user_id)
        logger.info(f"User data keys: {list(data.keys())}")
        
        # Store message info for later editing
        data['template_prompt_message_id'] = query.message.message_id
        data['template_prompt_chat_id'] = query.message.chat_id
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💾 *СОХРАНИТЬ ШАБЛОН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Введите название для шаблона:\n"
            "_Например: Мой офис → Склад_"
        )
        
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_review_after_save")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return TEMPLATE_SAVE_NAME
    
    async def save_template_name(self, update: Update, context) -> int:
        """Save template with given name"""
        user_id = str(update.effective_user.id)
        template_name = update.message.text.strip()[:50]
        data = self.get_user_data(user_id)
        
        # Remove the old message with cancel button
        msg_id = data.get('template_prompt_message_id')
        chat_id = data.get('template_prompt_chat_id')
        logger.info(f"[TEMPLATE] Trying to remove cancel button. msg_id={msg_id}, chat_id={chat_id}")
        
        if msg_id and chat_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=None
                )
                logger.info(f"[TEMPLATE] Successfully removed cancel button")
            except Exception as e:
                logger.warning(f"[TEMPLATE] Could not remove cancel button: {e}")
        else:
            logger.warning(f"[TEMPLATE] No message_id or chat_id stored to remove button")
        
        # Use current data (not last_order_data) since we're saving before creating label
        order_data = data
        
        if self.templates_service:
            # Check limit
            count = await self.templates_service.get_templates_count(user_id)
            if count >= 10:
                text = (
                    "❌ *Достигнут лимит шаблонов*\n\n"
                    "У вас уже 10 шаблонов. Удалите один из существующих, чтобы создать новый."
                )
                keyboard = [
                    [InlineKeyboardButton("◀️ Назад к данным", callback_data="back_to_review_after_save")],
                    [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                return REVIEW_SUMMARY
            else:
                template = await self.templates_service.create_template(user_id, template_name, order_data)
                if template:
                    text = f"✅ Шаблон *{template_name}* сохранён!\n\nТеперь вы можете продолжить создание лейбла."
                else:
                    text = "❌ Ошибка сохранения шаблона"
                
                keyboard = [
                    [InlineKeyboardButton("✅ Продолжить → Выбрать тариф", callback_data="continue_to_carrier")],
                    [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                return REVIEW_SUMMARY
        
        return REVIEW_SUMMARY
    
    async def use_template(self, update: Update, context) -> int:
        """Use a template to create a new label - sends new message"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
        template_id = query.data.replace("tpl_use_", "")
        
        # Remove buttons from old message (keep text)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        if not self.templates_service:
            await query.message.reply_text("❌ Сервис шаблонов недоступен")
            return ConversationHandler.END
        
        template = await self.templates_service.get_template(template_id)
        if not template:
            await query.message.reply_text("❌ Шаблон не найден")
            return ConversationHandler.END
        
        # Load template data into user_data
        template_data = self.templates_service.template_to_user_data(template)
        data = self.get_user_data(user_id)
        data.update(template_data)
        data['using_template'] = template_id
        
        # Increment use count
        await self.templates_service.increment_use_count(template_id)
        
        # Show review summary with template data as NEW message
        await self.show_review_summary(query.message, user_id, from_template=True, edit_message=False)
        return REVIEW_SUMMARY
    
    async def edit_template(self, update: Update, context) -> int:
        """Edit a template - sends new message"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        template_id = query.data.replace("tpl_edit_", "")
        
        # Remove buttons from old message (keep text)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        if not self.templates_service:
            await query.message.reply_text("❌ Сервис шаблонов недоступен")
            return ConversationHandler.END
        
        template = await self.templates_service.get_template(template_id)
        if not template:
            await query.message.reply_text("❌ Шаблон не найден")
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
        
        # Send as NEW message instead of editing
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return TEMPLATE_EDIT
    
    async def save_template_changes(self, update: Update, context) -> int:
        """Save template changes - sends new message"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        template_id = data.get('editing_template_id')
        template_name = data.get('editing_template_name', 'Шаблон')
        
        # Remove buttons from old message (keep text)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        if self.templates_service and template_id:
            await self.templates_service.update_template(template_id, data)
            text = f"✅ Шаблон *{template_name}* обновлён!"
        else:
            text = "❌ Ошибка сохранения"
        
        keyboard = [[InlineKeyboardButton("📋 К шаблонам", callback_data="templates_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send as NEW message instead of editing
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        self.clear_user_data(user_id)
        return ConversationHandler.END
    
    async def download_label(self, update: Update, context) -> int:
        """Download label PDF and send via Telegram"""
        query = update.callback_query
        await query.answer("📥 Загрузка лейбла...")
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id)
        
        label_url = data.get('label_url')
        tracking_number = data.get('tracking_number', 'label')
        
        if not label_url:
            await query.message.reply_text("❌ Ссылка на лейбл не найдена")
            return ConversationHandler.END
        
        try:
            import aiohttp
            import io
            
            # Download PDF from ShipEngine
            async with aiohttp.ClientSession() as session:
                async with session.get(label_url) as response:
                    if response.status == 200:
                        pdf_data = await response.read()
                        
                        # Send as document via Telegram
                        pdf_file = io.BytesIO(pdf_data)
                        pdf_file.name = f"{tracking_number}.pdf"
                        
                        await query.message.reply_document(
                            document=pdf_file,
                            filename=f"{tracking_number}.pdf",
                            caption=f"📦 Shipping Label\nTracking: {tracking_number}"
                        )
                        
                        logger.info(f"Label sent to user {user_id}: {tracking_number}")
                    else:
                        await query.message.reply_text(f"❌ Ошибка загрузки: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error downloading label: {e}")
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
        
        # Clear data after download
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
        
        weight_lbs = data.get('packageWeightLbs', 0) or (data.get('packageWeight', 0) / 16)
        text += (
            f"\n*Посылка:*\n"
            f"▫️ Вес: {weight_lbs:.2f} lbs\n"
            f"▫️ Размеры: {data.get('packageLength', 0)}×{data.get('packageWidth', 0)}×{data.get('packageHeight', 0)} дюймов\n"
        )
        
        return text
    
    async def back_to_menu_fallback(self, update: Update, context) -> int:
        """Handle back to menu button - works like /start command"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
        self.clear_user_data(user_id)
        
        logger.info(f"back_to_menu_fallback triggered by user {user_id} - ending conversation")
        
        # Get user balance
        balance = 0.0
        if self.users_service:
            user = await self.users_service.get_user(user_id)
            if user:
                balance = user.get('balance', 0.0)
        
        # Remove buttons from current message (keep text)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.debug(f"Could not remove buttons from message: {e}")
        
        # Send new welcome message (like /start)
        from services.telegram_service import TelegramService
        telegram_service = TelegramService()
        sent_message = await telegram_service.send_welcome_message(query.message.chat_id, balance)
        
        # Store the new menu message id
        if sent_message:
            context.user_data['last_menu_message_id'] = sent_message.message_id
        
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
    
    async def reset_and_start(self, update: Update, context) -> int:
        """Reset conversation and show start menu"""
        user_id = str(update.effective_user.id)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update)
        
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
                CallbackQueryHandler(self.start_create_callback, pattern="^start_create$"),
                CallbackQueryHandler(self.use_template, pattern="^tpl_use_"),
                CallbackQueryHandler(self.edit_template, pattern="^tpl_edit_"),
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
                    CallbackQueryHandler(self.handle_edit_choice, pattern="^(edit_from|edit_to|edit_package|continue_to_carrier)$"),
                    CallbackQueryHandler(self.save_template_prompt, pattern="^save_template$")
                ],
                EDIT_SECTION: [
                    CallbackQueryHandler(self.handle_specific_edit, pattern="^(edit_from_address|edit_from_location|edit_from_phone|edit_to_address|edit_to_location|edit_to_phone|edit_weight|edit_dimensions|back_to_review)$")
                ],
                
                SELECT_RATE: [
                    CallbackQueryHandler(self.select_rate, pattern="^(rate_|back_to_review_from_rates)")
                ],
                CONFIRM: [
                    CallbackQueryHandler(self.confirm_and_create, pattern="^(confirm_yes|confirm_no|back_to_rates)$"),
                    CallbackQueryHandler(self.download_label, pattern="^download_label$"),
                ],
                
                TEMPLATE_SAVE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_template_name),
                    CallbackQueryHandler(self.handle_edit_choice, pattern="^continue_to_carrier$"),
                    CallbackQueryHandler(self.back_to_review_from_template, pattern="^back_to_review_after_save$")
                ],
                
                TEMPLATE_EDIT: [
                    CallbackQueryHandler(self.handle_edit_choice, pattern="^(edit_from|edit_to|edit_package)$"),
                    CallbackQueryHandler(self.save_template_changes, pattern="^save_template_changes$")
                ],
            },
            fallbacks=[
                CommandHandler('start', self.reset_and_start),
                CommandHandler('cancel', self.cancel),
                CallbackQueryHandler(self.back_to_menu_fallback, pattern="^back_to_menu$"),
                # Fallback text handler - checks MongoDB when PTB state is lost
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback_text_handler),
            ],
            name="label_creation",
            persistent=False,  # Disable PTB caching - we use MongoDB directly
            per_message=False,
            per_chat=True,
            per_user=True,
            allow_reentry=True,
        )
    
    async def fallback_text_handler(self, update: Update, context) -> int:
        """Fallback handler - route based on MongoDB state when PTB state is lost"""
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        # Check MongoDB for saved state
        try:
            from database import Database
            db = Database.db
            doc = await db.ptb_conversations.find_one({
                'name': 'label_creation',
                'key': [chat_id, user_id]
            })
            
            if not doc:
                logger.warning(f"[FALLBACK] No state for user {user_id}, ignoring")
                return ConversationHandler.END
            
            saved_state = doc.get('state')
            logger.warning(f"[FALLBACK] Found state={saved_state} for user {user_id}, routing...")
            
            # Map state to handler
            state_handlers = {
                SHIP_FROM_NAME: self.ship_from_name,
                SHIP_FROM_ADDRESS: self.ship_from_address,
                SHIP_FROM_CITY: self.ship_from_city,
                SHIP_FROM_STATE: self.ship_from_state,
                SHIP_FROM_ZIP: self.ship_from_zip,
                SHIP_FROM_PHONE: self.ship_from_phone,
                SHIP_TO_NAME: self.ship_to_name,
                SHIP_TO_ADDRESS: self.ship_to_address,
                SHIP_TO_CITY: self.ship_to_city,
                SHIP_TO_STATE: self.ship_to_state,
                SHIP_TO_ZIP: self.ship_to_zip,
                SHIP_TO_PHONE: self.ship_to_phone,
                PACKAGE_WEIGHT: self.package_weight,
                PACKAGE_DIMENSIONS: self.package_dimensions,
                TEMPLATE_SAVE_NAME: self.save_template_name,
            }
            
            handler = state_handlers.get(saved_state)
            if handler:
                result = await handler(update, context)
                # Save new state to MongoDB
                if result != ConversationHandler.END:
                    await db.ptb_conversations.update_one(
                        {'name': 'label_creation', 'key': [chat_id, user_id]},
                        {'$set': {'state': result}},
                        upsert=True
                    )
                return result
            
            logger.warning(f"[FALLBACK] Unknown state {saved_state}")
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"[FALLBACK] Error: {e}")
            return ConversationHandler.END
