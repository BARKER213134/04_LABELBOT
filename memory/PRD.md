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

## User Languages
- Russian (Русский) - default
- English - added December 2025

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + Tailwind CSS
- **Database:** MongoDB
- **Bot:** python-telegram-bot v22.5
- **API Integrations:** ShipEngine, OxaPay, OpenAI (via emergentintegrations)

## What's Been Implemented

### Core Features (Completed)
- [x] Full-stack application with FastAPI backend, React frontend, MongoDB
- [x] Web dashboard with pages: Dashboard, Orders List, Admin Panel, Users
- [x] ShipEngine API integration (sandbox + production keys)
- [x] Telegram bot with ConversationHandler for multi-step wizard
- [x] Dual bot environment (test bot for sandbox, prod bot for production)
- [x] Environment switching via admin panel
- [x] Professional bot messages in Russian AND English (i18n)
- [x] Inline keyboard buttons instead of text commands
- [x] "Skip" button for phone numbers with random generation
- [x] "Back to Main Menu" button (works like /start command)
- [x] Review summary with edit functionality
- [x] Multi-language support (Russian/English) - December 2025

### User Management
- [x] Auto-create users on first bot interaction
- [x] Balance system per user
- [x] Balance management from admin panel
- [x] Balance notifications via Telegram
- [x] Balance, Templates, Refund, FAQ, Help menu buttons

### Template System
- [x] Create templates from label creation flow
- [x] Save up to 10 templates per user
- [x] View template details
- [x] Use template to create new label
- [x] Edit templates
- [x] Delete templates
- [x] **NEW: Conversational template flow** - each action sends a new message instead of editing one

### Payments
- [x] OxaPay cryptocurrency integration
- [x] Top-up balance flow
- [x] Payment status tracking
- [x] Insufficient balance handling with top-up prompt

### Label Creation
- [x] $10 markup on all ShipEngine rates
- [x] Rate selection with carrier info
- [x] Balance check before label creation
- [x] Secure label download (PDF sent as Telegram document, hides URL)
- [x] AI-generated thank-you messages in Russian after successful label creation

## API Endpoints
- `POST /api/telegram/webhook` - Webhook for Telegram bots
- `POST /api/oxapay/webhook` - Webhook for OxaPay payments
- `POST /api/orders/create` - Create shipping label
- `GET /api/orders/` - List all orders
- `GET /api/users/` - Get all users
- `POST /api/users/{telegram_id}/balance` - Update user balance
- `GET /api/admin/environment` - Get current environment
- `POST /api/admin/environment` - Set environment

## Database Schema
- **orders**: Stores order documents with sender/recipient details, package info, carrier, tracking number, cost, status
- **users**: `{ telegram_id, username, first_name, balance, balance_history, total_orders, total_spent }`
- **templates**: `{ user_id, name, ship_from_*, ship_to_*, package_* }`
- **settings**: Global app settings (environment)
- **oxapay_invoices**: Payment invoice records

## Key Files
- `/app/backend/telegram_bot_app.py` - Bot application setup, menu handlers, template handlers
- `/app/backend/services/telegram_conversation.py` - Bot conversation wizard logic
- `/app/backend/services/oxapay_service.py` - OxaPay integration
- `/app/backend/services/ai_messages.py` - AI message generation
- `/app/backend/routes/oxapay.py` - OxaPay webhook
- `/app/backend/config.py` - Configuration management

## Environment Variables (backend/.env)
- MONGO_URL
- DB_NAME
- SHIPENGINE_SANDBOX_KEY
- SHIPENGINE_PRODUCTION_KEY
- TELEGRAM_BOT_TOKEN (sandbox/test)
- TELEGRAM_BOT_TOKEN_PROD (production)
- WEBHOOK_URL
- WEBHOOK_SECRET
- OXAPAY_MERCHANT_API_KEY
- EMERGENT_LLM_KEY

## Future Tasks / Backlog

### P1 - Code Refactoring
- [ ] Break down `telegram_bot_app.py` and `telegram_conversation.py` into smaller modules
- [ ] Create `/app/backend/bot_handlers/` directory structure:
  - `templates.py` - Template management handlers
  - `balance.py` - Balance and payment handlers
  - `labels.py` - Label creation handlers
  - `menu.py` - Main menu handlers

### P2 - FedEx Sandbox
- [ ] Hide FedEx as carrier option in sandbox mode (it's unstable)

## Known Issues
- FedEx is unstable in ShipEngine sandbox environment (external limitation)
- UPS sometimes returns errors in sandbox (external limitation)
- USPS is the most reliable carrier for testing

## Update Log
- **2026-01-15**: Refactored template management flow to use new messages for each action (better UX)
- **2026-01-15**: Updated webhook to current URL
