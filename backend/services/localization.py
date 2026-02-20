"""
Localization service for multi-language support
"""
from typing import Dict, Any

# Default language
DEFAULT_LANGUAGE = "ru"

# All translations
TRANSLATIONS = {
    "ru": {
        # Main menu
        "welcome_title": "🚀 *SHIPPING LABEL BOT*",
        "welcome_subtitle": "Создавайте этикетки для доставки быстро и удобно!",
        "balance": "Баланс",
        "btn_create_label": "📦 Создать лейбл",
        "btn_templates": "📋 Шаблоны",
        "btn_balance": "💰 Баланс",
        "btn_refund": "🔄 Возврат",
        "btn_faq": "❓ FAQ",
        "btn_language": "🌐 Язык",
        "btn_main_menu": "🏠 Главное меню",
        "btn_back": "◀️ Назад",
        "btn_cancel": "❌ Отмена",
        "btn_confirm": "✅ Подтвердить",
        "btn_continue": "➡️ Продолжить",
        "btn_skip": "⏭️ Пропустить",
        
        # Language selection
        "select_language": "🌐 *ВЫБЕРИТЕ ЯЗЫК*\n\nSelect your language:",
        "language_changed": "✅ Язык изменён на Русский",
        
        # Balance
        "balance_title": "💰 *ВАШ БАЛАНС*",
        "current_balance": "Текущий баланс",
        "btn_topup": "💳 Пополнить баланс",
        "topup_title": "💳 *ПОПОЛНЕНИЕ БАЛАНСА*",
        "topup_enter_amount": "Введите сумму пополнения в USD (минимум $10):",
        "topup_min_amount": "❌ Минимальная сумма пополнения: $10",
        "topup_invalid_amount": "❌ Введите корректную сумму",
        "topup_success": "✅ *БАЛАНС ПОПОЛНЕН*",
        "topup_amount": "Сумма",
        "topup_reason": "Причина",
        "topup_was": "Было",
        "topup_now": "Стало",
        "balance_deducted": "💸 *СПИСАНИЕ СРЕДСТВ*",
        "btn_continue_order": "📦 Продолжить заказ",
        
        # Label creation
        "label_create_title": "📦 *СОЗДАНИЕ ЛЕЙБЛА*",
        "step": "Шаг",
        "substep": "Подшаг",
        
        # Sender info
        "sender_title": "📤 *ОТПРАВИТЕЛЬ*",
        "sender_name": "Полное имя отправителя",
        "sender_address": "Адрес (улица, дом)",
        "sender_city": "Город",
        "sender_state": "Штат (2 буквы, например NY)",
        "sender_zip": "ZIP код",
        "sender_phone": "Телефон",
        
        # Recipient info
        "recipient_title": "📥 *ПОЛУЧАТЕЛЬ*",
        "recipient_name": "Полное имя получателя",
        "recipient_address": "Адрес (улица, дом)",
        "recipient_city": "Город",
        "recipient_state": "Штат (2 буквы)",
        "recipient_zip": "ZIP код",
        "recipient_phone": "Телефон",
        
        # Package info
        "package_title": "📦 *ПОСЫЛКА*",
        "package_weight": "Вес посылки в унциях (oz)",
        "package_weight_lbs": "Вес",
        "package_dimensions": "Размеры (Д×Ш×В в дюймах)",
        "package_length": "Длина (дюймы)",
        "package_width": "Ширина (дюймы)",
        "package_height": "Высота (дюймы)",
        
        # Review
        "review_title": "📋 *ПРОВЕРЬТЕ ДАННЫЕ*",
        "review_sender": "📤 Отправитель",
        "review_recipient": "📥 Получатель",
        "review_package": "📦 Посылка",
        "review_weight": "Вес",
        "review_dimensions": "Размеры",
        "review_edit": "Отредактируйте при необходимости",
        "btn_all_correct": "✅ Всё верно, продолжить",
        "btn_edit_sender": "✏️ Отправитель",
        "btn_edit_recipient": "✏️ Получатель",
        "btn_edit_package": "✏️ Посылка",
        
        # Rates
        "rates_title": "🚚 *ВЫБЕРИТЕ ТАРИФ*",
        "rates_loading": "⏳ Загружаем тарифы...",
        "rates_error": "❌ *Ошибка получения тарифов*",
        "rates_not_found": "Тарифы не найдены",
        "carrier": "Перевозчик",
        "service": "Сервис",
        "price": "Цена",
        "delivery": "Доставка",
        "days": "дней",
        
        # Confirmation
        "confirm_title": "💳 *ПОДТВЕРЖДЕНИЕ ОПЛАТЫ*",
        "confirm_cost": "Стоимость",
        "confirm_balance": "Ваш баланс",
        "confirm_after": "После оплаты",
        "btn_pay_create": "✅ Оплатить и создать лейбл",
        
        # Success
        "label_created_title": "✅ *ЛЕЙБЛ СОЗДАН УСПЕШНО!*",
        "label_info": "📋 *Информация о доставке:*",
        "tracking_number": "Tracking номер",
        "cost": "Стоимость",
        "remaining_balance": "Остаток на балансе",
        
        # Errors
        "insufficient_funds_title": "❌ *НЕДОСТАТОЧНО СРЕДСТВ*",
        "insufficient_funds_cost": "Стоимость лейбла",
        "insufficient_funds_balance": "Ваш баланс",
        "insufficient_funds_need": "Необходимо пополнить",
        "insufficient_funds_crypto": "💳 *Пополните баланс криптой:*",
        "insufficient_funds_methods": "▫️ BTC, ETH, USDT, LTC\n▫️ Минимум: $10",
        "error_title": "❌ *ОШИБКА*",
        "error_carrier": "❌ *ОШИБКА ПЕРЕВОЗЧИКА*",
        "error_carrier_cannot": "не может создать лейбл",
        "error_reasons": "*Возможные причины:*",
        "error_reason_address": "▫️ Некорректный адрес",
        "error_reason_route": "▫️ Недоступный маршрут",
        "error_reason_sandbox": "▫️ Ограничения sandbox режима",
        "error_recommendation": "*Рекомендация:*",
        "error_try_other": "Попробуйте выбрать другого перевозчика\n(USPS обычно работает стабильнее)",
        "btn_try_again": "🔄 Попробовать снова",
        "btn_choose_other": "🔄 Выбрать другой тариф",
        
        # Templates
        "templates_title": "📋 *ВАШИ ШАБЛОНЫ*",
        "templates_empty": "У вас пока нет сохранённых шаблонов",
        "templates_use_count": "Использован",
        "templates_times": "раз",
        "btn_use_template": "📝 Использовать",
        "btn_delete_template": "🗑️ Удалить",
        "template_deleted": "✅ Шаблон удалён",
        "template_save_title": "💾 *СОХРАНИТЬ ШАБЛОН*",
        "template_save_prompt": "Введите название для шаблона:",
        "template_saved": "✅ Шаблон сохранён",
        
        # Continue order
        "continue_order_title": "📦 *ПРОДОЛЖЕНИЕ ЗАКАЗА*",
        "no_saved_order": "Нет сохранённого заказа.\nНачните создание нового лейбла.",
        
        # Refund
        "refund_title": "🔄 *ВОЗВРАТ СРЕДСТВ*",
        "refund_text": "Для возврата средств свяжитесь с поддержкой.",
        
        # FAQ
        "faq_title": "❓ *FAQ*",
        "faq_text": "Часто задаваемые вопросы...",
        
        # Banned
        "banned_title": "🚫 *ДОСТУП ЗАПРЕЩЁН*",
        "banned_text": "Ваш аккаунт заблокирован.\nДля разблокировки свяжитесь с поддержкой.",
        
        # Maintenance
        "maintenance_title": "🔧 *ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ*",
        "maintenance_text": "Бот временно недоступен.\nПопробуйте позже.",
        
        # Misc
        "name": "Имя",
        "address": "Адрес",
        "city": "Город",
        "phone": "Телефон",
        "inches": "дюймов",
        "lbs": "lbs",
        "oz": "oz",
        "what_next": "Что дальше?",
        "info": "ℹ️ *ИНФОРМАЦИЯ*",
    },
    
    "en": {
        # Main menu
        "welcome_title": "🚀 *SHIPPING LABEL BOT*",
        "welcome_subtitle": "Create shipping labels quickly and easily!",
        "balance": "Balance",
        "btn_create_label": "📦 Create Label",
        "btn_templates": "📋 Templates",
        "btn_balance": "💰 Balance",
        "btn_refund": "🔄 Refund",
        "btn_faq": "❓ FAQ",
        "btn_language": "🌐 Language",
        "btn_main_menu": "🏠 Main Menu",
        "btn_back": "◀️ Back",
        "btn_cancel": "❌ Cancel",
        "btn_confirm": "✅ Confirm",
        "btn_continue": "➡️ Continue",
        "btn_skip": "⏭️ Skip",
        
        # Language selection
        "select_language": "🌐 *SELECT LANGUAGE*\n\nВыберите язык:",
        "language_changed": "✅ Language changed to English",
        
        # Balance
        "balance_title": "💰 *YOUR BALANCE*",
        "current_balance": "Current balance",
        "btn_topup": "💳 Top Up Balance",
        "topup_title": "💳 *TOP UP BALANCE*",
        "topup_enter_amount": "Enter top-up amount in USD (minimum $10):",
        "topup_min_amount": "❌ Minimum top-up amount: $10",
        "topup_invalid_amount": "❌ Enter a valid amount",
        "topup_success": "✅ *BALANCE TOPPED UP*",
        "topup_amount": "Amount",
        "topup_reason": "Reason",
        "topup_was": "Was",
        "topup_now": "Now",
        "balance_deducted": "💸 *BALANCE DEDUCTED*",
        "btn_continue_order": "📦 Continue Order",
        
        # Label creation
        "label_create_title": "📦 *CREATE LABEL*",
        "step": "Step",
        "substep": "Substep",
        
        # Sender info
        "sender_title": "📤 *SENDER*",
        "sender_name": "Sender's full name",
        "sender_address": "Address (street, building)",
        "sender_city": "City",
        "sender_state": "State (2 letters, e.g. NY)",
        "sender_zip": "ZIP code",
        "sender_phone": "Phone",
        
        # Recipient info
        "recipient_title": "📥 *RECIPIENT*",
        "recipient_name": "Recipient's full name",
        "recipient_address": "Address (street, building)",
        "recipient_city": "City",
        "recipient_state": "State (2 letters)",
        "recipient_zip": "ZIP code",
        "recipient_phone": "Phone",
        
        # Package info
        "package_title": "📦 *PACKAGE*",
        "package_weight": "Package weight in ounces (oz)",
        "package_weight_lbs": "Weight",
        "package_dimensions": "Dimensions (L×W×H in inches)",
        "package_length": "Length (inches)",
        "package_width": "Width (inches)",
        "package_height": "Height (inches)",
        
        # Review
        "review_title": "📋 *REVIEW DATA*",
        "review_sender": "📤 Sender",
        "review_recipient": "📥 Recipient",
        "review_package": "📦 Package",
        "review_weight": "Weight",
        "review_dimensions": "Dimensions",
        "review_edit": "Edit if necessary",
        "btn_all_correct": "✅ All correct, continue",
        "btn_edit_sender": "✏️ Sender",
        "btn_edit_recipient": "✏️ Recipient",
        "btn_edit_package": "✏️ Package",
        
        # Rates
        "rates_title": "🚚 *SELECT RATE*",
        "rates_loading": "⏳ Loading rates...",
        "rates_error": "❌ *Error loading rates*",
        "rates_not_found": "No rates found",
        "carrier": "Carrier",
        "service": "Service",
        "price": "Price",
        "delivery": "Delivery",
        "days": "days",
        
        # Confirmation
        "confirm_title": "💳 *PAYMENT CONFIRMATION*",
        "confirm_cost": "Cost",
        "confirm_balance": "Your balance",
        "confirm_after": "After payment",
        "btn_pay_create": "✅ Pay & Create Label",
        
        # Success
        "label_created_title": "✅ *LABEL CREATED SUCCESSFULLY!*",
        "label_info": "📋 *Shipping information:*",
        "tracking_number": "Tracking number",
        "cost": "Cost",
        "remaining_balance": "Remaining balance",
        
        # Errors
        "insufficient_funds_title": "❌ *INSUFFICIENT FUNDS*",
        "insufficient_funds_cost": "Label cost",
        "insufficient_funds_balance": "Your balance",
        "insufficient_funds_need": "Need to top up",
        "insufficient_funds_crypto": "💳 *Top up with crypto:*",
        "insufficient_funds_methods": "▫️ BTC, ETH, USDT, LTC\n▫️ Minimum: $10",
        "error_title": "❌ *ERROR*",
        "error_carrier": "❌ *CARRIER ERROR*",
        "error_carrier_cannot": "cannot create label",
        "error_reasons": "*Possible reasons:*",
        "error_reason_address": "▫️ Invalid address",
        "error_reason_route": "▫️ Unavailable route",
        "error_reason_sandbox": "▫️ Sandbox mode restrictions",
        "error_recommendation": "*Recommendation:*",
        "error_try_other": "Try selecting another carrier\n(USPS usually works better)",
        "btn_try_again": "🔄 Try Again",
        "btn_choose_other": "🔄 Choose Another Rate",
        
        # Templates
        "templates_title": "📋 *YOUR TEMPLATES*",
        "templates_empty": "You don't have any saved templates yet",
        "templates_use_count": "Used",
        "templates_times": "times",
        "btn_use_template": "📝 Use",
        "btn_delete_template": "🗑️ Delete",
        "template_deleted": "✅ Template deleted",
        "template_save_title": "💾 *SAVE TEMPLATE*",
        "template_save_prompt": "Enter a name for the template:",
        "template_saved": "✅ Template saved",
        
        # Continue order
        "continue_order_title": "📦 *CONTINUE ORDER*",
        "no_saved_order": "No saved order.\nStart creating a new label.",
        
        # Refund
        "refund_title": "🔄 *REFUND*",
        "refund_text": "To request a refund, contact support.",
        
        # FAQ
        "faq_title": "❓ *FAQ*",
        "faq_text": "Frequently asked questions...",
        
        # Banned
        "banned_title": "🚫 *ACCESS DENIED*",
        "banned_text": "Your account is blocked.\nContact support for unblocking.",
        
        # Maintenance
        "maintenance_title": "🔧 *MAINTENANCE*",
        "maintenance_text": "Bot is temporarily unavailable.\nTry again later.",
        
        # Misc
        "name": "Name",
        "address": "Address",
        "city": "City",
        "phone": "Phone",
        "inches": "inches",
        "lbs": "lbs",
        "oz": "oz",
        "what_next": "What's next?",
        "info": "ℹ️ *INFORMATION*",
    }
}


def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    """Get translated text by key"""
    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    text = translations.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    
    # Format with kwargs if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return text


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Shorthand for get_text"""
    return get_text(key, lang, **kwargs)


class Localization:
    """Localization helper class"""
    
    def __init__(self, lang: str = "ru"):
        self.lang = lang
    
    def __call__(self, key: str, **kwargs) -> str:
        return get_text(key, self.lang, **kwargs)
    
    def set_language(self, lang: str):
        self.lang = lang


# User language cache
_user_languages: Dict[str, str] = {}


async def get_user_language(db, telegram_id: str) -> str:
    """Get user's preferred language from database"""
    # Check cache first
    if telegram_id in _user_languages:
        return _user_languages[telegram_id]
    
    try:
        user = await db.telegram_users.find_one({"telegram_id": telegram_id})
        if user and user.get("language"):
            lang = user.get("language")
            _user_languages[telegram_id] = lang
            return lang
    except Exception:
        pass
    
    return DEFAULT_LANGUAGE


async def set_user_language(db, telegram_id: str, lang: str):
    """Set user's preferred language in database"""
    try:
        await db.telegram_users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"language": lang}}
        )
        _user_languages[telegram_id] = lang
    except Exception as e:
        print(f"Error setting user language: {e}")


def clear_language_cache(telegram_id: str = None):
    """Clear language cache for user or all users"""
    global _user_languages
    if telegram_id:
        _user_languages.pop(telegram_id, None)
    else:
        _user_languages = {}
