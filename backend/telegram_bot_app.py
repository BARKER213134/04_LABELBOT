#!/usr/bin/env python3
"""
Telegram Bot - ULTRA FAST VERSION
"""
import asyncio
import logging
from telegram.ext import Application, CommandHandler
from telegram.constants import ChatAction
from config import get_settings
from database import Database, connect_db
from services.telegram_service import TelegramService
from services.telegram_conversation import TelegramConversationHandler
from services.orders_service import OrdersService
from services.shipengine_service import ShipEngineService
from services.users_service import UsersService
from services.templates_service import TemplatesService
from services.cache import user_cache, balance_cache, banned_cache

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_users_service = None
_templates_service = None


async def check_user_banned(user_id: str) -> bool:
    """Check if user is banned - CACHED"""
    # Check cache first (instant)
    cached = banned_cache.get(f"ban_{user_id}")
    if cached is not None:
        return cached
    
    if _users_service:
        user = await _users_service.get_user(user_id)
        is_banned = user and user.get('is_banned', False)
        banned_cache.set(f"ban_{user_id}", is_banned)
        return is_banned
    return False


async def get_user_balance(user_id: str) -> float:
    """Get user balance - CACHED"""
    cached = balance_cache.get(f"bal_{user_id}")
    if cached is not None:
        return cached
    
    if _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
            balance_cache.set(f"bal_{user_id}", balance)
            return balance
    return 0.0


async def send_banned_message(chat_id: int, bot):
    """Send banned message"""
    await bot.send_message(
        chat_id=chat_id,
        text="🚫 *ДОСТУП ЗАПРЕЩЁН*\n\nВаш аккаунт заблокирован.",
        parse_mode="Markdown"
    )


async def start_command(update, context):
    """Handle /start"""
    global _users_service
    
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    # Instant ban check from cache
    if banned_cache.get(f"ban_{user_id}"):
        await send_banned_message(chat_id, context.bot)
        return
    
    # Send photo IMMEDIATELY (no DB wait)
    logo_url = "https://customer-assets.emergentagent.com/job_shipnow-bot/artifacts/tnl64fud_JUST%20WHITE.png"
    
    # Send photo first (instant feedback)
    await context.bot.send_photo(chat_id=chat_id, photo=logo_url)
    
    # Get fresh balance from DB (not just cache)
    balance = 0.0
    if _users_service:
        tg_user = update.effective_user
        user = await _users_service.get_or_create_user(
            telegram_id=str(tg_user.id),
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name
        )
        if user:
            balance = user.get('balance', 0.0)
            # Update cache
            balance_cache.set(f"bal_{user_id}", balance)
    
    # Get user language
    from services.localization import get_user_language
    lang = await get_user_language(Database.db, user_id)
    context.user_data['language'] = lang
    
    # Send menu
    telegram_service = TelegramService('production')
    sent = await telegram_service.send_welcome_message(chat_id, balance, lang)
    if sent:
        context.user_data['last_menu_message_id'] = sent.message_id

async def check_balance_callback(update, context):
    """Handle balance check - FAST"""
    global _users_service
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    await query.answer()  # Answer immediately
    
    user_id = str(update.effective_user.id)
    
    # Quick ban check
    if banned_cache.get(f"ban_{user_id}"):
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    # Remove old buttons in background
    asyncio.create_task(_safe_remove_buttons(query))
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    # Get balance from cache or DB
    balance = balance_cache.get(f"bal_{user_id}")
    total_orders = 0
    total_spent = 0.0
    
    if balance is None and _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
            total_orders = user.get('total_orders', 0)
            total_spent = user.get('total_spent', 0.0)
            balance_cache.set(f"bal_{user_id}", balance)
    
    balance = balance or 0.0
    
    if lang == "en":
        text = (
            "💰 *YOUR BALANCE*\n\n"
            f"▫️ Available: *${balance:.2f}*\n"
            f"▫️ Orders: {total_orders}\n"
            f"▫️ Spent: ${total_spent:.2f}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Top Up", callback_data="topup_balance")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]
        ]
    else:
        text = (
            "💰 *ВАШ БАЛАНС*\n\n"
            f"▫️ Доступно: *${balance:.2f}*\n"
            f"▫️ Заказов: {total_orders}\n"
            f"▫️ Потрачено: ${total_spent:.2f}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Пополнить", callback_data="topup_balance")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def _safe_remove_buttons(query):
    """Remove buttons safely in background"""
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass


async def topup_balance_callback(update, context):
    """Handle balance top-up - starts text input flow"""
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    if banned_cache.get(f"ban_{user_id}"):
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    asyncio.create_task(_safe_remove_buttons(query))
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    # Set flag for topup amount input
    context.user_data['awaiting_topup_amount'] = True
    
    if lang == "en":
        text = (
            "💳 *TOP UP BALANCE*\n\n"
            "Enter amount in USD\n"
            "▫️ Minimum: $10\n"
            "▫️ Crypto: BTC, ETH, USDT, LTC"
        )
        cancel_btn = "❌ Cancel"
    else:
        text = (
            "💳 *ПОПОЛНЕНИЕ БАЛАНСА*\n\n"
            "Введите сумму в USD\n"
            "▫️ Минимум: $10\n"
            "▫️ Крипто: BTC, ETH, USDT, LTC"
        )
        cancel_btn = "❌ Отмена"
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[InlineKeyboardButton(cancel_btn, callback_data="cancel_topup")]]
    
    sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    context.user_data['topup_message_id'] = sent.message_id
    context.user_data['topup_chat_id'] = sent.chat_id


async def process_topup_amount(update, context):
    """Process top-up amount from text input"""
    from database import Database
    from services.localization import get_user_language
    
    user_id = str(update.effective_user.id)
    text_input = update.message.text.strip()
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    # Remove cancel button from previous message
    message_id = context.user_data.get('topup_message_id')
    chat_id = context.user_data.get('topup_chat_id')
    if message_id and chat_id:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None
            )
        except Exception:
            pass
    
    try:
        amount = float(text_input.replace('$', '').replace(',', '.'))
        cancel_btn = "❌ Cancel" if lang == "en" else "❌ Отмена"
        
        if amount < 10:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton(cancel_btn, callback_data="cancel_topup")]]
            if lang == "en":
                text = "❌ *Minimum amount: $10*\n\nPlease enter an amount of $10 or more"
            else:
                text = "❌ *Минимальная сумма: $10*\n\nПожалуйста, введите сумму от $10"
            sent_msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            context.user_data['topup_message_id'] = sent_msg.message_id
            context.user_data['topup_chat_id'] = sent_msg.chat_id
            return  # Stay in topup mode
        
        if amount > 10000:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton(cancel_btn, callback_data="cancel_topup")]]
            if lang == "en":
                text = "❌ *Maximum amount: $10,000*\n\nPlease enter a smaller amount"
            else:
                text = "❌ *Максимальная сумма: $10,000*\n\nПожалуйста, введите меньшую сумму"
            sent_msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            context.user_data['topup_message_id'] = sent_msg.message_id
            context.user_data['topup_chat_id'] = sent_msg.chat_id
            return  # Stay in topup mode
        
        # Clear topup flag and create invoice
        context.user_data['awaiting_topup_amount'] = False
        await create_crypto_invoice(update, context, user_id, amount, lang)
        
    except ValueError:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        cancel_btn = "❌ Cancel" if lang == "en" else "❌ Отмена"
        keyboard = [[InlineKeyboardButton(cancel_btn, callback_data="cancel_topup")]]
        if lang == "en":
            text = "❌ *Invalid amount*\n\nEnter a number, for example: 25 or 50.00"
        else:
            text = "❌ *Некорректная сумма*\n\nВведите число, например: 25 или 50.00"
        sent_msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        context.user_data['topup_message_id'] = sent_msg.message_id
        context.user_data['topup_chat_id'] = sent_msg.chat_id
        # Stay in topup mode


async def cancel_topup_callback(update, context):
    """Cancel top-up process and go back to balance"""
    query = update.callback_query
    await query.answer()
    
    # Clear the waiting flag
    context.user_data['awaiting_topup_amount'] = False
    
    # Remove buttons from old message
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Redirect to balance check (which sends new message)
    await check_balance_callback(update, context)


async def create_crypto_invoice(update, context, user_id: str, amount: float, lang: str = "ru"):
    """Create OxaPay crypto invoice - sends new message"""
    from database import Database
    from services.oxapay_service import OxaPayService
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Send loading message
    loading_msg_text = "⏳ *Creating payment...*" if lang == "en" else "⏳ *Создаю платёж...*"
    loading_msg = await update.message.reply_text(
        loading_msg_text,
        parse_mode="Markdown"
    )
    
    try:
        db = Database.db
        oxapay_service = OxaPayService(db)
        
        result = await oxapay_service.create_invoice(
            user_id=user_id,
            telegram_id=user_id,
            amount=amount,
            currency="USD"
        )
        
        if result.get("success"):
            payment_url = result.get("payment_url")
            
            if lang == "en":
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💳 *PAYMENT CREATED*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💰 Amount: *${amount:.2f}*\n\n"
                    "▫️ Click the button below to pay\n"
                    "▫️ Accepted: BTC, ETH, USDT, LTC\n"
                    "▫️ Balance will update automatically after payment\n\n"
                    "⏰ *Payment expires in: 60 minutes*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                text = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💳 *ОПЛАТА СОЗДАНА*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💰 Сумма: *${amount:.2f}*\n\n"
                    "▫️ Нажмите кнопку ниже для оплаты\n"
                    "▫️ Принимаем: BTC, ETH, USDT, LTC\n"
                    "▫️ После оплаты баланс обновится автоматически\n\n"
                    "⏰ *Срок оплаты: 60 минут*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
            
            track_id = result.get("track_id")
            if lang == "en":
                keyboard = [
                    [InlineKeyboardButton("💳 Pay with crypto", url=payment_url)],
                    [InlineKeyboardButton("🔄 Check status", callback_data=f"check_payment_{track_id}")],
                    [InlineKeyboardButton("🏠 Main menu", callback_data="back_to_menu")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("💳 Оплатить криптой", url=payment_url)],
                    [InlineKeyboardButton("🔄 Проверить статус", callback_data=f"check_payment_{track_id}")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit loading message with result
            await loading_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            raise Exception("Failed to create invoice")
            
    except Exception as e:
        logger.error(f"Failed to create crypto invoice: {e}")
        
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="topup_balance")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit loading message to show error
        await loading_msg.edit_text(
            f"❌ *Ошибка создания платежа*\n\n{str(e)}\n\nПопробуйте позже.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def check_payment_status_callback(update, context):
    """Check crypto payment status"""
    query = update.callback_query
    
    track_id = query.data.replace("check_payment_", "")
    
    from database import Database
    from services.oxapay_service import OxaPayService
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.error import BadRequest
    
    try:
        db = Database.db
        oxapay_service = OxaPayService(db)
        
        invoice = await oxapay_service.get_invoice_status(track_id)
        
        if not invoice:
            await query.answer("❌ Платёж не найден", show_alert=True)
            return
        
        status = invoice.get("status", "pending")
        amount = invoice.get("amount", 0)
        
        status_text = {
            "pending": "⏳ Ожидает оплаты",
            "confirming": "🔄 Подтверждается...",
            "paid": "✅ Оплачено",
            "expired": "❌ Истёк срок",
            "failed": "❌ Ошибка оплаты"
        }.get(status, f"📋 {status}")
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *СТАТУС ПЛАТЕЖА*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Сумма: *${amount:.2f}*\n"
            f"📊 Статус: *{status_text}*\n\n"
        )
        
        if status == "paid":
            text += "✅ Баланс пополнен!\n\n"
            keyboard = [
                [InlineKeyboardButton("💰 Проверить баланс", callback_data="check_balance")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
        elif status in ["expired", "failed"]:
            text += "Попробуйте создать новый платёж.\n\n"
            keyboard = [
                [InlineKeyboardButton("🔄 Новый платёж", callback_data="topup_balance")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
        else:
            text += "Ожидаем подтверждение оплаты...\n\n"
            payment_url = invoice.get("payment_url", "")
            keyboard = []
            if payment_url:
                keyboard.append([InlineKeyboardButton("💳 Оплатить", url=payment_url)])
            keyboard.append([InlineKeyboardButton("🔄 Обновить статус", callback_data=f"check_payment_{track_id}")])
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
        
        text += "━━━━━━━━━━━━━━━━━━━━"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            await query.answer()
        except BadRequest as e:
            # Message not modified - same content, just answer the callback
            if "message is not modified" in str(e).lower():
                await query.answer("Статус не изменился", show_alert=False)
            else:
                raise
        
    except Exception as e:
        logger.error(f"Failed to check payment status: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def change_language_callback(update, context):
    """Show language selection menu"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    query = update.callback_query
    await query.answer()
    
    # Remove old buttons
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 *SELECT LANGUAGE / ВЫБЕРИТЕ ЯЗЫК*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")],
        [InlineKeyboardButton("◀️ Back / Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def set_language_callback(update, context):
    """Set user language"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import Database
    from services.localization import set_user_language, t
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    # Parse language from callback data
    lang = query.data.replace("set_lang_", "")
    
    # Save language to database
    await set_user_language(Database.db, user_id, lang)
    
    # Store in context for current session
    context.user_data['language'] = lang
    
    # Remove old message buttons
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Send confirmation
    if lang == "en":
        text = "✅ Language changed to English"
    else:
        text = "✅ Язык изменён на Русский"
    
    keyboard = [[InlineKeyboardButton(t("btn_main_menu", lang), callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )

async def back_to_menu_callback(update, context):
    """Back to menu"""
    global _users_service
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    if banned_cache.get(f"ban_{user_id}"):
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    # Get fresh balance from DB
    balance = 0.0
    if _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
            balance_cache.set(f"bal_{user_id}", balance)
    
    asyncio.create_task(_safe_remove_buttons(query))
    
    telegram_service = TelegramService('production')
    sent = await telegram_service.send_welcome_message(query.message.chat_id, balance, lang)
    if sent:
        context.user_data['last_menu_message_id'] = sent.message_id

async def continue_order_callback(update, context):
    """Continue creating label after balance top-up - show saved order summary"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import Database
    from services.users_service import UsersService
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    # Check if user is banned
    if banned_cache.get(f"ban_{user_id}"):
        await send_banned_message(chat_id, context.bot)
        return
    
    # Remove buttons from old message
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Check if there's saved order data
    db = Database.db
    pending_order = await db.pending_label_orders.find_one({"telegram_id": user_id})
    
    if pending_order and pending_order.get("order_data"):
        order_data = pending_order.get("order_data", {})
        total_cost = pending_order.get("total_cost", 0)
        
        # Get user's current balance
        users_service = UsersService(db)
        user = await users_service.get_user(user_id)
        current_balance = user.get('balance', 0) if user else 0
        
        # Get order details with safe defaults
        ship_from = order_data.get("ship_from") or {}
        ship_to = order_data.get("ship_to") or {}
        package = order_data.get("package") or {}
        selected_rate = order_data.get("selected_rate") or {}
        
        # Build summary message
        carrier_name = selected_rate.get('carrier_friendly_name', 'Неизвестно')
        service_name = selected_rate.get('service_type', '')
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *ПРОДОЛЖЕНИЕ ЗАКАЗА*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📤 Отправитель:*\n"
            f"▫️ {ship_from.get('name', 'N/A')}\n"
            f"▫️ {ship_from.get('address_line1', 'N/A')}\n"
            f"▫️ {ship_from.get('city_locality', '')}, {ship_from.get('state_province', '')} {ship_from.get('postal_code', '')}\n\n"
            "*📥 Получатель:*\n"
            f"▫️ {ship_to.get('name', 'N/A')}\n"
            f"▫️ {ship_to.get('address_line1', 'N/A')}\n"
            f"▫️ {ship_to.get('city_locality', '')}, {ship_to.get('state_province', '')} {ship_to.get('postal_code', '')}\n\n"
            "*📦 Посылка:*\n"
        )
        
        # Get weight - check both nested and flat formats
        weight_val = 0
        weight_unit = "oz"
        if package.get('weight'):
            weight_val = package.get('weight', {}).get('value', 0) or 0
            weight_unit = package.get('weight', {}).get('unit', 'oz')
        elif order_data.get('packageWeight'):
            weight_val = order_data.get('packageWeight', 0) or 0
        
        # Convert to lbs for display if in ounces
        if weight_unit == "ounce" or weight_unit == "oz":
            weight_lbs = weight_val / 16 if weight_val else 0
            text += f"▫️ Вес: {weight_lbs:.2f} lbs\n"
        else:
            text += f"▫️ Вес: {weight_val} {weight_unit}\n"
        
        # Get dimensions
        length = 0
        width = 0
        height = 0
        if package.get('dimensions'):
            length = package.get('dimensions', {}).get('length', 0) or 0
            width = package.get('dimensions', {}).get('width', 0) or 0
            height = package.get('dimensions', {}).get('height', 0) or 0
        else:
            length = order_data.get('packageLength', 0) or 0
            width = order_data.get('packageWidth', 0) or 0
            height = order_data.get('packageHeight', 0) or 0
        
        text += f"▫️ Размеры: {length}×{width}×{height} дюймов\n\n"
        
        text += (
            "*🚚 Перевозчик:*\n"
            f"▫️ {carrier_name} - {service_name}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Стоимость: ${total_cost:.2f}*\n"
            f"💰 *Ваш баланс: ${current_balance:.2f}*\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Check if user has enough balance now
        if current_balance >= total_cost:
            # Restore data to context for ConversationHandler
            context.user_data.update(order_data)
            context.user_data['total_cost'] = total_cost
            context.user_data['pending_order_id'] = str(pending_order.get('_id'))
            
            keyboard = [
                [InlineKeyboardButton("✅ Оплатить и создать лейбл", callback_data="confirm_pending_order")],
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_pending_order")]
            ]
        else:
            needed = total_cost - current_balance
            text += f"\n\n⚠️ *Недостаточно средств!*\nНеобходимо ещё: ${needed:.2f}"
            keyboard = [
                [InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance")],
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_pending_order")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        # No pending order - go back to menu
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ *ИНФОРМАЦИЯ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Нет сохранённого заказа.\n"
            "Начните создание нового лейбла.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("📦 Создать лейбл", callback_data="start_create")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)

async def confirm_pending_order_callback(update, context):
    """Confirm and create label from pending order"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import Database
    from services.users_service import UsersService
    from services.orders_service import OrdersService
    from services.shipengine_service import ShipEngineService
    from services.ai_messages import generate_thank_you_message
    from config import get_settings
    import httpx
    
    query = update.callback_query
    await query.answer("⏳ Создаём лейбл...")
    
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    # Remove buttons
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    db = Database.db
    
    # Get pending order
    pending_order = await db.pending_label_orders.find_one({"telegram_id": user_id})
    
    if not pending_order or not pending_order.get("order_data"):
        await context.bot.send_message(chat_id, "❌ Заказ не найден. Попробуйте создать новый лейбл.")
        return
    
    order_data = pending_order.get("order_data", {})
    total_cost = pending_order.get("total_cost", 0)
    
    # Check balance again
    users_service = UsersService(db)
    user = await users_service.get_user(user_id)
    current_balance = user.get('balance', 0) if user else 0
    
    if current_balance < total_cost:
        needed = total_cost - current_balance
        text = f"❌ Недостаточно средств!\nНеобходимо ещё: ${needed:.2f}"
        keyboard = [[InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance")]]
        await context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Show processing message
    processing_msg = await context.bot.send_message(chat_id, "⏳ *Создаём лейбл...*", parse_mode="Markdown")
    
    try:
        # Get API key based on environment
        settings = get_settings()
        api_config = await db.api_config.find_one({"key": "shipengine_environment"})
        env = api_config.get("value", "sandbox") if api_config else "sandbox"
        
        if env == "production":
            api_key = settings.shipengine_production_key
        else:
            api_key = settings.shipengine_sandbox_key
        
        orders_service = OrdersService(db)
        
        # Prepare order data
        order_data['telegram_user_id'] = user_id
        order_data['total_cost'] = total_cost
        
        # Create label
        result = await orders_service.create_order(order_data)
        
        if result.get('success'):
            # Deduct balance
            actual_user_paid = result.get('userPaid', total_cost)
            await users_service.deduct_for_order(user_id, actual_user_paid)
            
            # Get new balance
            user = await users_service.get_user(user_id)
            new_balance = user.get('balance', 0) if user else 0
            
            # Delete pending order
            await db.pending_label_orders.delete_one({"telegram_id": user_id})
            
            # Get tracking info
            tracking_number = result.get('trackingNumber', 'N/A')
            label_url = result.get('labelDownloadUrl', '')
            carrier_name = order_data.get('selected_rate', {}).get('carrier_friendly_name', '')
            
            # Generate AI thank you message
            try:
                thank_you = await generate_thank_you_message()
            except:
                thank_you = "Спасибо за заказ! 🎉"
            
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
                f"💬 {thank_you}"
            )
            
            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass
            
            # Send success message with PDF and menu button attached
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if label_url:
                # Download and send PDF
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(label_url)
                        if response.status_code == 200:
                            from io import BytesIO
                            pdf_file = BytesIO(response.content)
                            pdf_file.name = f"{tracking_number}.pdf"
                            await context.bot.send_document(
                                chat_id=chat_id,
                                document=pdf_file,
                                filename=f"{tracking_number}.pdf",
                                caption=success_message,
                                parse_mode="Markdown",
                                reply_markup=reply_markup
                            )
                        else:
                            await context.bot.send_message(chat_id, success_message, parse_mode="Markdown", reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Failed to send PDF: {e}")
                    await context.bot.send_message(chat_id, success_message, parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id, success_message, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Notify admin about label creation
            try:
                from services.admin_notifications import notify_label_created
                label_cost = result.get('cost', 0) or 0
                profit = actual_user_paid - label_cost if label_cost else 10
                username = pending_order.get('order_data', {}).get('username') or None
                
                # Try to get username from user data
                if not username:
                    user_data = await db.telegram_users.find_one({"telegram_id": user_id})
                    username = user_data.get('username') if user_data else None
                
                await notify_label_created(
                    telegram_id=user_id,
                    username=username,
                    tracking_number=tracking_number,
                    carrier=carrier_name,
                    cost=actual_user_paid,
                    profit=profit
                )
            except Exception as admin_err:
                logger.warning(f"Failed to send admin notification: {admin_err}")
        else:
            try:
                await processing_msg.delete()
            except:
                pass
            error_msg = result.get('error', 'Неизвестная ошибка')
            await context.bot.send_message(chat_id, f"❌ Ошибка создания лейбла: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error creating label from pending order: {e}")
        
        # Notify admin about error
        try:
            from services.admin_notifications import notify_user_error
            await notify_user_error(
                telegram_id=user_id,
                username=update.effective_user.username if update.effective_user else None,
                error_type="Ошибка создания лейбла (pending)",
                error_message=str(e),
                context="После пополнения баланса"
            )
        except Exception as admin_err:
            logger.warning(f"Failed to send admin error notification: {admin_err}")
        
        try:
            await processing_msg.delete()
        except:
            pass
        await context.bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

async def cancel_pending_order_callback(update, context):
    """Cancel pending order"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import Database
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    # Remove buttons
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Delete pending order
    db = Database.db
    await db.pending_label_orders.delete_one({"telegram_id": user_id})
    
    text = "✅ Заказ отменён."
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    await context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def templates_menu_callback(update, context):
    """Templates menu - FAST"""
    global _templates_service
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    if banned_cache.get(f"ban_{user_id}"):
        await query.answer()
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    await query.answer()
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Remove buttons from old message
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    templates = []
    if _templates_service:
        templates = await _templates_service.get_user_templates(user_id)
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *ШАБЛОНЫ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if templates:
        text += f"У вас {len(templates)} из 10 шаблонов:\n\n"
        keyboard = []
        for t in templates:
            from_city = t.get('ship_from_city', '?')
            to_city = t.get('ship_to_city', '?')
            btn_text = f"📋 {t['name']} ({from_city} → {to_city})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"tpl_view_{t['template_id']}")])
    else:
        text += "У вас пока нет сохранённых шаблонов.\n\n"
        text += "_Шаблоны можно создать при проверке данных перед оплатой._"
        keyboard = []
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send new message
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def template_view_callback(update, context):
    """View a specific template - sends new message"""
    global _templates_service
    
    query = update.callback_query
    
    user_id = str(update.effective_user.id)
    
    # Check if user is banned
    if await check_user_banned(user_id):
        await query.answer()
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    await query.answer()
    
    template_id = query.data.replace("tpl_view_", "")
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    template = None
    if _templates_service:
        template = await _templates_service.get_template(template_id)
    
    if not template:
        await query.message.reply_text("❌ Шаблон не найден")
        return
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *{template['name']}*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Отправитель:*\n"
        f"▫️ {template.get('ship_from_name', '-')}\n"
        f"▫️ {template.get('ship_from_address', '-')}\n"
        f"▫️ {template.get('ship_from_city', '-')}, {template.get('ship_from_state', '-')} {template.get('ship_from_zip', '-')}\n\n"
        "*Получатель:*\n"
        f"▫️ {template.get('ship_to_name', '-')}\n"
        f"▫️ {template.get('ship_to_address', '-')}\n"
        f"▫️ {template.get('ship_to_city', '-')}, {template.get('ship_to_state', '-')} {template.get('ship_to_zip', '-')}\n\n"
        "*Посылка:*\n"
    )
    
    # Display weight in lbs
    weight_lbs = template.get('package_weight_lbs', 0)
    if not weight_lbs:
        # Fallback: convert oz to lbs
        weight_oz = template.get('package_weight', 0) or 0
        weight_lbs = weight_oz / 16 if weight_oz else 0
    
    text += (
        f"▫️ Вес: {weight_lbs:.2f} lbs\n"
        f"▫️ Размеры: {template.get('package_length', 0)}×{template.get('package_width', 0)}×{template.get('package_height', 0)}\n\n"
        f"_Использован: {template.get('use_count', 0)} раз_"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Использовать", callback_data=f"tpl_use_{template_id}")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"tpl_edit_{template_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"tpl_del_{template_id}")],
        [InlineKeyboardButton("◀️ Назад к шаблонам", callback_data="templates_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message instead of editing
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def template_delete_callback(update, context):
    """Delete a template - sends new message"""
    global _templates_service
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    
    user_id = str(update.effective_user.id)
    
    # Check if user is banned
    if await check_user_banned(user_id):
        await query.answer()
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    await query.answer()
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    template_id = query.data.replace("tpl_del_", "")
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    if _templates_service:
        await _templates_service.delete_template(template_id)
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if lang == "en":
        text = "✅ Template deleted"
        back_btn = "◀️ To templates"
    else:
        text = "✅ Шаблон удалён"
        back_btn = "◀️ К шаблонам"
    keyboard = [[InlineKeyboardButton(back_btn, callback_data="templates_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message instead of editing
    await query.message.reply_text(text, reply_markup=reply_markup)

async def refund_info_callback(update, context):
    """Show refund information - sends new message"""
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    
    user_id = str(update.effective_user.id)
    
    logger.info(f"refund_info_callback triggered by user {user_id}")
    
    # Check if user is banned
    if await check_user_banned(user_id):
        await query.answer()
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    await query.answer()
    
    # Get user language
    lang = context.user_data.get('language')
    if not lang:
        lang = await get_user_language(Database.db, user_id)
        context.user_data['language'] = lang
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if lang == "en":
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "↩️ *REFUND LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ *Important information:*\n\n"
            "To request a refund for an unused label, "
            "*at least 4 days* must pass from the moment of its creation.\n\n"
            "To request a refund, contact our agent:\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("👤 Contact agent", url="https://t.me/White_Label_Shipping_Bot_Agent")],
            [InlineKeyboardButton("🏠 Main menu", callback_data="back_to_menu")]
        ]
    else:
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "↩️ *REFUND LABEL*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ *Важная информация:*\n\n"
            "Для оформления возврата средств за неиспользованный label должно пройти "
            "*минимум 4 дня* с момента его создания.\n\n"
            "Для оформления refund обратитесь к нашему агенту:\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("👤 Связаться с агентом", url="https://t.me/White_Label_Shipping_Bot_Agent")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def faq_info_callback(update, context):
    """Show FAQ and service description - sends new message"""
    from database import Database
    from services.localization import get_user_language
    
    query = update.callback_query
    
    user_id = str(update.effective_user.id)
    
    logger.info(f"faq_info_callback triggered by user {user_id}")
    
    # Check if user is banned
    if await check_user_banned(user_id):
        await query.answer()
        await send_banned_message(update.effective_chat.id, context.bot)
        return
    
    await query.answer()
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📖 *WHITE LABEL SHIPPING BOT*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 *О сервисе*\n\n"
        "White Label Shipping Bot — это удобный инструмент для создания "
        "shipping labels напрямую в Telegram. Экономьте время и деньги "
        "на отправке посылок по США!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 *Перевозчики*\n\n"
        "▫️ *USPS* — доступные цены, отличный выбор для небольших посылок\n"
        "▫️ *FedEx* — быстрая доставка, надёжный трекинг\n"
        "▫️ *UPS* — идеально для тяжёлых грузов\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Преимущества*\n\n"
        "✓ Мгновенное создание labels\n"
        "✓ Выгодные тарифы\n"
        "✓ Сохранение шаблонов\n"
        "✓ Удобное управление балансом\n"
        "✓ Возврат за неиспользованные labels\n"
        "✓ Оплата криптовалютой\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "❓ *Частые вопросы*\n\n"
        "*Как пополнить баланс?*\n"
        "Нажмите 💰 Баланс → 💳 Пополнить баланс\n"
        "Принимаем: BTC, ETH, USDT, LTC\n\n"
        "*Как получить refund?*\n"
        "Refund возможен через 4 дня после создания label.\n\n"
        "*Как использовать шаблон?*\n"
        "Сохраните данные после создания label и используйте повторно.\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance")],
        [InlineKeyboardButton("👤 Связаться с агентом", url="https://t.me/White_Label_Shipping_Bot_Agent")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update, context):
    """Handle /help command"""
    help_text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📚 *СПРАВКА ПО ИСПОЛЬЗОВАНИЮ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Доступные команды:*\n\n"
        "/create - Создать новый shipping label\n"
        "▫️ Пошаговый процесс (4 шага)\n"
        "▫️ Время: ~2-3 минуты\n\n"
        "/cancel - Отменить текущее создание\n"
        "▫️ Используйте в процессе создания\n\n"
        "/help - Показать эту справку\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *ПРОЦЕСС СОЗДАНИЯ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Шаг 1:* Адрес отправителя (6 полей)\n"
        "*Шаг 2:* Адрес получателя (6 полей)\n"
        "*Шаг 3:* Параметры посылки (2 поля)\n"
        "*Шаг 4:* Выбор тарифа доставки\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "▫️ Просмотр всех заказов\n"
        "▫️ Скачивание PDF лейблов\n"
        "▫️ Статистика доставок"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def setup_bot_application(environment='sandbox'):
    """Setup bot application with handlers - ULTRA FAST"""
    settings = get_settings()
    
    if environment == 'production':
        bot_token = settings.telegram_bot_token_prod
        shipengine_key = settings.shipengine_production_key
    else:
        bot_token = settings.telegram_bot_token
        shipengine_key = settings.shipengine_sandbox_key
    
    # Create application with reasonable timeouts
    from telegram.ext import ApplicationBuilder
    from telegram.request import HTTPXRequest
    
    # Reasonable request settings (not too aggressive)
    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=10.0,
        read_timeout=15.0,
        write_timeout=15.0,
        pool_timeout=3.0,
    )
    
    # Connect to database BEFORE building application
    await connect_db()
    db = Database.db
    
    # Create MongoDB persistence for state management across pods
    from services.mongo_persistence import MongoPersistence
    persistence = MongoPersistence(db)
    
    application = (
        ApplicationBuilder()
        .token(bot_token)
        .request(request)
        .get_updates_request(request)
        .persistence(persistence)
        .build()
    )
    
    # Create services
    orders_service = OrdersService(db)
    shipengine_service = ShipEngineService(shipengine_key)
    users_service = UsersService(db)
    templates_service = TemplatesService(db)
    
    # Set global references for use in handlers
    global _users_service, _templates_service
    _users_service = users_service
    _templates_service = templates_service
    
    # Add conversation handler (includes start_create button callback)
    conversation_handler_instance = TelegramConversationHandler(
        db, orders_service, shipengine_service, users_service, templates_service
    )
    application.add_handler(conversation_handler_instance.get_conversation_handler())
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))  # Alias for main menu
    application.add_handler(CommandHandler("help", help_command))
    
    # Set bot commands menu - only /menu to avoid duplicates
    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand("menu", "🏠 Главное меню")
    ])
    
    # Add callback handlers for menu buttons (these work when user is NOT in conversation)
    from telegram.ext import CallbackQueryHandler, MessageHandler, filters
    application.add_handler(CallbackQueryHandler(check_balance_callback, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(topup_balance_callback, pattern="^topup_balance$"))
    application.add_handler(CallbackQueryHandler(cancel_topup_callback, pattern="^cancel_topup$"))
    application.add_handler(CallbackQueryHandler(check_payment_status_callback, pattern="^check_payment_"))
    application.add_handler(CallbackQueryHandler(continue_order_callback, pattern="^create_label$"))
    application.add_handler(CallbackQueryHandler(confirm_pending_order_callback, pattern="^confirm_pending_order$"))
    application.add_handler(CallbackQueryHandler(cancel_pending_order_callback, pattern="^cancel_pending_order$"))
    application.add_handler(CallbackQueryHandler(change_language_callback, pattern="^change_language$"))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_lang_"))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(templates_menu_callback, pattern="^templates_menu$"))
    application.add_handler(CallbackQueryHandler(template_view_callback, pattern="^tpl_view_"))
    application.add_handler(CallbackQueryHandler(template_delete_callback, pattern="^tpl_del_"))
    application.add_handler(CallbackQueryHandler(refund_info_callback, pattern="^refund_info$"))
    application.add_handler(CallbackQueryHandler(faq_info_callback, pattern="^faq_info$"))
    
    # Text handler for topup amount - in group 2 (lowest priority)
    # Only processes if user is in topup mode AND not in ConversationHandler
    async def handle_topup_text(update, context):
        """Handle text input ONLY for topup amount"""
        if context.user_data.get('awaiting_topup_amount'):
            await process_topup_amount(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topup_text), group=2)
    
    logger.info("Bot application setup complete")
    return application

# Global applications for both environments
sandbox_app = None
production_app = None

async def get_or_create_app(environment='sandbox'):
    """Get or create bot application for environment"""
    global sandbox_app, production_app
    
    if environment == 'production':
        if production_app is None:
            production_app = await setup_bot_application('production')
            await production_app.initialize()
            logger.info("Production bot initialized")
        return production_app
    else:
        if sandbox_app is None:
            sandbox_app = await setup_bot_application('sandbox')
            await sandbox_app.initialize()
            logger.info("Sandbox bot initialized")
        return sandbox_app

if __name__ == "__main__":
    # For testing polling mode
    async def main():
        app = await setup_bot_application('sandbox')
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info("Bot is running in polling mode...")
        
        # Run forever
        while True:
            await asyncio.sleep(1)
    
    asyncio.run(main())
