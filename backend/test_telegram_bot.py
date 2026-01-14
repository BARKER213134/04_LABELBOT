#!/usr/bin/env python3
"""
Test script to send a message to Telegram bot
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def test_bot():
    """Test bot by getting updates"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        print("🤖 Getting bot updates...")
        updates = await bot.get_updates(limit=5)
        
        if not updates:
            print("\n⚠️  No updates found. Please:")
            print("   1. Open Telegram")
            print("   2. Search for @whitelabel_shipping_bot_test_bot")
            print("   3. Send /start command")
            print("   4. Run this script again")
            return
        
        print(f"\n✅ Found {len(updates)} updates:\n")
        
        for update in updates:
            if update.message:
                msg = update.message
                print(f"Message from {msg.from_user.first_name} (@{msg.from_user.username}):")
                print(f"  Chat ID: {msg.chat_id}")
                print(f"  Text: {msg.text}")
                print(f"  Date: {msg.date}")
                print()
        
        print("💡 The webhook is active, so messages are being processed automatically!")
        print("Check the backend logs: tail -f /var/log/supervisor/backend.out.log")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot())
