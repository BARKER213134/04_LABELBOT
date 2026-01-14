#!/usr/bin/env python3
"""
Setup webhooks for both Telegram bots (Sandbox and Production)
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SANDBOX_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PRODUCTION_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_PROD')
BASE_WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Разные эндпоинты для разных ботов
SANDBOX_WEBHOOK = BASE_WEBHOOK_URL
PRODUCTION_WEBHOOK = BASE_WEBHOOK_URL.replace('/webhook', '/webhook-prod')

async def setup_bot_webhook(token: str, webhook_url: str, bot_name: str):
    """Setup webhook for a specific bot"""
    print(f"\n{'='*60}")
    print(f"Setting up {bot_name}")
    print(f"{'='*60}")
    
    bot = Bot(token=token)
    
    try:
        # Get bot info
        me = await bot.get_me()
        print(f"Bot Username: @{me.username}")
        print(f"Bot Name: {me.first_name}")
        print(f"Bot ID: {me.id}")
        
        # Check current webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\nCurrent webhook: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        
        if webhook_info.url == webhook_url:
            print(f"✅ Webhook already configured correctly!")
            return True
        
        # Set new webhook
        print(f"\nSetting webhook to: {webhook_url}")
        success = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        
        if success:
            print(f"✅ Webhook set successfully!")
            
            # Verify
            webhook_info = await bot.get_webhook_info()
            print(f"Verified URL: {webhook_info.url}")
            return True
        else:
            print(f"❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main function"""
    print("=" * 60)
    print("ShipBot - Dual Telegram Bot Webhook Setup")
    print("=" * 60)
    
    # Setup Sandbox bot
    sandbox_success = await setup_bot_webhook(
        SANDBOX_TOKEN,
        SANDBOX_WEBHOOK,
        "SANDBOX BOT (Test)"
    )
    
    # Setup Production bot
    production_success = await setup_bot_webhook(
        PRODUCTION_TOKEN,
        PRODUCTION_WEBHOOK,
        "PRODUCTION BOT"
    )
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Sandbox Bot: {'✅ Ready' if sandbox_success else '❌ Failed'}")
    print(f"Production Bot: {'✅ Ready' if production_success else '❌ Failed'}")
    
    if sandbox_success:
        print(f"\n📱 Test Sandbox: https://t.me/whitelabel_shipping_bot_test_bot")
    
    if production_success:
        print(f"📱 Production: https://t.me/whitelabel_shipping_bot")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
