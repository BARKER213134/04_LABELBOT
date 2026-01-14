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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global reference to users_service for use in handlers
_users_service = None

async def start_command(update, context):
    """Handle /start command"""
    global _users_service
    
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
    await telegram_service.send_welcome_message(update.effective_chat.id, balance)

async def check_balance_callback(update, context):
    """Handle balance check button"""
    global _users_service
    
    query = update.callback_query
    await query.answer()
    
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
        "Для пополнения баланса обратитесь к администратору."
    )
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("📦 Создать Label", callback_data="start_create")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def back_to_menu_callback(update, context):
    """Handle back to menu button"""
    global _users_service
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    balance = 0.0
    
    if _users_service:
        user = await _users_service.get_user(user_id)
        if user:
            balance = user.get('balance', 0.0)
    
    telegram_service = TelegramService()
    await telegram_service.send_welcome_message(query.message.chat_id, balance)

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
        "https://labelgen-4.preview.emergentagent.com\n\n"
        "▫️ Просмотр всех заказов\n"
        "▫️ Скачивание PDF лейблов\n"
        "▫️ Статистика доставок"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

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
    
    # Set global reference for use in handlers
    global _users_service
    _users_service = users_service
    
    # Add conversation handler (includes start_create button callback)
    conversation_handler_instance = TelegramConversationHandler(db, orders_service, shipengine_service, users_service)
    application.add_handler(conversation_handler_instance.get_conversation_handler())
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add callback handler for back to menu button
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    
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
