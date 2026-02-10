# 🧪 Telegram Bot Testing Instructions

## Быстрый тест

### Sandbox Bot (Test)

1. **Откройте Telegram**
2. **Найдите бота**: `@whitelabel_shipping_bot_test_bot`
3. **Нажмите "START" или отправьте**: `/start`

Вы должны получить приветственное сообщение:

```
🚀 Добро пожаловать в ShipBot!

Я помогу вам создать shipping labels для:
📦 USPS
✈️ FedEx
🚚 UPS

Доступные команды:
/create - Создать новый лейбл
/help - Показать помощь

💡 Для полного функционала используйте веб-дашборд:
https://shiplabel-bot.preview.emergentagent.com
```

### Тест команды /create

4. **Отправьте**: `/create`

Вы должны получить:

```
🚀 Создание нового лейбла

Давайте начнем! Я проведу вас через все шаги.

📍 Шаг 1 из 4: Адрес отправителя

Введите имя отправителя:
```

5. **Следуйте инструкциям бота** - вводите данные шаг за шагом

### Пример полного прохождения:

```
Вы: /create

Бот: Введите имя отправителя:
Вы: John Doe

Бот: Введите адрес отправителя (улица, дом):
Вы: 123 Main St

Бот: Введите город:
Вы: Austin

Бот: Введите штат (2 буквы, например: CA, NY, TX):
Вы: TX

Бот: Введите ZIP код:
Вы: 78701

Бот: Введите телефон отправителя (или напишите 'skip' чтобы пропустить):
Вы: skip

... (продолжайте для адреса получателя)

Вы: Jane Smith
Вы: 456 Oak Ave
Вы: San Francisco
Вы: CA
Вы: 94102
Вы: skip

... (параметры посылки)

Вы: 16
Вы: 12 8 6

... (выбор перевозчика - нажмите кнопку)

Бот покажет summary и кнопки [✅ Создать лейбл] [❌ Отменить]

Нажмите ✅ Создать лейбл

Бот: ✅ Лейбл создан успешно!
     📋 Tracking: 940555...
     💰 Стоимость: $12.59
```

## Проверка логов на сервере

Если что-то не работает, проверьте логи:

```bash
# Backend логи
tail -f /var/log/supervisor/backend.out.log | grep telegram

# Ошибки
tail -f /var/log/supervisor/backend.err.log
```

## Проверка статуса

```bash
# Статус сервисов
sudo supervisorctl status

# Перезапуск backend
sudo supervisorctl restart backend

# Проверка webhook
cd /app/backend
python3 setup_dual_webhooks.py
```

## Production Bot

Для тестирования production бота:

1. **Переключите environment в Admin Panel**:
   - Откройте: https://shiplabel-bot.preview.emergentagent.com/admin
   - Выберите: "Production (Live)"
   - Нажмите: "Save Changes"

2. **Откройте production бота**: `@whitelabel_shipping_bot`

3. **Отправьте**: `/start`

4. **Следуйте тем же шагам**

Production бот будет использовать production ShipEngine API ключи и создавать реальные лейблы.

## Troubleshooting

### Бот не отвечает на /start

**Проверьте:**
1. Webhook настроен:
```bash
cd /app/backend
python3 setup_dual_webhooks.py
```

2. Backend работает:
```bash
sudo supervisorctl status backend
```

3. Логи показывают обработку:
```bash
tail -20 /var/log/supervisor/backend.err.log
```

### Бот не отвечает на /create

**Проверьте:**
1. Application инициализирован (должно быть в логах):
```
telegram_bot_app - INFO - Sandbox bot initialized
```

2. ConversationHandler зарегистрирован

3. Перезапустите backend:
```bash
sudo supervisorctl restart backend
```

### Ошибка при создании лейбла

**Проверьте:**
1. ShipEngine API ключи в .env корректны
2. Current environment в Admin Panel
3. Адреса валидны (US адреса)
4. Логи ShipEngine API:
```bash
tail -50 /var/log/supervisor/backend.err.log | grep -i shipengine
```

## Команды для отладки

```bash
# Проверить текущий environment
curl https://shiplabel-bot.preview.emergentagent.com/api/admin/api-config

# Симулировать webhook
API_URL="https://shiplabel-bot.preview.emergentagent.com"
curl -X POST "$API_URL/api/telegram/webhook" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"message_id":1,"from":{"id":123,"first_name":"Test"},"chat":{"id":123,"type":"private"},"text":"/help","date":1705264800}}'

# Проверить orders в базе
mongosh
use shipbot_database
db.orders.find().sort({createdAt: -1}).limit(5).pretty()

# Проверить telegram users
db.telegram_users.find().pretty()
```

## Ожидаемое поведение

**После /start:**
- ✅ Приветственное сообщение
- ✅ Список команд
- ✅ Ссылка на dashboard

**После /create:**
- ✅ Пошаговая форма
- ✅ Валидация input
- ✅ Inline кнопки для выбора
- ✅ Summary перед созданием
- ✅ Success message с tracking

**После /help:**
- ✅ Список всех команд
- ✅ Краткая справка

**После /cancel (во время создания):**
- ✅ Отмена conversation
- ✅ Очистка session data

---

**Все готово для тестирования!** 🚀

Просто откройте Telegram и найдите:
- **Test:** @whitelabel_shipping_bot_test_bot
- **Production:** @whitelabel_shipping_bot
