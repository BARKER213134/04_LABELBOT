# ShipBot - Telegram Bot for Shipping Labels

## Original Problem Statement
Create a Telegram bot for generating shipping labels using the ShipEngine API with web admin panel.

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + Tailwind CSS
- **Database:** MongoDB Atlas
- **Bot:** python-telegram-bot v22.5
- **APIs:** ShipEngine, OxaPay, OpenAI (via emergentintegrations)

## What's Been Implemented
- Full Telegram bot with multi-step wizard for label creation
- Admin panel (Dashboard, Orders, Users, Broadcast, Settings)
- ShipEngine integration (USPS, FedEx, UPS)
- OxaPay crypto payments
- Template management
- i18n (Russian/English)
- Maintenance mode with whitelist
- User balance system
- AI thank-you messages

## Key Files
- `/app/backend/server.py` - FastAPI server
- `/app/backend/telegram_bot_app.py` - Bot handlers
- `/app/backend/services/telegram_conversation.py` - Conversation wizard
- `/app/backend/services/shipengine_service.py` - ShipEngine API
- `/app/backend/services/health_monitor.py` - Health monitoring
- `/app/backend/services/orders_service.py` - Order creation
- `/app/backend/routes/admin.py` - Admin API
- `/app/backend/routes/telegram.py` - Webhook handler
- `/app/backend/database.py` - MongoDB connection with retry
- `/app/frontend/src/pages/AdminPanel.jsx` - Admin UI

## API Endpoints
- `POST /api/telegram/webhook` - Telegram webhook
- `GET /api/health` - Health check
- `GET /api/admin/api-config` - Environment config
- `POST /api/admin/maintenance/whitelist` - Maintenance whitelist
- `GET /api/users/` - All users
- `GET /api/users/:userId/labels` - User labels
- `GET /api/users/:userId/topups` - User top-ups
- `GET /api/statistics/` - Order statistics

## Credentials
- **Admin Panel:** admin / ShipBot2026!Secure (HTTP Basic Auth)
- **Admin Telegram ID:** 7066790254

## Pending Issues
- P1: Hardcoded carrier_ids for ShipEngine fallback (needs user's IDs)
- P2: Incorrect weight/dimensions from templates
- P3: "SITKAGEAR" on UPS labels (ShipEngine account setting)
- P2: Hide FedEx in sandbox mode

## Future Tasks
- Refactor `telegram_conversation.py` (~3000 lines) into modules
- Refactor `AdminPanel.jsx` into components

## Update Log
- **2026-03-21**: Fixed webhook timeout (background processing), MongoDB DNS retry, health monitor service
- **2026-03-21**: Added WhiteLabelPlatform.cc button to bot menu (i18n)
- **2026-03-21**: Fixed rate pricing (include all cost components), negative profit protection
- **2026-03-13**: Fixed infinite recursion in safe_answer_query (2 files)
- **2026-03-13**: Fixed slow server startup (background bot preload)
