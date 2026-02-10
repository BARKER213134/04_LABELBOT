#!/usr/bin/env python3
"""
Setup webhook for production Telegram bot
Run this script after deployment to set up the webhook
"""
import asyncio
import os
import sys
from telegram import Bot

async def setup_production_webhook():
    """Setup webhook for production bot"""
    
    # Get production token
    prod_token = os.environ.get("TELEGRAM_BOT_TOKEN_PROD", "8492458522:AAE3dLsl2blomb5WxP7w4S0bqvrs1M4WSsM")
    
    # Get webhook URL from argument or environment
    if len(sys.argv) > 1:
        webhook_url = sys.argv[1]
    else:
        webhook_url = os.environ.get("PRODUCTION_WEBHOOK_URL", "")
    
    if not webhook_url:
        print("Usage: python setup_production_webhook.py <webhook_url>")
        print("Example: python setup_production_webhook.py https://your-domain.com/api/telegram/webhook")
        return False
    
    print(f"Setting up production webhook...")
    print(f"Bot token: {prod_token[:20]}...")
    print(f"Webhook URL: {webhook_url}")
    
    try:
        bot = Bot(token=prod_token)
        
        # Get current webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"\nCurrent webhook: {webhook_info.url or 'Not set'}")
        
        if webhook_info.url == webhook_url:
            print("✅ Webhook already set correctly!")
            return True
        
        # Set new webhook
        success = await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"]
        )
        
        if success:
            # Verify
            webhook_info = await bot.get_webhook_info()
            print(f"\n✅ Webhook set successfully!")
            print(f"New URL: {webhook_info.url}")
            return True
        else:
            print("❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(setup_production_webhook())
