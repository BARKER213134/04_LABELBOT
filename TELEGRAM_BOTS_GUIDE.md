# 🤖 Telegram Bots - Environment-Based Switching

## How It Works

**Unified Webhook Architecture:**
- Both bots send updates to **the same webhook endpoint**
- Backend automatically switches between bots based on **ShipEngine environment**
- Change environment in **Admin Panel** to switch bots

```
Admin Panel → ShipEngine Environment → Telegram Bot Selection

Sandbox Environment  → @whitelabel_shipping_bot_test_bot
Production Environment → @whitelabel_shipping_bot
```

## Active Bots

### 1️⃣ Sandbox Bot (Test)
- **Username**: @whitelabel_shipping_bot_test_bot
- **Bot ID**: 8560388458
- **Active when**: ShipEngine environment = "sandbox"
- **Purpose**: Testing with sandbox API keys

### 2️⃣ Production Bot
- **Username**: @whitelabel_shipping_bot
- **Bot ID**: 8492458522  
- **Active when**: ShipEngine environment = "production"
- **Purpose**: Live production with real API keys

## Webhook Configuration

**Single Endpoint for Both Bots:**
```
POST /api/telegram/webhook
```

**Logic:**
1. Webhook receives update from ANY bot
2. Backend reads current ShipEngine environment from DB
3. Backend uses appropriate bot token to respond
4. All messages/responses use correct bot automatically

## Testing Workflow

### 1. Test in Sandbox Environment

```bash
# 1. Go to Admin Panel
# 2. Select "Sandbox (Test)"
# 3. Save Changes

# 4. Open Telegram
https://t.me/whitelabel_shipping_bot_test_bot

# 5. Send /start
# Bot responds using TEST bot
```

### 2. Deploy to Production

```bash
# 1. Go to Admin Panel
# 2. Select "Production (Live)"  
# 3. Save Changes

# 4. Open Telegram
https://t.me/whitelabel_shipping_bot

# 5. Send /start
# Bot responds using PRODUCTION bot
```

## Available Commands

Both bots support:
- `/start` - Welcome message
- `/create` - Start label creation
- `/help` - Show help

## Configuration

**Environment Variables** (`/app/backend/.env`):
```env
# Sandbox Bot Token
TELEGRAM_BOT_TOKEN="8560388458:AAHxT-vYpImOpy49lMnaXpSHDM-vtnOn6ZE"

# Production Bot Token
TELEGRAM_BOT_TOKEN_PROD="8492458522:AAE3dLsl2blomb5WxP7w4S0bqvrs1M4WSsM"

# Shared Webhook
WEBHOOK_URL="https://shipbot-dashboard.preview.emergentagent.com/api/telegram/webhook"
```

## Setup Script

```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

**This script:**
- ✅ Configures both bots to use same webhook
- ✅ Verifies webhook status
- ✅ Shows how environment switching works

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Admin Panel                         │
│         [Sandbox] ◄──► [Production]                     │
│              │              │                            │
│              ▼              ▼                            │
│         ShipEngine Environment                          │
│         (stored in MongoDB)                             │
└─────────────────────────────────────────────────────────┘
                         │
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Telegram Webhook Handler                   │
│          /api/telegram/webhook                          │
│                                                          │
│  1. Receive update from any bot                         │
│  2. Check environment from DB                           │
│  3. Select appropriate bot token                        │
│  4. Send response using correct bot                     │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌─────────────┐              ┌──────────────┐
  │ Sandbox Bot │              │ Production   │
  │   (Test)    │              │     Bot      │
  └─────────────┘              └──────────────┘
```

## Database Integration

**Collections Used:**
- `api_config` - Stores current environment ('sandbox' or 'production')
- `orders` - Stores all orders with environment info
- `telegram_users` - Tracks users from both bots

**Environment Check:**
```python
# Backend automatically does this:
env_config = await db.api_config.find_one({"_id": "api_config"})
current_env = env_config.get("environment", "sandbox")

if current_env == "production":
    bot = ProductionBot()
else:
    bot = SandboxBot()
```

## Monitoring

### Check Current Environment
```bash
# Via API
curl https://shipbot-dashboard.preview.emergentagent.com/api/admin/api-config

# Via MongoDB
mongosh
use shipbot_database
db.api_config.findOne({"_id": "api_config"})
```

### Check Which Bot Responded
```bash
# Backend logs show bot selection
tail -f /var/log/supervisor/backend.out.log | grep "Telegram"
```

## Benefits of This Approach

✅ **Single Deployment**: One codebase, two bots
✅ **Easy Switching**: Change in Admin Panel, instant effect
✅ **Synchronized**: Environment, API keys, and bot always match
✅ **Clear Separation**: Test vs Production completely isolated
✅ **No Manual Work**: Automatic bot selection

## Troubleshooting

### Wrong bot responding?

1. **Check current environment:**
```bash
curl https://shipbot-dashboard.preview.emergentagent.com/api/admin/api-config
```

2. **Switch in Admin Panel:**
   - Go to Admin Panel
   - Select correct environment
   - Click "Save Changes"

3. **Verify webhook:**
```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

### Both bots not responding?

1. **Check backend logs:**
```bash
tail -50 /var/log/supervisor/backend.err.log
```

2. **Restart backend:**
```bash
sudo supervisorctl restart backend
```

3. **Reconfigure webhooks:**
```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

## Security

- ✅ Separate tokens for test/production
- ✅ Environment stored securely in DB
- ✅ Single webhook endpoint (easier to secure)
- ✅ Automatic environment matching
- ✅ No manual token switching needed

## Next Steps

- [ ] Add environment indicator in bot responses
- [ ] Add /status command to show current environment
- [ ] Log environment switches in audit trail
- [ ] Add notification when environment changes
- [ ] Dashboard widget showing active bot
