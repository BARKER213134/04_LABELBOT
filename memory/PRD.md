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
- Professional, official conversation flow
- Multi-step wizard for data entry with summary and edit options
- Button-driven UI (no text commands)
- "Skip" button for optional fields with random data generation

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + Tailwind CSS
- **Database:** MongoDB
- **Bot:** python-telegram-bot v22.5
- **API Integration:** ShipEngine API

## What's Been Implemented

### Completed (January 2026)
- [x] Full-stack application with FastAPI backend, React frontend, MongoDB
- [x] Web dashboard with pages: Dashboard, Orders List, Admin Panel, Create Order form
- [x] ShipEngine API integration (sandbox + production keys)
- [x] Telegram bot with ConversationHandler for multi-step wizard
- [x] Dual bot environment (test bot for sandbox, prod bot for production)
- [x] Environment switching via admin panel (changes both ShipEngine key and active bot)
- [x] Professional bot messages with official tone
- [x] Inline keyboard buttons instead of text commands
- [x] "Skip" button for phone numbers with random generation
- [x] "Back to Main Menu" button
- [x] **REVIEW SUMMARY with EDIT functionality** - users can review all entered data and edit any section before selecting carrier

### Edit Feature Details
The Telegram bot wizard now includes:
1. After entering package dimensions, users see a summary of all data
2. Summary shows: Sender info, Recipient info, Package details
3. Edit buttons for each section:
   - "Edit Sender" -> submenu: Address, City/State, Phone
   - "Edit Recipient" -> submenu: Address, City/State, Phone  
   - "Edit Package" -> submenu: Weight, Dimensions
4. "Continue" button to proceed to carrier selection
5. After editing any field, user returns to the summary screen

## API Endpoints
- `POST /api/telegram/webhook` - Webhook for both test and production Telegram bots
- `POST /api/orders/create` - Create shipping label
- `GET /api/orders/` - List all orders
- `GET /api/statistics/` - Dashboard statistics
- `GET /api/admin/environment` - Get current environment
- `POST /api/admin/environment` - Set environment (sandbox/production)

## Database Schema
- **orders**: Stores order documents with sender/recipient details, package info, carrier, tracking number, cost, status
- **settings**: Global app settings, primarily environment setting

## Key Files
- `/app/backend/services/telegram_conversation.py` - Bot conversation wizard logic
- `/app/backend/telegram_bot_app.py` - Bot application setup
- `/app/backend/routes/telegram.py` - Webhook endpoint
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

## Future Tasks / Backlog
None specified at this time. The primary functionality is complete.

## Testing Notes
- Test the bot by interacting with it on Telegram
- Use the test bot (sandbox environment) for testing
- The edit functionality can be tested by:
  1. Starting a label creation (/create or button)
  2. Filling out all required fields
  3. On the summary screen, clicking edit buttons
  4. Verifying data can be changed and returns to summary
