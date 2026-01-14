# ShipBot - Shipping Label Management System

Telegram бот и веб-дашборд для создания shipping labels через ShipEngine API (USPS, FedEx, UPS).

## 🚀 Функционал

### Веб-Дашборд
- 📊 **Dashboard** - статистика и аналитика заказов
- 📦 **Orders** - список всех заказов с фильтрацией
- ➕ **Create Label** - многошаговая форма создания лейбла
- ⚙️ **Admin Panel** - переключение между test/production API ключами

### Telegram Бот
- Пошаговое создание лейблов
- Выбор перевозчика (USPS, FedEx, UPS)
- Уведомления о создании лейблов
- Интеграция с веб-дашбордом

## 📋 Требования

- Python 3.11+
- Node.js 16+
- MongoDB
- Telegram Bot Token
- ShipEngine API Keys (sandbox & production)

## 🔧 Настройка

### 1. Backend Configuration

Обновите `/app/backend/.env`:

```env
# MongoDB
MONGO_URL="mongodb://localhost:27017"
DB_NAME="shipbot_database"

# ShipEngine API Keys
SHIPENGINE_SANDBOX_KEY="TEST_your_sandbox_key_here"
SHIPENGINE_PRODUCTION_KEY="your_production_key_here"
ENVIRONMENT="sandbox"

# Telegram Bot
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
WEBHOOK_SECRET="your_webhook_secret_here"
WEBHOOK_URL="https://your-domain.com/api/telegram/webhook"

# CORS
CORS_ORIGINS="*"
```

### 2. Получение API ключей

#### ShipEngine
1. Зарегистрируйтесь на [ShipEngine](https://www.shipengine.com/)
2. Получите Sandbox API key (начинается с `TEST_`)
3. Для production получите Production API key
4. Добавьте ключи в `.env`

#### Telegram Bot
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте бота: `/newbot`
3. Следуйте инструкциям и получите Bot Token
4. Добавьте токен в `.env`

### 3. Установка зависимостей

```bash
# Backend
cd /app/backend
pip install -r requirements.txt

# Frontend
cd /app/frontend
yarn install
```

### 4. Запуск

```bash
# Restart services
sudo supervisorctl restart backend frontend
```

## 🎯 Использование

### Веб-Дашборд

1. Откройте `https://your-domain.com`
2. Перейдите в **Admin Panel** для настройки API environment
3. Создайте новый лейбл через **Create Label**
4. Просмотрите все заказы в **Orders**

### Telegram Бот

1. Найдите вашего бота в Telegram
2. Отправьте `/start` для начала
3. Используйте `/create` для создания лейбла
4. Выберите перевозчика
5. Дополните информацию через веб-дашборд

### API Endpoints

- `POST /api/orders/create` - создать заказ
- `GET /api/orders` - список заказов
- `GET /api/orders/{id}` - получить заказ
- `GET /api/admin/api-config` - получить конфигурацию
- `POST /api/admin/api-config` - обновить конфигурацию
- `POST /api/telegram/webhook` - webhook для Telegram
- `GET /api/statistics` - статистика

## 🎨 Дизайн

Приложение использует **Neo-Industrial Logistics** тему:
- Dark mode first
- Outfit для заголовков
- DM Sans для текста
- JetBrains Mono для данных (tracking numbers)
- International Orange (#F97316) как primary цвет
- Sharp edges и minimal borders

## 📁 Структура проекта

```
/app
├── backend/
│   ├── models/          # Pydantic модели
│   ├── routes/          # API endpoints
│   ├── services/        # ShipEngine, Telegram сервисы
│   ├── config.py        # Конфигурация
│   ├── database.py      # MongoDB подключение
│   └── server.py        # FastAPI приложение
├── frontend/
│   ├── src/
│   │   ├── components/  # React компоненты
│   │   ├── services/    # API клиент
│   │   ├── App.js
│   │   └── App.css
│   └── package.json
└── design_guidelines.json
```

## 🗄️ База данных

MongoDB коллекции:
- `orders` - все заказы (каждый лейбл = отдельный ордер)
- `api_config` - настройки API environment
- `telegram_users` - Telegram пользователи

## 🔐 Безопасность

- API ключи хранятся в environment variables
- Webhook защищен секретом
- CORS настроен для production
- MongoDB без hardcoded credentials

## 🐛 Troubleshooting

### Backend не запускается
```bash
# Проверьте логи
tail -f /var/log/supervisor/backend.err.log

# Проверьте зависимости
cd /app/backend && pip install -r requirements.txt
```

### Frontend ошибки
```bash
# Проверьте логи
tail -f /var/log/supervisor/frontend.err.log

# Переустановите зависимости
cd /app/frontend && yarn install
```

### MongoDB подключение
```bash
# Проверьте статус
sudo supervisorctl status mongodb

# Проверьте connection string в .env
```

## 📝 Следующие шаги

1. ✅ Настроить ShipEngine API ключи
2. ✅ Создать Telegram бота
3. ✅ Настроить webhook для Telegram
4. 🔄 Протестировать создание лейблов в sandbox
5. 🚀 Перейти на production после тестирования

## 🤝 Поддержка

Для вопросов и поддержки:
- Проверьте логи: `/var/log/supervisor/`
- Проверьте настройки в Admin Panel
- Убедитесь что API ключи корректны
