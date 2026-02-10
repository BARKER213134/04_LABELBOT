#!/usr/bin/env python3
"""
Run Telegram bot in polling mode (for testing/development)
"""
import asyncio
import logging
from telegram_bot_app import setup_bot_application

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run bot in polling mode"""
    logger.info("Starting Telegram bot in POLLING mode...")
    
    app = await setup_bot_application('sandbox')
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    logger.info("Bot is running in polling mode. Press Ctrl+C to stop.")
    
    try:
        # Run forever
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
