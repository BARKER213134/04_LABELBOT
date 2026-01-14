#!/usr/bin/env python3
"""
Script to set up Telegram webhook for ShipBot
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

async def setup_webhook():
    """Set up webhook for Telegram bot"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        # Get current webhook info
        print("Checking current webhook...")
        webhook_info = await bot.get_webhook_info()
        print(f"Current webhook URL: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        
        if webhook_info.url == WEBHOOK_URL:
            print("✅ Webhook already configured correctly!")
            return
        
        # Set new webhook
        print(f"\nSetting webhook to: {WEBHOOK_URL}")
        success = await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        
        if success:
            print("✅ Webhook set successfully!")
            
            # Verify webhook
            webhook_info = await bot.get_webhook_info()
            print(f"\nVerification:")
            print(f"  URL: {webhook_info.url}")
            print(f"  Pending updates: {webhook_info.pending_update_count}")
        else:
            print("❌ Failed to set webhook")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def get_bot_info():
    """Get bot information"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        me = await bot.get_me()
        print("\n📱 Bot Information:")
        print(f"  Username: @{me.username}")
        print(f"  Name: {me.first_name}")
        print(f"  ID: {me.id}")
        print(f"  Can join groups: {me.can_join_groups}")
        print(f"  Can read messages: {me.can_read_all_group_messages}")
    except Exception as e:
        print(f"❌ Error getting bot info: {e}")

async def delete_webhook():
    """Delete webhook (for testing with polling)"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        success = await bot.delete_webhook(drop_pending_updates=True)
        if success:
            print("✅ Webhook deleted successfully!")
        else:
            print("❌ Failed to delete webhook")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Main function"""
    print("=" * 60)
    print("ShipBot Telegram Webhook Setup")
    print("=" * 60)
    
    await get_bot_info()
    await setup_webhook()
    
    print("\n" + "=" * 60)
    print("Setup complete! Start chatting with your bot:")
    print(f"https://t.me/whitelabel_shipping_bot_test_bot")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
