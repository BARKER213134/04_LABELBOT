#!/usr/bin/env python3
"""
Setup webhooks for both Telegram bots to use the same endpoint
The backend will automatically switch between bots based on ShipEngine environment
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
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Одинаковый для обоих

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
    print("ShipBot - Unified Webhook Setup")
    print("Both bots will use the same webhook endpoint")
    print("Backend switches bots based on ShipEngine environment")
    print("=" * 60)
    
    # Setup Sandbox bot
    sandbox_success = await setup_bot_webhook(
        SANDBOX_TOKEN,
        WEBHOOK_URL,
        "SANDBOX BOT (Test) - for sandbox environment"
    )
    
    # Setup Production bot
    production_success = await setup_bot_webhook(
        PRODUCTION_TOKEN,
        WEBHOOK_URL,  # Тот же endpoint!
        "PRODUCTION BOT - for production environment"
    )
    
    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    print(f"Webhook endpoint: {WEBHOOK_URL}")
    print(f"Sandbox Bot: {'✅ Ready' if sandbox_success else '❌ Failed'}")
    print(f"Production Bot: {'✅ Ready' if production_success else '❌ Failed'}")
    
    print("\n" + "=" * 60)
    print("HOW IT WORKS")
    print("=" * 60)
    print("1. Both bots send updates to the same webhook")
    print("2. Backend checks current ShipEngine environment")
    print("3. If environment = 'sandbox' → uses test bot")
    print("4. If environment = 'production' → uses production bot")
    print("5. Switch environment in Admin Panel to change bot")
    
    if sandbox_success:
        print(f"\n📱 Test with Sandbox: https://t.me/whitelabel_shipping_bot_test_bot")
    
    if production_success:
        print(f"📱 Test with Production: https://t.me/whitelabel_shipping_bot")
    
    print("\n💡 Go to Admin Panel to switch between sandbox/production")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
