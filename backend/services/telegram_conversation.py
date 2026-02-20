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
from datetime import datetime, timezone
from services.ai_messages import generate_thank_you_message
from services.localization import t, get_user_language, DEFAULT_LANGUAGE

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
    
    async def _send_banned_message(self, update: Update, context=None) -> int:
        """Send banned message and end conversation"""
        user_id = str(update.effective_user.id)
        lang = await self._get_lang(user_id, context) if context else "ru"
        
        if lang == "en":
            message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🚫 *ACCESS DENIED*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Your account is blocked.\n\n"
                "Contact support for unblocking.\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
        else:
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
    
    async def _get_lang(self, user_id: str, context=None) -> str:
        """Get user's language from context or database"""
        if context and context.user_data.get('language'):
            return context.user_data.get('language')
        # Fallback to database
        try:
            lang = await get_user_language(self.db, user_id)
            if context:
                context.user_data['language'] = lang
            return lang
        except Exception:
            return DEFAULT_LANGUAGE
    
    def get_user_data(self, user_id: str, context=None) -> Dict[str, Any]:
        """Get user's conversation data. 
        Uses context.user_data if available (persisted via MongoPersistence),
        otherwise falls back to local dict (for backward compatibility)
        """
        if context is not None:
            # Use PTB's context.user_data which is persisted via MongoPersistence
            return context.user_data
        # Fallback to local dict (should be avoided)
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        return self.user_data[user_id]
    
    def clear_user_data(self, user_id: str, context=None):
        """Clear user's conversation data"""
        if context is not None:
            context.user_data.clear()
        elif user_id in self.user_data:
            del self.user_data[user_id]
        
        # Also clear pending label order flag from MongoDB
        try:
            import asyncio
            from database import Database
            if Database.db is not None:
                asyncio.create_task(
                    Database.db.pending_label_orders.delete_one({"telegram_id": user_id})
                )
        except Exception:
            pass  # Silently ignore errors during cleanup
    
    def get_progress_bar(self, step: int) -> str:
        """Generate progress bar for steps"""
        total_steps = 4
        filled = "🟦" * step
        empty = "⬜" * (total_steps - step)
        return f"{filled}{empty}"
    
    def validate_english_text(self, text: str, field_name: str = "текст", lang: str = "ru") -> tuple[bool, str]:
        """Validate that text contains only English characters, numbers, and basic punctuation"""
        import re
        # Allow English letters, numbers, spaces, and common punctuation
        pattern = r'^[a-zA-Z0-9\s\.,\-\'\"#@&()/\\]+$'
        if not re.match(pattern, text):
            if lang == "en":
                return False, f"Please enter {field_name} in English (Latin characters)"
            return False, f"Пожалуйста, введите {field_name} на английском языке (латиницей)"
        if len(text.strip()) < 1:
            if lang == "en":
                return False, f"The {field_name} field cannot be empty"
            return False, f"Поле {field_name} не может быть пустым"
        return True, ""
    
    def validate_name(self, name: str, lang: str = "ru") -> tuple[bool, str]:
        """Validate name - English only, 2-50 characters"""
        field_name = "name" if lang == "en" else "имя"
        is_english, msg = self.validate_english_text(name, field_name, lang)
        if not is_english:
            return False, msg
        if len(name.strip()) < 2:
            if lang == "en":
                return False, "Name must be at least 2 characters"
            return False, "Имя должно содержать минимум 2 символа"
        if len(name.strip()) > 50:
            if lang == "en":
                return False, "Name must be at most 50 characters"
            return False, "Имя должно содержать максимум 50 символов"
        return True, ""
    
    def validate_address(self, address: str, lang: str = "ru") -> tuple[bool, str]:
        """Validate address - English only, 5-100 characters"""
        field_name = "address" if lang == "en" else "адрес"
        is_english, msg = self.validate_english_text(address, field_name, lang)
        if not is_english:
            return False, msg
        if len(address.strip()) < 5:
            if lang == "en":
                return False, "Address must be at least 5 characters"
            return False, "Адрес должен содержать минимум 5 символов"
        if len(address.strip()) > 100:
            if lang == "en":
                return False, "Address must be at most 100 characters"
            return False, "Адрес должен содержать максимум 100 символов"
        return True, ""
    
    def validate_city(self, city: str, lang: str = "ru") -> tuple[bool, str]:
        """Validate city - English only, 2-50 characters"""
        field_name = "city" if lang == "en" else "город"
        is_english, msg = self.validate_english_text(city, field_name, lang)
        if not is_english:
            return False, msg
        if len(city.strip()) < 2:
            if lang == "en":
                return False, "City name must be at least 2 characters"
            return False, "Название города должно содержать минимум 2 символа"
        if len(city.strip()) > 50:
            if lang == "en":
                return False, "City name must be at most 50 characters"
            return False, "Название города должно содержать максимум 50 символов"
        return True, ""
    
    def validate_phone(self, phone: str, lang: str = "ru") -> tuple[bool, str]:
        """Validate phone number - must have 10-15 digits"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        if len(digits_only) < 10:
            if lang == "en":
                return False, "Phone must have at least 10 digits"
            return False, "Телефон должен содержать минимум 10 цифр"
        if len(digits_only) > 15:
            if lang == "en":
                return False, "Phone must have at most 15 digits"
            return False, "Телефон должен содержать максимум 15 цифр"
        
        return True, digits_only
    
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
            return await self._send_banned_message(update, context)
        
        # Clear previous data
        self.clear_user_data(user_id, context)
        
        # Ensure user exists and get language
        db_user = await self._ensure_user(update)
        balance = db_user.get('balance', 0.0) if db_user else 0.0
        lang = await self._get_lang(user_id, context)
        
        if lang == "en":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📦 *CREATE SHIPPING LABEL*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Your balance: *${balance:.2f}*\n\n"
                f"Progress: {self.get_progress_bar(1)} (Step 1/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📍 *STEP 1: SENDER ADDRESS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 1.1:* Full name\n\n"
                "Please enter the sender's full name:"
            )
        else:
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
            return await self._send_banned_message(update, context)
        
        # Clear previous data
        self.clear_user_data(user_id, context)
        
        # Ensure user exists and get language
        db_user = await self._ensure_user(update)
        balance = db_user.get('balance', 0.0) if db_user else 0.0
        lang = await self._get_lang(user_id, context)
        
        if lang == "en":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📦 *CREATE SHIPPING LABEL*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Your balance: *${balance:.2f}*\n\n"
                f"Progress: {self.get_progress_bar(1)} (Step 1/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📍 *STEP 1: SENDER ADDRESS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 1.1:* Full name\n\n"
                "Please enter the sender's full name:"
            )
        else:
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
        
        return SHIP_FROM_NAME
    
    # ===== SHIP FROM ADDRESS =====
    
    async def ship_from_name(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        logger.warning(f"[HANDLER] ship_from_name called for user {user_id}")
        
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        name = update.message.text.strip()
        
        # Validate name
        is_valid, error_msg = self.validate_name(name, lang)
        if not is_valid:
            retry_msg = "Please enter the name again:" if lang == "en" else "Пожалуйста, введите имя заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_NAME
        
        data['shipFromName'] = name
        
        # Check if we're in edit mode - editing only name
        if data.get('editing_field') == 'from_name_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *Sender name saved*\n\n"
                "▫️ *Substep 1.2:* Address\n\n"
                "Enter the sender's address:\n"
                "_(Street, building, apartment)_"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        address = update.message.text.strip()
        
        # Validate address
        is_valid, error_msg = self.validate_address(address, lang)
        if not is_valid:
            retry_msg = "Please enter the address again:" if lang == "en" else "Пожалуйста, введите адрес заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_ADDRESS
        
        data['shipFromAddressLine1'] = address
        
        # Check if we're in edit mode - editing address chain
        if data.get('editing_field') == 'from_address':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *Address saved*\n\n"
                "▫️ *Substep 1.3:* City\n\n"
                "Enter the city name:"
            )
        else:
            text = (
                "✅ *Адрес сохранен*\n\n"
                "▫️ *Подшаг 1.3:* Город\n\n"
                "Введите название города:"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_CITY
    
    async def ship_from_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        city = update.message.text.strip()
        
        # Validate city
        is_valid, error_msg = self.validate_city(city, lang)
        if not is_valid:
            retry_msg = "Please enter the city again:" if lang == "en" else "Пожалуйста, введите город заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_FROM_CITY
        
        data['shipFromCity'] = city
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'from_city_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *City saved*\n\n"
                "▫️ *Substep 1.4:* State\n\n"
                "Enter state code (2 letters):\n"
                "_Example: CA, NY, TX, FL_"
            )
        else:
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
        lang = await self._get_lang(user_id, context)
        state = update.message.text.strip().upper()
        
        if len(state) != 2 or not state.isalpha():
            if lang == "en":
                text = (
                    "❌ *Invalid format*\n\n"
                    "State code must be 2 letters.\n"
                    "_Example: CA, NY, TX_\n\n"
                    "Please try again:"
                )
            else:
                text = (
                    "❌ *Некорректный формат*\n\n"
                    "Код штата должен состоять из 2 букв.\n"
                    "_Например: CA, NY, TX_\n\n"
                    "Пожалуйста, попробуйте еще раз:"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_STATE
        data = self.get_user_data(user_id, context)
        data['shipFromState'] = state
        
        # Check if we're in edit mode - editing location chain (city -> state -> zip)
        if data.get('editing_field') == 'from_location':
            if lang == "en":
                text = (
                    "✅ *State saved*\n\n"
                    "▫️ ZIP code\n\n"
                    "Enter ZIP code (5 digits):"
                )
            else:
                text = (
                    "✅ *Штат сохранен*\n\n"
                    "▫️ ZIP код\n\n"
                    "Введите почтовый индекс (5 цифр):"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_ZIP
        
        if lang == "en":
            text = (
                "✅ *State saved*\n\n"
                "▫️ *Substep 1.5:* ZIP code\n\n"
                "Enter ZIP code (5 digits):\n"
                "_Example: 94102, 10001, 78701_"
            )
        else:
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
        lang = await self._get_lang(user_id, context)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            if lang == "en":
                text = (
                    "❌ *Invalid format*\n\n"
                    "ZIP code must be 5 digits.\n"
                    "_Example: 94102, 10001_\n\n"
                    "Please try again:"
                )
            else:
                text = (
                    "❌ *Некорректный формат*\n\n"
                    "ZIP код должен состоять из 5 цифр.\n"
                    "_Например: 94102, 10001_\n\n"
                    "Пожалуйста, попробуйте еще раз:"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_ZIP
        data = self.get_user_data(user_id, context)
        data['shipFromPostalCode'] = zip_code
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'from_location':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *ZIP code saved*\n\n"
                "▫️ *Substep 1.6:* Phone (optional)\n\n"
                "Enter sender's phone number or press the button:"
            )
            skip_btn = "⏭️ Skip (generate random)"
        else:
            text = (
                "✅ *ZIP код сохранен*\n\n"
                "▫️ *Подшаг 1.6:* Телефон (опционально)\n\n"
                "Введите контактный телефон отправителя или нажмите кнопку:"
            )
            skip_btn = "⏭️ Пропустить (сгенерировать случайный)"
        
        keyboard = [
            [InlineKeyboardButton(skip_btn, callback_data="skip_from_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return SHIP_FROM_PHONE
    
    async def ship_from_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        phone = update.message.text.strip()
        if phone.lower() not in ['пропустить', 'skip']:
            # Validate phone
            is_valid, result = self.validate_phone(phone, lang)
            if not is_valid:
                retry_msg = "Please enter a valid phone number:" if lang == "en" else "Пожалуйста, введите корректный номер телефона:"
                await update.message.reply_text(
                    f"❌ *{result}*\n\n{retry_msg}",
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
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *STEP 1 COMPLETED*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Progress: {self.get_progress_bar(2)} (Step 2/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📍 *STEP 2: RECIPIENT ADDRESS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 2.1:* Full name\n\n"
                "Enter the recipient's full name:"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        # Generate random phone
        random_phone = self.generate_random_phone()
        data['shipFromPhone'] = random_phone
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'from_phone':
            data['editing_field'] = None
            # Edit the message to remove button and show confirmation
            auto_gen_msg = "(auto-generated)" if lang == "en" else "(сгенерирован автоматически)"
            phone_saved_msg = "Phone saved" if lang == "en" else "Телефон сохранен"
            await query.edit_message_text(
                f"✅ *{phone_saved_msg}:* {random_phone}\n_{auto_gen_msg}_",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(query.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                f"✅ *Phone saved:* {random_phone}\n"
                "_(auto-generated)_\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *STEP 1 COMPLETED*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Progress: {self.get_progress_bar(2)} (Step 2/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📍 *STEP 2: RECIPIENT ADDRESS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 2.1:* Full name\n\n"
                "Enter the recipient's full name:"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        name = update.message.text.strip()
        
        # Validate name
        is_valid, error_msg = self.validate_name(name, lang)
        if not is_valid:
            retry_msg = "Please enter the name again:" if lang == "en" else "Пожалуйста, введите имя заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_NAME
        
        data['shipToName'] = name
        
        # Check if we're in edit mode - editing only name
        if data.get('editing_field') == 'to_name_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *Recipient name saved*\n\n"
                "▫️ *Substep 2.2:* Address\n\n"
                "Enter the recipient's address:\n"
                "_(Street, building, apartment)_"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        address = update.message.text.strip()
        
        # Validate address
        is_valid, error_msg = self.validate_address(address, lang)
        if not is_valid:
            retry_msg = "Please enter the address again:" if lang == "en" else "Пожалуйста, введите адрес заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_ADDRESS
        
        data['shipToAddressLine1'] = address
        
        # Check if we're in edit mode - editing address only
        if data.get('editing_field') == 'to_address':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *Address saved*\n\n"
                "▫️ *Substep 2.3:* City\n\n"
                "Enter the city name:"
            )
        else:
            text = (
                "✅ *Адрес сохранен*\n\n"
                "▫️ *Подшаг 2.3:* Город\n\n"
                "Введите название города:"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_CITY
    
    async def ship_to_city(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        city = update.message.text.strip()
        
        # Validate city
        is_valid, error_msg = self.validate_city(city, lang)
        if not is_valid:
            retry_msg = "Please enter the city again:" if lang == "en" else "Пожалуйста, введите город заново:"
            await update.message.reply_text(
                f"❌ *{error_msg}*\n\n{retry_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            return SHIP_TO_CITY
        
        data['shipToCity'] = city
        
        # Check if we're in edit mode - editing city only
        if data.get('editing_field') == 'to_city_only':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *City saved*\n\n"
                "▫️ *Substep 2.4:* State\n\n"
                "Enter state code (2 letters):\n"
                "_Example: CA, NY, TX, FL_"
            )
        else:
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
        lang = await self._get_lang(user_id, context)
        state = update.message.text.strip().upper()
        
        if len(state) != 2 or not state.isalpha():
            if lang == "en":
                text = (
                    "❌ *Invalid format*\n\n"
                    "State code must be 2 letters.\n\n"
                    "Please try again:"
                )
            else:
                text = (
                    "❌ *Некорректный формат*\n\n"
                    "Код штата должен состоять из 2 букв.\n\n"
                    "Пожалуйста, попробуйте еще раз:"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_STATE
        data = self.get_user_data(user_id, context)
        data['shipToState'] = state
        
        # Check if we're in edit mode - editing location chain (city -> state -> zip)
        if data.get('editing_field') == 'to_location':
            if lang == "en":
                text = (
                    "✅ *State saved*\n\n"
                    "▫️ ZIP code\n\n"
                    "Enter ZIP code (5 digits):"
                )
            else:
                text = (
                    "✅ *Штат сохранен*\n\n"
                    "▫️ ZIP код\n\n"
                    "Введите почтовый индекс (5 цифр):"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_ZIP
        
        if lang == "en":
            text = (
                "✅ *State saved*\n\n"
                "▫️ *Substep 2.5:* ZIP code\n\n"
                "Enter ZIP code (5 digits):"
            )
        else:
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
        lang = await self._get_lang(user_id, context)
        zip_code = update.message.text.strip()
        
        if not zip_code.isdigit() or len(zip_code) != 5:
            if lang == "en":
                text = (
                    "❌ *Invalid format*\n\n"
                    "ZIP code must be exactly 5 digits.\n\n"
                    "Please try again:"
                )
            else:
                text = (
                    "❌ *Некорректный формат*\n\n"
                    "ZIP код должен содержать ровно 5 цифр.\n\n"
                    "Пожалуйста, попробуйте еще раз:"
                )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_ZIP
        data = self.get_user_data(user_id, context)
        data['shipToPostalCode'] = zip_code
        
        # Check if we're in edit mode - editing location chain
        if data.get('editing_field') == 'to_location':
            data['editing_field'] = None
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "✅ *ZIP code saved*\n\n"
                "▫️ *Substep 2.6:* Phone (optional)\n\n"
                "Enter recipient's phone number or press the button:"
            )
            skip_btn = "⏭️ Skip (generate random)"
        else:
            text = (
                "✅ *ZIP код сохранен*\n\n"
                "▫️ *Подшаг 2.6:* Телефон (опционально)\n\n"
                "Введите контактный телефон получателя или нажмите кнопку:"
            )
            skip_btn = "⏭️ Пропустить (сгенерировать случайный)"
        
        keyboard = [
            [InlineKeyboardButton(skip_btn, callback_data="skip_to_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return SHIP_TO_PHONE
    
    async def ship_to_phone(self, update: Update, context) -> int:
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        phone = update.message.text.strip()
        if phone.lower() not in ['пропустить', 'skip']:
            # Validate phone
            is_valid, result = self.validate_phone(phone, lang)
            if not is_valid:
                retry_msg = "Please enter a valid phone number:" if lang == "en" else "Пожалуйста, введите корректный номер телефона:"
                await update.message.reply_text(
                    f"❌ *{result}*\n\n{retry_msg}",
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
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *STEP 2 COMPLETED*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Progress: {self.get_progress_bar(3)} (Step 3/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📦 *STEP 3: PACKAGE DETAILS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 3.1:* Package weight\n\n"
                "Enter the weight in pounds (lbs):\n"
                "_Example: 1 or 2.5_"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        # Generate random phone
        random_phone = self.generate_random_phone()
        data['shipToPhone'] = random_phone
        
        # Check if we're in edit mode
        if data.get('editing_field') == 'to_phone':
            data['editing_field'] = None
            # Edit the message to remove button and show confirmation
            auto_gen_msg = "(auto-generated)" if lang == "en" else "(сгенерирован автоматически)"
            phone_saved_msg = "Phone saved" if lang == "en" else "Телефон сохранен"
            await query.edit_message_text(
                f"✅ *{phone_saved_msg}:* {random_phone}\n_{auto_gen_msg}_",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(query.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                f"✅ *Phone saved:* {random_phone}\n"
                "_(auto-generated)_\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *STEP 2 COMPLETED*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Progress: {self.get_progress_bar(3)} (Step 3/4)\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📦 *STEP 3: PACKAGE DETAILS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "▫️ *Substep 3.1:* Package weight\n\n"
                "Enter the weight in pounds (lbs):\n"
                "_Example: 1 or 2.5_"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        try:
            weight_lbs = float(update.message.text.strip())
            if weight_lbs <= 0:
                raise ValueError()
            # Convert pounds to ounces for API
            weight_oz = weight_lbs * 16
            data['packageWeight'] = weight_oz
            data['packageWeightLbs'] = weight_lbs
        except ValueError:
            if lang == "en":
                text = (
                    "❌ *Invalid value*\n\n"
                    "Weight must be a positive number.\n"
                    "_Example: 1 or 2.5_\n\n"
                    "Please try again:"
                )
            else:
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
            weight_saved_msg = "Weight saved" if lang == "en" else "Вес сохранен"
            await update.message.reply_text(
                f"✅ *{weight_saved_msg}* ({weight_lbs} lbs)",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.show_review_summary(update.message, user_id, context)
            return REVIEW_SUMMARY
        
        if lang == "en":
            text = (
                f"✅ *Weight saved* ({weight_lbs} lbs)\n\n"
                "▫️ *Substep 3.2:* Package dimensions\n\n"
                "Enter dimensions separated by space in inches:\n"
                "*Length Width Height*\n\n"
                "_Example: 12 8 6_"
            )
        else:
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
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
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
            if lang == "en":
                text = (
                    "❌ *Invalid format*\n\n"
                    "Enter 3 positive numbers separated by space.\n"
                    "_Format: Length Width Height_\n"
                    "_Example: 12 8 6_\n\n"
                    "Please try again:"
                )
            else:
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
            dims_saved_msg = "Dimensions saved" if lang == "en" else "Размеры сохранены"
            inches_msg = "inches" if lang == "en" else "дюймов"
            await update.message.reply_text(
                f"✅ *{dims_saved_msg}* ({length}×{width}×{height} {inches_msg})",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Show review summary
        await self.show_review_summary(update.message, user_id, context)
        return REVIEW_SUMMARY
    
    async def show_review_summary(self, message, user_id: str, context=None, from_template: bool = False, edit_message: bool = False):
        """Show summary with edit options"""
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context) if context else "ru"
        
        if from_template:
            if lang == "en":
                header = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 *DATA FROM TEMPLATE*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Check the data and edit if necessary.\n\n"
                )
            else:
                header = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 *ДАННЫЕ ИЗ ШАБЛОНА*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Проверьте данные и отредактируйте при необходимости.\n\n"
                )
        else:
            if lang == "en":
                header = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 *REVIEW DATA*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Please check the data before selecting a carrier.\n\n"
                )
            else:
                header = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 *ПРОВЕРКА ДАННЫХ*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Пожалуйста, проверьте введенные данные перед выбором перевозчика.\n\n"
                )
        
        # Localized labels
        if lang == "en":
            sender_lbl = "SENDER"
            recipient_lbl = "RECIPIENT"
            package_lbl = "PACKAGE"
            name_lbl = "Name"
            address_lbl = "Address"
            city_lbl = "City"
            phone_lbl = "Phone"
            weight_lbl = "Weight"
            dims_lbl = "Dimensions"
            inches_lbl = "inches"
            action_lbl = "Choose action:"
        else:
            sender_lbl = "ОТПРАВИТЕЛЬ"
            recipient_lbl = "ПОЛУЧАТЕЛЬ"
            package_lbl = "ПОСЫЛКА"
            name_lbl = "Имя"
            address_lbl = "Адрес"
            city_lbl = "Город"
            phone_lbl = "Телефон"
            weight_lbl = "Вес"
            dims_lbl = "Размеры"
            inches_lbl = "дюймов"
            action_lbl = "Выберите действие:"
        
        text = header + (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *{sender_lbl}*\n"
            f"▫️ {name_lbl}: {data.get('shipFromName')}\n"
            f"▫️ {address_lbl}: {data.get('shipFromAddressLine1')}\n"
            f"▫️ {city_lbl}: {data.get('shipFromCity')}, {data.get('shipFromState')} {data.get('shipFromPostalCode')}\n"
        )
        
        if data.get('shipFromPhone'):
            text += f"▫️ {phone_lbl}: {data.get('shipFromPhone')}\n"
        
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *{recipient_lbl}*\n"
            f"▫️ {name_lbl}: {data.get('shipToName')}\n"
            f"▫️ {address_lbl}: {data.get('shipToAddressLine1')}\n"
            f"▫️ {city_lbl}: {data.get('shipToCity')}, {data.get('shipToState')} {data.get('shipToPostalCode')}\n"
        )
        
        if data.get('shipToPhone'):
            text += f"▫️ {phone_lbl}: {data.get('shipToPhone')}\n"
        
        weight_lbs = data.get('packageWeightLbs', 0) or (data.get('packageWeight', 0) / 16)
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *{package_lbl}*\n"
            f"▫️ {weight_lbl}: {weight_lbs:.2f} lbs\n"
            f"▫️ {dims_lbl}: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} {inches_lbl}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{action_lbl}"
        )
        
        if lang == "en":
            keyboard = [
                [InlineKeyboardButton("✏️ Edit sender", callback_data="edit_from")],
                [InlineKeyboardButton("✏️ Edit recipient", callback_data="edit_to")],
                [InlineKeyboardButton("✏️ Edit package", callback_data="edit_package")],
                [InlineKeyboardButton("💾 Save as template", callback_data="save_template")],
                [InlineKeyboardButton("✅ All correct, continue", callback_data="continue_to_carrier")],
                [InlineKeyboardButton("🏠 Main menu", callback_data="back_to_menu")]
            ]
        else:
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
        
        user_id = str(update.effective_user.id)
        lang = await self._get_lang(user_id, context)
        edit_choice = query.data
        
        if edit_choice == "continue_to_carrier":
            data = self.get_user_data(user_id, context)
            
            # Show loading message
            loading_msg = "Loading rates..." if lang == "en" else "Получаю тарифы..."
            wait_msg = "Please wait." if lang == "en" else "Пожалуйста, подождите."
            await query.edit_message_text(
                f"⏳ *{loading_msg}*\n\n{wait_msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Fetch rates from ShipEngine
            try:
                rates = await self._fetch_rates(data)
                
                if not rates:
                    if lang == "en":
                        text = (
                            "❌ *No rates found*\n\n"
                            "Sorry, we couldn't get rates for this route.\n"
                            "Please check the addresses and try again."
                        )
                        back_btn = "◀️ Back to review"
                    else:
                        text = (
                            "❌ *Тарифы не найдены*\n\n"
                            "К сожалению, не удалось получить тарифы для данного маршрута.\n"
                            "Пожалуйста, проверьте адреса и попробуйте снова."
                        )
                        back_btn = "◀️ Назад к проверке"
                    keyboard = [[InlineKeyboardButton(back_btn, callback_data="back_to_review_from_rates")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                    return SELECT_RATE
                
                # Store rates in user data
                data['available_rates'] = rates
                
                # Show rates
                await self._show_rates(query, user_id, rates, context)
                return SELECT_RATE
                
            except Exception as e:
                logger.error(f"Error fetching rates: {e}")
                
                # Notify admin about error
                try:
                    from services.admin_notifications import notify_user_error
                    tg_user = update.effective_user
                    await notify_user_error(
                        telegram_id=user_id,
                        username=tg_user.username if tg_user else None,
                        error_type="Ошибка получения тарифов",
                        error_message=str(e),
                        context="ShipEngine API"
                    )
                except Exception as admin_err:
                    logger.warning(f"Failed to send admin error notification: {admin_err}")
                
                if lang == "en":
                    text = (
                        "❌ *Error loading rates*\n\n"
                        f"Reason: {str(e)}\n\n"
                        "Try again later or check your data."
                    )
                    back_btn = "◀️ Back to review"
                else:
                    text = (
                        "❌ *Ошибка получения тарифов*\n\n"
                        f"Причина: {str(e)}\n\n"
                        "Попробуйте позже или проверьте данные."
                    )
                    back_btn = "◀️ Назад к проверке"
                keyboard = [[InlineKeyboardButton(back_btn, callback_data="back_to_review_from_rates")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                return SELECT_RATE
        
        # Show edit options for the selected section
        if edit_choice == "edit_from":
            if lang == "en":
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✏️ *EDIT SENDER*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "What do you want to change?"
                )
                keyboard = [
                    [InlineKeyboardButton("📝 Address", callback_data="edit_from_address")],
                    [InlineKeyboardButton("📍 City and state", callback_data="edit_from_location")],
                    [InlineKeyboardButton("📞 Phone", callback_data="edit_from_phone")],
                    [InlineKeyboardButton("◀️ Back to review", callback_data="back_to_review")]
                ]
            else:
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
            if lang == "en":
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✏️ *EDIT RECIPIENT*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "What do you want to change?"
                )
                keyboard = [
                    [InlineKeyboardButton("📝 Address", callback_data="edit_to_address")],
                    [InlineKeyboardButton("📍 City and state", callback_data="edit_to_location")],
                    [InlineKeyboardButton("📞 Phone", callback_data="edit_to_phone")],
                    [InlineKeyboardButton("◀️ Back to review", callback_data="back_to_review")]
                ]
            else:
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
            if lang == "en":
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✏️ *EDIT PACKAGE*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "What do you want to change?"
                )
                keyboard = [
                    [InlineKeyboardButton("⚖️ Weight", callback_data="edit_weight")],
                    [InlineKeyboardButton("📏 Dimensions", callback_data="edit_dimensions")],
                    [InlineKeyboardButton("◀️ Back to review", callback_data="back_to_review")]
                ]
            else:
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
            if lang == "en":
                text = (
                    "❌ Session expired.\n\n"
                    "Please start creating a label again:"
                )
                keyboard = [
                    [InlineKeyboardButton("📦 Create label", callback_data="start_create")]
                ]
            else:
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
    
    async def _show_rates(self, query, user_id: str, rates: List[Dict[str, Any]], context=None):
        """Display available rates with prices - 4 per carrier"""
        lang = await self._get_lang(user_id, context) if context else "ru"
        
        # Carrier display settings - map carrier codes to display info
        carrier_config = {
            'stamps_com': {'icon': '📦', 'name': 'USPS'},
            'usps': {'icon': '📦', 'name': 'USPS'},
            'fedex': {'icon': '✈️', 'name': 'FedEx'},
            'fedex_walleted': {'icon': '✈️', 'name': 'FedEx'},
            'ups': {'icon': '🚚', 'name': 'UPS'},
            'globalpost': {'icon': '🌍', 'name': 'GlobalPost'},
        }
        
        # Popular services to prioritize (in order of priority)
        popular_services = {
            'stamps_com': ['usps_ground_advantage', 'usps_priority_mail', 'usps_first_class_mail', 'usps_priority_mail_express'],
            'usps': ['usps_ground_advantage', 'usps_priority_mail', 'usps_first_class_mail', 'usps_priority_mail_express'],
            'fedex': ['fedex_ground', 'fedex_home_delivery', 'fedex_2day', 'fedex_express_saver'],
            'fedex_walleted': ['fedex_ground', 'fedex_home_delivery', 'fedex_2day', 'fedex_express_saver'],
            'ups': ['ups_ground', 'ups_3_day_select', 'ups_2nd_day_air', 'ups_next_day_air_saver'],
            'globalpost': [],
        }
        
        # Get user balance
        user_balance = 0.0
        if self.users_service:
            db_user = await self.users_service.get_user(user_id)
            if db_user:
                user_balance = db_user.get('balance', 0.0)
        
        if lang == "en":
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💰 *AVAILABLE RATES*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Progress: {self.get_progress_bar(4)} (Step 4/4)\n\n"
                f"💳 Your balance: *${user_balance:.2f}*\n\n"
                "Select shipping rate:\n\n"
            )
            back_btn = "◀️ Back to review"
        else:
            text = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💰 *ДОСТУПНЫЕ ТАРИФЫ*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Прогресс: {self.get_progress_bar(4)} (Шаг 4/4)\n\n"
                f"💳 Ваш баланс: *${user_balance:.2f}*\n\n"
                "Выберите тариф доставки:\n\n"
            )
            back_btn = "◀️ Назад к проверке"
        
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
        data = self.get_user_data(user_id, context)
        data['rate_map'] = {}
        
        # Process each carrier - include all possible carrier codes
        for carrier_code in ['stamps_com', 'usps', 'fedex', 'fedex_walleted', 'ups']:
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
        
        keyboard.append([InlineKeyboardButton(back_btn, callback_data="back_to_review_from_rates")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_specific_edit(self, update: Update, context) -> int:
        """Handle specific field edit choice"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        lang = await self._get_lang(user_id, context)
        
        edit_type = query.data
        
        if edit_type == "back_to_review":
            # Go back to review summary - edit message to show summary
            await self.show_review_summary(query.message, user_id, context, edit_message=True)
            return REVIEW_SUMMARY
        
        # Handle different edit types - set editing_field flag
        if edit_type == "edit_from_address":
            data['editing_field'] = 'from_address'
            if lang == "en":
                text = (
                    "✏️ *Edit sender address*\n\n"
                    "Enter new address:\n"
                    "_(Street, building, apartment)_"
                )
            else:
                text = (
                    "✏️ *Редактирование адреса отправителя*\n\n"
                    "Введите новый адрес:\n"
                    "_(Улица, номер дома, квартира)_"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_ADDRESS
        elif edit_type == "edit_from_location":
            data['editing_field'] = 'from_location'
            if lang == "en":
                text = (
                    "✏️ *Edit sender city*\n\n"
                    "Enter new city:"
                )
            else:
                text = (
                    "✏️ *Редактирование города отправителя*\n\n"
                    "Введите новый город:"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_CITY
        elif edit_type == "edit_from_phone":
            data['editing_field'] = 'from_phone'
            if lang == "en":
                text = "✏️ *Edit sender phone*\n\nEnter new phone or press the button:"
                skip_btn = "⏭️ Skip (generate random)"
            else:
                text = "✏️ *Редактирование телефона отправителя*\n\nВведите новый телефон или нажмите кнопку:"
                skip_btn = "⏭️ Пропустить (сгенерировать случайный)"
            keyboard = [
                [InlineKeyboardButton(skip_btn, callback_data="skip_from_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_FROM_PHONE
        
        elif edit_type == "edit_to_address":
            data['editing_field'] = 'to_address'
            if lang == "en":
                text = (
                    "✏️ *Edit recipient address*\n\n"
                    "Enter new address:\n"
                    "_(Street, building, apartment)_"
                )
            else:
                text = (
                    "✏️ *Редактирование адреса получателя*\n\n"
                    "Введите новый адрес:\n"
                    "_(Улица, номер дома, квартира)_"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_ADDRESS
        elif edit_type == "edit_to_location":
            data['editing_field'] = 'to_location'
            if lang == "en":
                text = (
                    "✏️ *Edit recipient city*\n\n"
                    "Enter new city:"
                )
            else:
                text = (
                    "✏️ *Редактирование города получателя*\n\n"
                    "Введите новый город:"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_CITY
        elif edit_type == "edit_to_phone":
            data['editing_field'] = 'to_phone'
            if lang == "en":
                text = "✏️ *Edit recipient phone*\n\nEnter new phone or press the button:"
                skip_btn = "⏭️ Skip (generate random)"
            else:
                text = "✏️ *Редактирование телефона получателя*\n\nВведите новый телефон или нажмите кнопку:"
                skip_btn = "⏭️ Пропустить (сгенерировать случайный)"
            keyboard = [
                [InlineKeyboardButton(skip_btn, callback_data="skip_to_phone")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return SHIP_TO_PHONE
        
        elif edit_type == "edit_weight":
            data['editing_field'] = 'weight'
            if lang == "en":
                text = (
                    "✏️ *Edit weight*\n\n"
                    "Enter new weight in pounds (lbs):\n"
                    "_Example: 1 or 2.5_"
                )
            else:
                text = (
                    "✏️ *Редактирование веса*\n\n"
                    "Введите новый вес в фунтах (lbs):\n"
                    "_Например: 1 или 2.5_"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return PACKAGE_WEIGHT
        elif edit_type == "edit_dimensions":
            data['editing_field'] = 'dimensions'
            if lang == "en":
                text = (
                    "✏️ *Edit dimensions*\n\n"
                    "Enter new dimensions separated by space:\n"
                    "*Length Width Height*\n"
                    "_Example: 12 8 6_"
                )
            else:
                text = (
                    "✏️ *Редактирование размеров*\n\n"
                    "Введите новые размеры через пробел:\n"
                    "*Длина Ширина Высота*\n"
                    "_Например: 12 8 6_"
                )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            return PACKAGE_DIMENSIONS
        
        return EDIT_SECTION
    
    # ===== RATE SELECTION =====
    
    async def select_rate(self, update: Update, context) -> int:
        """Handle rate selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        logger.warning(f"[SELECT_RATE] User {user_id} selected rate: {query.data}")
        lang = await self._get_lang(user_id, context)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update, context)
        
        data = self.get_user_data(user_id, context)
        
        callback_data = query.data
        
        # Handle back to review
        if callback_data == "back_to_review_from_rates":
            # Remove buttons from old message
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await self.show_review_summary(query.message, user_id, context)
            return REVIEW_SUMMARY
        
        # Get selected rate
        rate_map = data.get('rate_map', {})
        logger.warning(f"[SELECT_RATE] Rate map keys: {list(rate_map.keys())}")
        selected_rate = rate_map.get(callback_data)
        
        if not selected_rate:
            if lang == "en":
                text = "❌ Rate not found. Please try again."
            else:
                text = "❌ Тариф не найден. Попробуйте снова."
            back_btn = "◀️ Back" if lang == "en" else "◀️ Назад"
            keyboard = [[InlineKeyboardButton(back_btn, callback_data="back_to_review_from_rates")]]
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
        
        # Localized labels
        if lang == "en":
            sender_lbl, recipient_lbl, package_lbl = "SENDER", "RECIPIENT", "PACKAGE"
            name_lbl, address_lbl, city_lbl, phone_lbl = "Name", "Address", "City", "Phone"
            weight_lbl, dims_lbl, inches_lbl = "Weight", "Dimensions", "inches"
            delivery_lbl, carrier_lbl, service_lbl = "DELIVERY", "Carrier", "Service"
            cost_lbl, balance_lbl, after_payment_lbl, insufficient_lbl = "COST", "Your balance", "After payment", "Insufficient"
            confirm_header = "ORDER CONFIRMATION"
        else:
            sender_lbl, recipient_lbl, package_lbl = "ОТПРАВИТЕЛЬ", "ПОЛУЧАТЕЛЬ", "ПОСЫЛКА"
            name_lbl, address_lbl, city_lbl, phone_lbl = "Имя", "Адрес", "Город", "Телефон"
            weight_lbl, dims_lbl, inches_lbl = "Вес", "Размеры", "дюймов"
            delivery_lbl, carrier_lbl, service_lbl = "ДОСТАВКА", "Перевозчик", "Сервис"
            cost_lbl, balance_lbl, after_payment_lbl, insufficient_lbl = "СТОИМОСТЬ", "Ваш баланс", "После оплаты", "Не хватает"
            confirm_header = "ПОДТВЕРЖДЕНИЕ ЗАКАЗА"
        
        summary = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *{confirm_header}*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 *{sender_lbl}*\n"
            f"▫️ {name_lbl}: {data.get('shipFromName')}\n"
            f"▫️ {address_lbl}: {data.get('shipFromAddressLine1')}\n"
            f"▫️ {city_lbl}: {data.get('shipFromCity')}, {data.get('shipFromState')} {data.get('shipFromPostalCode')}\n"
        )
        
        if data.get('shipFromPhone'):
            summary += f"▫️ {phone_lbl}: {data.get('shipFromPhone')}\n"
        
        summary += (
            f"\n📍 *{recipient_lbl}*\n"
            f"▫️ {name_lbl}: {data.get('shipToName')}\n"
            f"▫️ {address_lbl}: {data.get('shipToAddressLine1')}\n"
            f"▫️ {city_lbl}: {data.get('shipToCity')}, {data.get('shipToState')} {data.get('shipToPostalCode')}\n"
        )
        
        if data.get('shipToPhone'):
            summary += f"▫️ {phone_lbl}: {data.get('shipToPhone')}\n"
        
        weight_lbs = data.get('packageWeightLbs', 0) or (data.get('packageWeight', 0) / 16)
        summary += (
            f"\n📦 *{package_lbl}*\n"
            f"▫️ {weight_lbl}: {weight_lbs:.2f} lbs\n"
            f"▫️ {dims_lbl}: {data.get('packageLength')}×{data.get('packageWidth')}×{data.get('packageHeight')} {inches_lbl}\n"
            f"\n🚚 *{delivery_lbl}*\n"
            f"▫️ {carrier_lbl}: {carrier_name}\n"
            f"▫️ {service_lbl}: {service_type}\n"
            f"\n💰 *{cost_lbl}: ${total_price:.2f}*\n"
            f"💳 *{balance_lbl}: ${user_balance:.2f}* {balance_status}\n"
        )
        
        if user_balance >= total_price:
            summary += f"▫️ {after_payment_lbl}: ${balance_after:.2f}\n"
        else:
            needed = total_price - user_balance
            summary += f"▫️ {insufficient_lbl}: ${needed:.2f}\n"
        
        summary += "\n━━━━━━━━━━━━━━━━━━━━"
        
        if lang == "en":
            keyboard = [
                [InlineKeyboardButton(f"✅ Pay ${total_price:.2f} and create label", callback_data="confirm_yes")],
                [InlineKeyboardButton("◀️ Select different rate", callback_data="back_to_rates")],
                [InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")]
            ]
        else:
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
        lang = await self._get_lang(user_id, context)
        
        # Check if user is banned before creating label
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update, context)
        
        data = self.get_user_data(user_id, context)
        
        if query.data == "confirm_no":
            if lang == "en":
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *ORDER CANCELLED*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Label creation cancelled.\n\n"
                    "Press the button below to return to main menu:"
                )
                menu_btn = "🏠 Return to main menu"
            else:
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ *ЗАКАЗ ОТМЕНЕН*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Создание лейбла отменено.\n\n"
                    "Нажмите кнопку ниже, чтобы вернуться в главное меню:"
                )
                menu_btn = "🏠 Вернуться в главное меню"
            
            keyboard = [
                [InlineKeyboardButton(menu_btn, callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            self.clear_user_data(user_id, context)
            return ConversationHandler.END
        
        if query.data == "back_to_rates":
            # Go back to rate selection
            rates = data.get('available_rates', [])
            if rates:
                await self._show_rates(query, user_id, rates, context)
                return SELECT_RATE
            else:
                # Refetch rates if not available
                loading_msg = "Loading rates..." if lang == "en" else "Получаю тарифы..."
                wait_msg = "Please wait." if lang == "en" else "Пожалуйста, подождите."
                await query.edit_message_text(
                    f"⏳ *{loading_msg}*\n\n{wait_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
                try:
                    rates = await self._fetch_rates(data)
                    data['available_rates'] = rates
                    await self._show_rates(query, user_id, rates, context)
                    return SELECT_RATE
                except Exception as e:
                    error_msg = "Error" if lang == "en" else "Ошибка"
                    text = f"❌ {error_msg}: {str(e)}"
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
                
                # Set flag that user is waiting for balance to continue order - store in MongoDB directly
                try:
                    from database import Database
                    # Build ship_from and ship_to objects from data
                    ship_from_obj = {
                        "name": data.get('shipFromName'),
                        "address_line1": data.get('shipFromAddressLine1'),
                        "city_locality": data.get('shipFromCity'),
                        "state_province": data.get('shipFromState'),
                        "postal_code": data.get('shipFromPostalCode'),
                        "country_code": "US",
                        "phone": data.get('shipFromPhone', ''),
                    }
                    ship_to_obj = {
                        "name": data.get('shipToName'),
                        "address_line1": data.get('shipToAddressLine1'),
                        "city_locality": data.get('shipToCity'),
                        "state_province": data.get('shipToState'),
                        "postal_code": data.get('shipToPostalCode'),
                        "country_code": "US",
                        "phone": data.get('shipToPhone', ''),
                    }
                    # Build package object
                    package_obj = {
                        "weight": {
                            "value": data.get('packageWeight', 0),
                            "unit": "ounce"
                        },
                        "dimensions": {
                            "length": data.get('packageLength', 0),
                            "width": data.get('packageWidth', 0),
                            "height": data.get('packageHeight', 0),
                            "unit": "inch"
                        }
                    }
                    selected_rate_obj = data.get('selected_rate', {})
                    
                    await Database.db.pending_label_orders.update_one(
                        {"telegram_id": user_id},
                        {"$set": {
                            "telegram_id": user_id,
                            "waiting_for_balance": True,
                            "total_cost": total_cost,
                            "order_data": {
                                "ship_from": ship_from_obj,
                                "ship_to": ship_to_obj,
                                "package": package_obj,
                                "selected_rate": selected_rate_obj,
                                # Also save raw data for label creation
                                "shipFromName": data.get('shipFromName'),
                                "shipFromAddressLine1": data.get('shipFromAddressLine1'),
                                "shipFromCity": data.get('shipFromCity'),
                                "shipFromState": data.get('shipFromState'),
                                "shipFromPostalCode": data.get('shipFromPostalCode'),
                                "shipFromPhone": data.get('shipFromPhone', ''),
                                "shipToName": data.get('shipToName'),
                                "shipToAddressLine1": data.get('shipToAddressLine1'),
                                "shipToCity": data.get('shipToCity'),
                                "shipToState": data.get('shipToState'),
                                "shipToPostalCode": data.get('shipToPostalCode'),
                                "shipToPhone": data.get('shipToPhone', ''),
                                "packageWeight": data.get('packageWeight', 0),
                                "packageWeightLbs": data.get('packageWeightLbs', 0),
                                "packageLength": data.get('packageLength', 0),
                                "packageWidth": data.get('packageWidth', 0),
                                "packageHeight": data.get('packageHeight', 0),
                                "carrier": data.get('carrier'),
                                "serviceCode": data.get('serviceCode'),
                                "rate_id": data.get('rate_id'),
                            },
                            "updated_at": datetime.now(timezone.utc)
                        }},
                        upsert=True
                    )
                    logger.warning(f"[PENDING] Saved pending order for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to save pending order status: {e}")
                
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
            
            # Get actual cost from result (actual ShipEngine cost + $10 markup)
            actual_user_paid = result.get('userPaid', total_cost)
            
            # Check if user has enough balance for actual cost
            if self.users_service:
                db_user = await self.users_service.get_user(user_id)
                current_balance = db_user.get('balance', 0) if db_user else 0
                
                if current_balance < actual_user_paid:
                    # User doesn't have enough for actual cost
                    # This can happen if ShipEngine actual price > estimated price
                    # We'll deduct what they have and note the difference
                    logger.warning(f"User {user_id} balance ${current_balance:.2f} < actual cost ${actual_user_paid:.2f}")
                    # Deduct what's available - in production you might want to handle this differently
                    await self.users_service.deduct_for_order(user_id, min(current_balance, actual_user_paid))
                else:
                    # Normal case - deduct actual cost
                    await self.users_service.deduct_for_order(user_id, actual_user_paid)
                
                db_user = await self.users_service.get_user(user_id)
                new_balance = db_user.get('balance', 0) if db_user else 0
            else:
                new_balance = 0
            
            carrier_name = data.get('selected_rate', {}).get('carrier_friendly_name', data.get('carrier', ''))
            tracking_number = result.get('trackingNumber', 'N/A')
            label_url = result.get('labelDownloadUrl', '')
            
            # Store data for potential template save
            self.get_user_data(user_id, context)['last_order_data'] = data.copy()
            
            # Generate AI thank you message
            try:
                thank_you_msg = await generate_thank_you_message(carrier_name, tracking_number)
            except Exception as ai_err:
                logger.warning(f"Failed to generate AI thank you message: {ai_err}")
                thank_you_msg = "Спасибо за заказ! 🎉"
            
            success_message = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *ЛЕЙБЛ СОЗДАН УСПЕШНО!*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 *Информация о доставке:*\n\n"
                f"▫️ Tracking номер:\n`{tracking_number}`\n\n"
                f"▫️ Перевозчик: {carrier_name}\n"
                f"▫️ Стоимость: ${actual_user_paid:.2f}\n"
                f"▫️ Остаток на балансе: ${new_balance:.2f}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 {thank_you_msg}"
            )
            
            # Send PDF file directly if available
            if label_url:
                try:
                    import httpx
                    from io import BytesIO
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(label_url)
                        if response.status_code == 200:
                            pdf_file = BytesIO(response.content)
                            pdf_file.name = f"{tracking_number}.pdf"
                            
                            # Delete "Creating label..." message
                            try:
                                await query.message.delete()
                            except Exception:
                                pass
                            
                            # Send PDF with caption and menu button
                            keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            await context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=pdf_file,
                                filename=f"{tracking_number}.pdf",
                                caption=success_message,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                            
                            # Notify admin about label creation
                            try:
                                from services.admin_notifications import notify_label_created
                                tg_user = update.effective_user
                                label_cost = result.get('cost', 0) or 0
                                profit = actual_user_paid - label_cost if label_cost else 10
                                await notify_label_created(
                                    telegram_id=user_id,
                                    username=tg_user.username,
                                    tracking_number=tracking_number,
                                    carrier=carrier_name,
                                    cost=actual_user_paid,
                                    profit=profit
                                )
                            except Exception as admin_err:
                                logger.warning(f"Failed to send admin notification: {admin_err}")
                            
                            return CONFIRM
                except Exception as pdf_err:
                    logger.warning(f"Failed to send PDF directly: {pdf_err}")
                    # Fall through to button-based approach
            
            # Fallback: show download button if PDF send failed
            keyboard = []
            if label_url:
                data['label_url'] = label_url
                data['tracking_number'] = tracking_number
                keyboard.append([InlineKeyboardButton(f"📥 Скачать {tracking_number}.pdf", callback_data="download_label")])
            keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
            return CONFIRM
            
        except Exception as e:
            logger.error(f"Error creating label: {e}", exc_info=True)
            error_str = str(e)
            
            # Notify admin about user error
            try:
                from services.admin_notifications import notify_user_error
                tg_user = update.effective_user
                carrier_name = data.get('selected_rate', {}).get('carrier_friendly_name', 'Unknown')
                await notify_user_error(
                    telegram_id=user_id,
                    username=tg_user.username if tg_user else None,
                    error_type="Ошибка создания лейбла",
                    error_message=error_str,
                    context=f"Перевозчик: {carrier_name}"
                )
            except Exception as admin_err:
                logger.warning(f"Failed to send admin error notification: {admin_err}")
            
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
        await self.show_review_summary(query.message, user_id, context, edit_message=True)
        return REVIEW_SUMMARY
    
    async def save_template_prompt(self, update: Update, context) -> int:
        """Ask for template name"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        logger.info(f"save_template_prompt called for user {user_id}")
        
        # Check if we have data
        data = self.get_user_data(user_id, context)
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
        data = self.get_user_data(user_id, context)
        
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
                logger.info("[TEMPLATE] Successfully removed cancel button")
            except Exception as e:
                logger.warning(f"[TEMPLATE] Could not remove cancel button: {e}")
        else:
            logger.warning("[TEMPLATE] No message_id or chat_id stored to remove button")
        
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
            return await self._send_banned_message(update, context)
        
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
        data = self.get_user_data(user_id, context)
        data.update(template_data)
        data['using_template'] = template_id
        
        # Increment use count
        await self.templates_service.increment_use_count(template_id)
        
        # Show review summary with template data as NEW message
        await self.show_review_summary(query.message, user_id, context, from_template=True, edit_message=False)
        return REVIEW_SUMMARY
    
    async def edit_template(self, update: Update, context) -> int:
        """Edit a template - sends new message"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # Check if user is banned
        if await self._check_user_banned(user_id):
            return await self._send_banned_message(update, context)
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
        data = self.get_user_data(user_id, context)
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
        data = self.get_user_data(user_id, context)
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
        self.clear_user_data(user_id, context)
        return ConversationHandler.END
    
    async def download_label(self, update: Update, context) -> int:
        """Download label PDF and send via Telegram"""
        query = update.callback_query
        await query.answer("📥 Загрузка лейбла...")
        
        user_id = str(update.effective_user.id)
        data = self.get_user_data(user_id, context)
        
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
        self.clear_user_data(user_id, context)
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
            return await self._send_banned_message(update, context)
        
        self.clear_user_data(user_id, context)
        
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
        self.clear_user_data(user_id, context)
        
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
            return await self._send_banned_message(update, context)
        
        self.clear_user_data(user_id, context)
        
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
                    CallbackQueryHandler(self.select_rate, pattern="^(rate_\\d+|back_to_review_from_rates)$")
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
            ],
            name="label_creation",
            persistent=True,  # Use MongoPersistence for multi-pod state sync
            per_message=False,
            per_chat=True,
            per_user=True,
            allow_reentry=True,
        )
