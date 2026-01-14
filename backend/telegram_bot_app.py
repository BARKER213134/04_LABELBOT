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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    """Handle /start command"""
    telegram_service = TelegramService()
    await telegram_service.send_welcome_message(update.effective_chat.id)

async def back_to_menu_callback(update, context):
    """Handle back to menu button"""
    query = update.callback_query
    await query.answer()
    
    telegram_service = TelegramService()
    await telegram_service.send_welcome_message(query.message.chat_id)

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
        "*Шаг 4:* Выбор перевозчика и сервиса\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *Веб-дашборд для управления:*\n"
        "https://shipbot-labels.preview.emergentagent.com\n\n"
        "▫️ Просмотр всех заказов\n"
        "▫️ Скачивание PDF лейблов\n"
        "▫️ Статистика доставок"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def setup_bot_application(environment='sandbox'):
    """Setup bot application with handlers"""
    settings = get_settings()
    
    # Select bot token based on environment
    if environment == 'production':
        bot_token = settings.telegram_bot_token_prod
        logger.info("Setting up PRODUCTION bot")
    else:
        bot_token = settings.telegram_bot_token
        logger.info("Setting up SANDBOX bot")
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Connect to database
    await connect_db()
    db = Database.db
    
    # Create services
    orders_service = OrdersService(db)
    
    # Add conversation handler (includes start_create button callback)
    conversation_handler_instance = TelegramConversationHandler(db, orders_service)
    application.add_handler(conversation_handler_instance.get_conversation_handler())
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
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
