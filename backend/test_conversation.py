#!/usr/bin/env python3
"""
Test Telegram bot conversation handler
Sends a test /create command to the bot
"""
import asyncio
from telegram import Bot
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SANDBOX_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def test_create_command():
    """Test /create command"""
    bot = Bot(token=SANDBOX_TOKEN)
    
    try:
        # Get bot info
        me = await bot.get_me()
        print(f"Bot: @{me.username}")
        
        # Check webhook
        webhook_info = await bot.get_webhook_info()
        print(f"Webhook: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        
        # Instruct user
        print("\n" + "="*60)
        print("TO TEST THE CONVERSATION:")
        print("="*60)
        print(f"1. Open Telegram and find @{me.username}")
        print("2. Send: /create")
        print("3. Follow the wizard:")
        print("   - Ship From Name")
        print("   - Ship From Address")
        print("   - Ship From City")
        print("   - Ship From State (2 letters)")
        print("   - Ship From ZIP")
        print("   - Ship From Phone (or 'skip')")
        print("   - Ship To Name")
        print("   - Ship To Address") 
        print("   - Ship To City")
        print("   - Ship To State")
        print("   - Ship To ZIP")
        print("   - Ship To Phone (or 'skip')")
        print("   - Package Weight (ounces)")
        print("   - Package Dimensions (L W H in inches)")
        print("   - Select Carrier (button)")
        print("   - Select Service (button)")
        print("   - Confirm (button)")
        print("\n4. Watch backend logs:")
        print("   tail -f /var/log/supervisor/backend.out.log")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_create_command())
