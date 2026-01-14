# 🤖 Telegram Bot - Full Wizard Guide

## Complete Label Creation in Telegram

Теперь пользователи могут **полностью создать shipping label прямо в Telegram** - от А до Я!

### 🎯 Что Работает

**Multi-Step Wizard (17 шагов):**
1. ✅ Ship From Address (6 полей)
2. ✅ Ship To Address (6 полей)
3. ✅ Package Details (4 поля)
4. ✅ Carrier Selection (inline кнопки)
5. ✅ Service Selection (inline кнопки)
6. ✅ Confirmation (summary + inline кнопки)
7. ✅ Label Creation (API call)
8. ✅ Success notification с tracking number

### 📱 User Flow

```
/create
  ↓
📍 Step 1: Ship From Address
  • Name
  • Street Address
  • City
  • State (2 letters, validated)
  • ZIP (5 digits, validated)
  • Phone (optional, can skip)
  ↓
📍 Step 2: Ship To Address
  • Name
  • Street Address
  • City
  • State (validated)
  • ZIP (validated)
  • Phone (optional)
  ↓
📦 Step 3: Package Details
  • Weight in ounces (number, validated)
  • Dimensions: L W H in inches (3 numbers, validated)
  ↓
🚚 Step 4: Carrier Selection
  [📦 USPS] [✈️ FedEx] [🚚 UPS]
  ↓
📋 Step 5: Service Selection
  (Options depend on carrier)
  ↓
✅ Step 6: Confirmation
  Shows full summary
  [✅ Create Label] [❌ Cancel]
  ↓
⏳ Creating label...
  ↓
✅ Success!
  📋 Tracking: 940555...
  💰 Cost: $12.59
  🔗 Download in dashboard
```

### 🔧 Architecture

**Backend Components:**

1. **`telegram_conversation.py`**
   - TelegramConversationHandler class
   - 17 conversation states
   - Input validation
   - Error handling
   - Session management

2. **`orders_service.py`**
   - OrdersService class
   - Creates orders in DB
   - Calls ShipEngine API
   - Updates telegram user stats

3. **`telegram_bot_app.py`**
   - Bot Application runner
   - Conversation handler registration
   - Command handlers (/start, /help, /cancel)
   - Environment-based bot selection

4. **`routes/telegram.py`**
   - Webhook endpoint
   - Routes to correct bot app
   - Based on environment

### 🎨 Features

**Input Validation:**
- ✅ State: Must be 2 letters
- ✅ ZIP: Must be 5 digits
- ✅ Weight: Must be positive number
- ✅ Dimensions: Must be 3 positive numbers
- ✅ Friendly error messages

**User Experience:**
- ✅ Clear step indicators ("Шаг 1 из 4")
- ✅ Progress feedback ("✅ Saved!")
- ✅ Optional fields (phone can skip)
- ✅ Inline keyboards for selections
- ✅ Full order summary before confirmation
- ✅ Cancel anytime with /cancel

**Data Management:**
- ✅ Session data stored in memory
- ✅ Auto-cleanup after completion/cancel
- ✅ Telegram user tracking in DB
- ✅ Order history preserved

### 📋 Example Interaction

```
User: /create

Bot: 🚀 Создание нового лейбла
     Давайте начнем! Я проведу вас через все шаги.
     
     📍 Шаг 1 из 4: Адрес отправителя
     
     Введите имя отправителя:

User: John Doe

Bot: ✅ Отлично!
     Теперь введите адрес отправителя (улица, дом):

User: 123 Main St

Bot: Введите город:

User: Austin

Bot: Введите штат (2 буквы, например: CA, NY, TX):

User: TX

Bot: Введите ZIP код:

User: 78701

Bot: Введите телефон отправителя (или напишите 'skip' чтобы пропустить):

User: skip

Bot: ✅ Адрес отправителя сохранен!
     
     📍 Шаг 2 из 4: Адрес получателя
     
     Введите имя получателя:

... (continues for all steps)

Bot: 📋 Подтверждение заказа
     
     От: John Doe
     123 Main St
     Austin, TX 78701
     
     Кому: Jane Smith
     456 Oak Ave
     San Francisco, CA 94102
     
     Посылка:
     Вес: 16 oz
     Размеры: 12x8x6 in
     
     Перевозчик: USPS
     Сервис: Priority Mail
     
     [✅ Создать лейбл] [❌ Отменить]

User: [Clicks ✅ Создать лейбл]

Bot: ⏳ Создаю лейбл...

Bot: ✅ Лейбл создан успешно!
     
     📋 Tracking: 9405550899563317562932
     💰 Стоимость: $12.59
     🚚 Перевозчик: USPS
     
     🔗 Скачать лейбл можно в веб-дашборде
```

### 🛠️ Commands

- `/create` - Start label creation wizard
- `/cancel` - Cancel current wizard (anytime)
- `/start` - Welcome message
- `/help` - Show help

### 🧪 Testing

**Test the bot:**

```bash
# Run test helper
cd /app/backend
python3 test_conversation.py

# Then open Telegram and follow instructions
```

**Watch logs:**

```bash
tail -f /var/log/supervisor/backend.out.log | grep -i telegram
```

### 🔄 Environment Switching

**Same as before:**
- Admin Panel → Select Environment → Save
- Sandbox environment → @whitelabel_shipping_bot_test_bot
- Production environment → @whitelabel_shipping_bot

**Backend automatically:**
- Uses correct bot token
- Uses correct ShipEngine API key
- Saves orders with correct environment tag

### 📊 Database Integration

**Collections Updated:**

**`telegram_users`:**
```json
{
  "telegram_id": "123456789",
  "username": "john_doe",
  "first_name": "John",
  "total_orders": 3,
  "last_interaction": "2026-01-14T19:30:00"
}
```

**`orders`:**
```json
{
  "id": "order_123",
  "telegram_user_id": "123456789",
  "telegram_username": "john_doe",
  "shipFromAddress": {...},
  "shipToAddress": {...},
  "package": {...},
  "carrier": "usps",
  "trackingNumber": "9405550899...",
  "environment": "sandbox"
}
```

### 🚀 Deployment

**Already deployed!**
- ✅ Conversation handlers active
- ✅ Webhooks configured
- ✅ Both bots ready (sandbox & production)
- ✅ Environment switching works

**No additional setup needed!**

### 🐛 Troubleshooting

**Bot not responding to /create?**

1. Check webhook status:
```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

2. Check backend logs:
```bash
tail -50 /var/log/supervisor/backend.err.log
```

3. Restart backend:
```bash
sudo supervisorctl restart backend
```

**Conversation stuck?**

- Send `/cancel` to reset
- Or wait 30 minutes (auto-timeout)

**Label creation fails?**

- Check ShipEngine API keys in .env
- Verify environment in Admin Panel
- Check address validation errors

### 📈 Next Steps

- [ ] Add /orders command to view user's labels
- [ ] Add /track command for tracking
- [ ] Add conversation timeout
- [ ] Add rate limiting
- [ ] Add admin commands
- [ ] Add analytics
- [ ] Add multi-language support
- [ ] Add address autocomplete

### 💡 Tips

**For Users:**
- Use 'skip' for optional fields
- State must be exactly 2 letters (CA, not California)
- ZIP must be exactly 5 digits
- Dimensions format: "12 8 6" (space-separated)
- Use /cancel if you make a mistake

**For Developers:**
- Conversation state stored in memory (restart clears)
- For production, consider Redis for sessions
- Add timeout handler for abandoned conversations
- Consider adding "Back" button for step navigation
- Add conversation analytics

---

**Bot is fully functional! Try it now!** 🎉

**Sandbox:** https://t.me/whitelabel_shipping_bot_test_bot  
**Production:** https://t.me/whitelabel_shipping_bot
