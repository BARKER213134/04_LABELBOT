# ShipBot - Telegram Bot for Shipping Labels

## Original Problem Statement
Create a Telegram bot for generating shipping labels using the ShipEngine API. The bot should have:
- Beautiful and animated interface
- Scalable architecture
- Support for both sandbox and production ShipEngine environments
- Admin panel with environment toggle
- Support for USPS, FedEx, and UPS carriers
- Web dashboard for management
- Database for shipment history and users
- Complete user management system with balance
- Professional, official conversation flow
- Multi-step wizard for data entry with summary and edit options
- Button-driven UI (no text commands)
- "Skip" button for optional fields with random data generation
- Template management (up to 10 templates per user)
- Cryptocurrency payments via OxaPay
- AI-generated thank-you messages
- Secure label download (hide original URL)
- $10 markup on all ShipEngine prices
- Mass messaging/advertising to all users
- Admin ban/unban/delete users
- Maintenance mode with whitelist
- Admin notifications for new users, balance top-ups, label creations, errors
- i18n support (Russian/English)

## User Languages
- Russian - default
- English

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + Tailwind CSS
- **Database:** MongoDB Atlas
- **Bot:** python-telegram-bot v22.5
- **API Integrations:** ShipEngine, OxaPay, OpenAI (via emergentintegrations)

## What's Been Implemented

### Core Features (Completed)
- [x] Full-stack application with FastAPI backend, React frontend, MongoDB
- [x] Web dashboard with pages: Dashboard, Orders List, Admin Panel, Users, Broadcast
- [x] ShipEngine API integration (sandbox + production keys)
- [x] Telegram bot with ConversationHandler for multi-step wizard
- [x] Environment switching via admin panel
- [x] Professional bot messages in Russian AND English (i18n)
- [x] Inline keyboard buttons instead of text commands
- [x] "Skip" button for phone numbers with random generation
- [x] Review summary with edit functionality
- [x] Price fix: uses rate_id for accurate final pricing
- [x] Accurate profit calculation (user_paid - label_cost)
- [x] Bot state management with MongoDB ptb_conversations clearing
- [x] Maintenance mode with whitelist UI
- [x] User detail view with label and top-up history
- [x] Retry mechanism for ShipEngine API
- [x] Global error handler for Telegram bot
- [x] Carrier rate sorting by price

### User Management
- [x] Auto-create users on first bot interaction
- [x] Balance system per user
- [x] Balance management from admin panel
- [x] Balance notifications via Telegram
- [x] Balance, Templates, Refund, FAQ, Help menu buttons

### Template System
- [x] Full CRUD for templates (create, view, use, edit, delete)
- [x] Save up to 10 templates per user

### Payments
- [x] OxaPay cryptocurrency integration
- [x] Top-up balance flow
- [x] Payment status tracking

### Label Creation
- [x] $10 markup on all ShipEngine rates
- [x] Rate selection with carrier info
- [x] Balance check before label creation
- [x] Secure label download (PDF sent as Telegram document)
- [x] AI-generated thank-you messages

## API Endpoints
- `POST /api/telegram/webhook` - Webhook for Telegram bots
- `POST /api/oxapay/webhook` - Webhook for OxaPay payments
- `POST /api/orders/create` - Create shipping label
- `GET /api/orders/` - List all orders
- `GET /api/users/` - Get all users
- `POST /api/users/{telegram_id}/balance` - Update user balance
- `GET /api/admin/api-config` - Get current environment
- `POST /api/admin/api-config` - Set environment
- `GET /api/admin/maintenance` - Get maintenance mode status
- `POST /api/admin/maintenance/whitelist` - Manage whitelist
- `GET /api/users/:userId/labels` - User label history
- `GET /api/users/:userId/topups` - User top-up history

## Database Schema
- **orders**: Label info with sender/recipient, package, carrier, tracking, cost, status
- **users**: `{ telegram_id, username, first_name, balance, balance_history, total_orders, total_spent }`
- **templates**: `{ user_id, name, ship_from_*, ship_to_*, package_* }`
- **settings**: Global app settings (environment, maintenance)
- **oxapay_invoices**: Payment records
- **ptb_conversations**: Bot conversation state persistence
- **balance_logs**: Balance top-up history

## Key Files
- `/app/backend/telegram_bot_app.py` - Bot application setup, menu handlers
- `/app/backend/services/telegram_conversation.py` - Bot conversation wizard logic
- `/app/backend/services/shipengine_service.py` - ShipEngine API integration
- `/app/backend/routes/admin.py` - Admin API endpoints
- `/app/frontend/src/pages/AdminPanel.jsx` - Admin panel UI

## Environment Variables (backend/.env)
- MONGO_URL, DB_NAME
- SHIPENGINE_SANDBOX_KEY, SHIPENGINE_PRODUCTION_KEY
- TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_PROD
- WEBHOOK_URL, WEBHOOK_SECRET
- OXAPAY_MERCHANT_API_KEY
- EMERGENT_LLM_KEY
- ADMIN_PASSWORD

## Pending Issues
- **P1**: ShipEngine `/v1/carriers` API instability - need hardcoded carrier_ids as fallback (BLOCKED on user providing IDs)
- **P2**: Incorrect weight/dimensions when loading from a template
- **P3**: "SITKAGEAR" on UPS labels - user verification pending (likely ShipEngine account setting)
- **P2**: Hide FedEx in sandbox mode

## Future Tasks / Backlog
- **P1**: Refactor `telegram_conversation.py` (~3000 lines) into smaller modules
- **P2**: Refactor `AdminPanel.jsx` into smaller components
- **P2**: FedEx sandbox handling

## Credentials
- **Admin Panel:** admin / ShipBot2026!Secure (HTTP Basic Auth)
- **Admin Telegram ID:** 7066790254

## Update Log
- **2026-01-15**: Refactored template management flow
- **2026-02-18**: Core pricing fix, profit calculation, bot state management
- **2026-03-13**: Fixed critical infinite recursion bug in safe_answer_query (both telegram_bot_app.py and telegram_conversation.py)
