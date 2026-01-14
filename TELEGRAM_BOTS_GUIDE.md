# 🤖 Telegram Bots - Quick Reference

## Active Bots

### 1️⃣ Sandbox Bot (Test)
- **Username**: @whitelabel_shipping_bot_test_bot
- **Bot ID**: 8560388458
- **Webhook**: `/api/telegram/webhook`
- **Purpose**: Testing and development
- **Status**: ✅ Active

### 2️⃣ Production Bot
- **Username**: @whitelabel_shipping_bot
- **Bot ID**: 8492458522  
- **Webhook**: `/api/telegram/webhook-prod`
- **Purpose**: Live production use
- **Status**: ✅ Active

## Quick Start

### Test the Bots

**Sandbox Bot:**
```
1. Open: https://t.me/whitelabel_shipping_bot_test_bot
2. Send: /start
3. Try: /create to select carrier
```

**Production Bot:**
```
1. Open: https://t.me/whitelabel_shipping_bot
2. Send: /start
3. Try: /create to select carrier
```

## Available Commands

Both bots support:
- `/start` - Welcome message with instructions
- `/create` - Start label creation (choose carrier)
- `/help` - Show help information

## Architecture

```
User → Telegram Bot → Webhook → Backend → Database
                          ↓
                    ShipEngine API
                          ↓
                    Create Label
```

**Webhook Routes:**
- Sandbox: `POST /api/telegram/webhook`
- Production: `POST /api/telegram/webhook-prod`

## Switching Between Environments

The system automatically routes to correct bot based on webhook endpoint:

**For Sandbox (Test) Bot:**
- Uses: `TELEGRAM_BOT_TOKEN`
- Endpoint: `/api/telegram/webhook`

**For Production Bot:**
- Uses: `TELEGRAM_BOT_TOKEN_PROD`  
- Endpoint: `/api/telegram/webhook-prod`

## Configuration Files

**Environment Variables** (`/app/backend/.env`):
```env
# Sandbox Bot
TELEGRAM_BOT_TOKEN="8560388458:AAHxT-vYpImOpy49lMnaXpSHDM-vtnOn6ZE"

# Production Bot
TELEGRAM_BOT_TOKEN_PROD="8492458522:AAE3dLsl2blomb5WxP7w4S0bqvrs1M4WSsM"
```

## Management Scripts

### Setup Both Webhooks
```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

### Check Webhook Status
```bash
cd /app/backend
python3 -c "
from telegram import Bot
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def check_webhooks():
    # Check sandbox
    sandbox_bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    sandbox_info = await sandbox_bot.get_webhook_info()
    print('SANDBOX:', sandbox_info.url)
    
    # Check production
    prod_bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN_PROD'))
    prod_info = await prod_bot.get_webhook_info()
    print('PRODUCTION:', prod_info.url)

asyncio.run(check_webhooks())
"
```

### View Recent Messages
```bash
# Check backend logs for bot activity
tail -f /var/log/supervisor/backend.out.log | grep telegram
```

## Integration with Web Dashboard

Both bots integrate with the same web dashboard:
- **URL**: https://shipbot-labels.preview.emergentagent.com
- **Database**: Shared MongoDB (shipbot_database)
- **Collections**: 
  - `orders` - All shipping labels
  - `telegram_users` - Bot users
  - `api_config` - ShipEngine settings

## User Flow

1. **User starts bot** → `/start` command
2. **User creates label** → `/create` command
3. **Bot shows carriers** → Inline keyboard (USPS, FedEx, UPS)
4. **User selects carrier** → Stored in session
5. **Bot directs to dashboard** → Complete form on web
6. **Label created** → Saved in database
7. **User notified** → Bot sends confirmation

## Monitoring

### Check Bot Health
```bash
# Test sandbox bot
curl -s "https://api.telegram.org/bot8560388458:AAHxT-vYpImOpy49lMnaXpSHDM-vtnOn6ZE/getMe" | python3 -m json.tool

# Test production bot
curl -s "https://api.telegram.org/bot8492458522:AAE3dLsl2blomb5WxP7w4S0bqvrs1M4WSsM/getMe" | python3 -m json.tool
```

### Database Stats
```bash
mongosh
use shipbot_database
db.telegram_users.countDocuments()  # Total users
db.orders.countDocuments({"telegram_user_id": {$exists: true}})  # Orders from bot
```

## Troubleshooting

### Bot not responding?

1. **Check webhook:**
```bash
cd /app/backend && python3 setup_dual_webhooks.py
```

2. **Check backend logs:**
```bash
tail -50 /var/log/supervisor/backend.err.log
```

3. **Restart backend:**
```bash
sudo supervisorctl restart backend
```

### Webhook errors?

Check that:
- ✅ Backend is running
- ✅ HTTPS endpoint is accessible
- ✅ No firewall blocking
- ✅ Valid SSL certificate

## Security

- ✅ Tokens stored in `.env` (not in git)
- ✅ Webhook secret for validation
- ✅ Separate endpoints for sandbox/production
- ✅ HTTPS required for webhooks
- ✅ MongoDB connection secured

## Next Steps

- [ ] Add full label creation wizard in bot
- [ ] Add /orders command to view user's labels
- [ ] Add /track command for package tracking
- [ ] Add /cancel command to cancel orders
- [ ] Add admin commands for bot management
- [ ] Add rate limiting for spam protection
- [ ] Add analytics dashboard for bot usage
