#!/usr/bin/env python3
"""
Telegram Bot Application Runner
This runs the bot with webhook mode and conversation handlers
"""
import asyncio
import logging
from telegram.ext import Application, CommandHandler
from config import get_settings
from database import Database, connect_db
from services.telegram_service import TelegramService
from services.telegram_conversation import TelegramConversationHandler
from services.orders_service import OrdersService
from services.shipengine_service import ShipEngineService
from services.users_service import UsersService
from services.templates_service import TemplatesService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global references for use in handlers
_users_service = None
_templates_service = None

async def start_command(update, context):
    """Handle /start command"""
    global _users_service
    
    # Remove buttons from the previous menu message (keep the message text)
    try:
        last_menu_msg_id = context.user_data.get('last_menu_message_id')
        if last_menu_msg_id:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id,
                message_id=last_menu_msg_id,
                reply_markup=None
            )
    except Exception as e:
        logger.debug(f"Could not remove buttons from previous menu: {e}")
    
    balance = 0.0
    # Create/update user in database
    if _users_service:
        tg_user = update.effective_user
        user = await _users_service.get_or_create_user(
            telegram_id=str(tg_user.id),
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name
        )
        balance = user.get('balance', 0.0)
        logger.info(f"User {tg_user.id} ({tg_user.username}) - balance: ${balance:.2f}")
    
    telegram_service = TelegramService()
    sent_message = await telegram_service.send_welcome_message(update.effective_chat.id, balance)
    
    # Store the new menu message id
    if sent_message:
        context.user_data['last_menu_message_id'] = sent_message.message_id

async def check_balance_callback(update, context):
    """Handle balance check button - sends new message"""
    global _users_service
    
    query = update.callback_query
    await query.answer()
    
    logger.info(f"check_balance_callback triggered by user {update.effective_user.id}")
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    user_id = str(update.effective_user.id)
    balance = 0.0
    total_orders = 0
    total_spent = 0.0
    
    if _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
            total_orders = user.get('total_orders', 0)
            total_spent = user.get('total_spent', 0.0)
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 *ВАШ БАЛАНС*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"▫️ Доступно: *${balance:.2f}*\n"
        f"▫️ Заказов: {total_orders}\n"
        f"▫️ Потрачено: ${total_spent:.2f}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💳 *Способы оплаты:*\n"
        "▫️ BTC, ETH, USDT, LTC\n"
        "▫️ Минимум: $10"
    )
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def topup_balance_callback(update, context):
    """Handle balance top-up request - sends new message"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    logger.info(f"topup_balance_callback triggered by user {user_id}")
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Store state in context
    context.user_data['awaiting_topup_amount'] = True
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💳 *ПОПОЛНЕНИЕ БАЛАНСА*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 *Введите сумму пополнения в USD*\n\n"
        "▫️ Минимум: $10\n"
        "▫️ Криптовалюты: BTC, ETH, USDT, LTC\n\n"
        "_Например: 25 или 50.00_"
    )
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_topup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message and store its ID
    sent_msg = await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data['topup_message_id'] = sent_msg.message_id
    context.user_data['topup_chat_id'] = sent_msg.chat_id


async def process_topup_amount(update, context):
    """Process the entered top-up amount - sends new messages"""
    if not context.user_data.get('awaiting_topup_amount'):
        return False
    
    user_id = str(update.effective_user.id)
    text_input = update.message.text.strip()
    
    # Clear the waiting flag
    context.user_data['awaiting_topup_amount'] = False
    
    # Remove buttons from previous message
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
        
        if amount < 10:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_topup")]]
            sent_msg = await update.message.reply_text(
                "❌ *Минимальная сумма: $10*\n\nПожалуйста, введите сумму от $10",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            context.user_data['awaiting_topup_amount'] = True
            context.user_data['topup_message_id'] = sent_msg.message_id
            context.user_data['topup_chat_id'] = sent_msg.chat_id
            return True
        
        if amount > 10000:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_topup")]]
            sent_msg = await update.message.reply_text(
                "❌ *Максимальная сумма: $10,000*\n\nПожалуйста, введите меньшую сумму",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            context.user_data['awaiting_topup_amount'] = True
            context.user_data['topup_message_id'] = sent_msg.message_id
            context.user_data['topup_chat_id'] = sent_msg.chat_id
            return True
        
        # Create payment invoice - send new message
        await create_crypto_invoice(update, context, user_id, amount)
        return True
        
    except ValueError:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_topup")]]
        sent_msg = await update.message.reply_text(
            "❌ *Некорректная сумма*\n\nВведите число, например: 25 или 50.00",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        context.user_data['awaiting_topup_amount'] = True
        context.user_data['topup_message_id'] = sent_msg.message_id
        context.user_data['topup_chat_id'] = sent_msg.chat_id
        return True


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


async def create_crypto_invoice(update, context, user_id: str, amount: float, message_id=None, chat_id=None):
    """Create OxaPay crypto invoice"""
    from database import Database
    from services.oxapay_service import OxaPayService
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Edit existing message to show loading
    if message_id and chat_id:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⏳ *Создаю платёж...*",
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
            keyboard = [
                [InlineKeyboardButton("💳 Оплатить криптой", url=payment_url)],
                [InlineKeyboardButton("🔄 Проверить статус", callback_data=f"check_payment_{track_id}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit the same message with result
            if message_id and chat_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        else:
            raise Exception("Failed to create invoice")
            
    except Exception as e:
        logger.error(f"Failed to create crypto invoice: {e}")
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="topup_balance")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit message to show error
        if message_id and chat_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ *Ошибка создания платежа*\n\n{str(e)}\n\nПопробуйте позже.",
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

async def back_to_menu_callback(update, context):
    """Handle back to menu button - works like /start command"""
    global _users_service
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    balance = 0.0
    
    if _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
    
    # Remove buttons from the current message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception as e:
        logger.debug(f"Could not remove buttons from message: {e}")
    
    # Send new welcome message with menu (like /start)
    telegram_service = TelegramService()
    sent_message = await telegram_service.send_welcome_message(query.message.chat_id, balance)
    
    # Store the new menu message id
    if sent_message:
        context.user_data['last_menu_message_id'] = sent_message.message_id

async def templates_menu_callback(update, context):
    """Show templates menu - sends new message"""
    global _templates_service
    
    query = update.callback_query
    await query.answer()
    
    logger.info(f"templates_menu_callback triggered by user {update.effective_user.id}")
    
    user_id = str(update.effective_user.id)
    
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
        f"▫️ Вес: {template.get('package_weight', 0)} oz\n"
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
    
    query = update.callback_query
    await query.answer()
    
    template_id = query.data.replace("tpl_del_", "")
    
    # Remove buttons from old message (keep text)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    if _templates_service:
        await _templates_service.delete_template(template_id)
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = "✅ Шаблон удалён"
    keyboard = [[InlineKeyboardButton("◀️ К шаблонам", callback_data="templates_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as NEW message instead of editing
    await query.message.reply_text(text, reply_markup=reply_markup)

async def refund_info_callback(update, context):
    """Show refund information"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"refund_info_callback triggered by user {update.effective_user.id}")
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
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
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def faq_info_callback(update, context):
    """Show FAQ and service description"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"faq_info_callback triggered by user {update.effective_user.id}")
    
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
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

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
        "💡 *Веб-дашборд для управления:*\n"
        "https://shipnow-bot.preview.emergentagent.com\n\n"
        "▫️ Просмотр всех заказов\n"
        "▫️ Скачивание PDF лейблов\n"
        "▫️ Статистика доставок"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_text_input(update, context):
    """Handle text input for top-up amount"""
    # Check if we're waiting for top-up amount
    if context.user_data.get('awaiting_topup_amount'):
        await process_topup_amount(update, context)
        return
    
    # If not waiting for anything specific, ignore
    # The ConversationHandler will handle text input during label creation


async def setup_bot_application(environment='sandbox'):
    """Setup bot application with handlers"""
    settings = get_settings()
    
    # Select bot token and API key based on environment
    if environment == 'production':
        bot_token = settings.telegram_bot_token_prod
        shipengine_key = settings.shipengine_production_key
        logger.info("Setting up PRODUCTION bot")
    else:
        bot_token = settings.telegram_bot_token
        shipengine_key = settings.shipengine_sandbox_key
        logger.info("Setting up SANDBOX bot")
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Connect to database
    await connect_db()
    db = Database.db
    
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
    application.add_handler(CommandHandler("help", help_command))
    
    # Add callback handlers for menu buttons (these work when user is NOT in conversation)
    from telegram.ext import CallbackQueryHandler, MessageHandler, filters
    application.add_handler(CallbackQueryHandler(check_balance_callback, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(topup_balance_callback, pattern="^topup_balance$"))
    application.add_handler(CallbackQueryHandler(check_payment_status_callback, pattern="^check_payment_"))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(templates_menu_callback, pattern="^templates_menu$"))
    application.add_handler(CallbackQueryHandler(template_view_callback, pattern="^tpl_view_"))
    application.add_handler(CallbackQueryHandler(template_delete_callback, pattern="^tpl_del_"))
    application.add_handler(CallbackQueryHandler(refund_info_callback, pattern="^refund_info$"))
    application.add_handler(CallbackQueryHandler(faq_info_callback, pattern="^faq_info$"))
    
    # Add message handler for top-up amount input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
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
