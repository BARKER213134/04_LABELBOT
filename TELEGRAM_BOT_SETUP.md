# Telegram Bot Configuration Guide

## Текущая конфигурация

### Тестовый бот (Sandbox)
- **Username**: @whitelabel_shipping_bot_test_bot
- **Bot ID**: 8560388458
- **Token**: `8560388458:AAHxT-vYpImOpy49lMnaXpSHDM-vtnOn6ZE`
- **Webhook**: https://shipping-label-bot.preview.emergentagent.com/api/telegram/webhook
- **Status**: ✅ Configured and Active

### Продакшн бот (Production)
- **Username**: [To be configured]
- **Token**: [Waiting for production bot token]
- **Webhook**: Will use same URL with production credentials

## Как добавить продакшн бота

### 1. Создайте продакшн бота через @BotFather

```
/newbot
# Введите имя бота
# Введите username бота (должен заканчиваться на _bot)
# Получите токен
```

### 2. Обновите конфигурацию

Создайте отдельную конфигурацию для production в `/app/backend/.env`:

```env
# Добавьте новые переменные для production бота
TELEGRAM_BOT_TOKEN_PROD="ваш_продакшн_токен_здесь"
```

### 3. Обновите код для поддержки двух ботов

Нужно модифицировать `services/telegram_service.py`:

```python
class TelegramService:
    def __init__(self, environment='sandbox'):
        settings = get_settings()
        # Выбираем токен в зависимости от окружения
        if environment == 'production':
            token = settings.telegram_bot_token_prod
        else:
            token = settings.telegram_bot_token
        self.bot = Bot(token=token)
```

### 4. Настройте webhook для продакшн бота

```bash
cd /app/backend
# Добавьте переменную окружения
export TELEGRAM_BOT_TOKEN="продакшн_токен"
python3 setup_telegram_webhook.py
```

## Тестирование бота

### 1. Проверить статус webhook

```bash
cd /app/backend
python3 setup_telegram_webhook.py
```

### 2. Отправить тестовое сообщение

1. Откройте Telegram
2. Найдите @whitelabel_shipping_bot_test_bot
3. Отправьте `/start`
4. Проверьте логи:

```bash
tail -f /var/log/supervisor/backend.out.log
```

### 3. Проверить получение обновлений

```bash
cd /app/backend
python3 test_telegram_bot.py
```

## Доступные команды бота

### /start
Приветственное сообщение с инструкциями

### /create
Запускает процесс создания лейбла:
1. Выбор перевозчика (USPS, FedEx, UPS)
2. Пользователь получает уведомление
3. Полное создание лейбла через веб-дашборд

### /help
Показывает справку по командам

## Webhook vs Polling

**Текущий режим**: Webhook (рекомендуется для production)

**Преимущества webhook:**
- ✅ Мгновенная доставка сообщений
- ✅ Меньше нагрузки на сервер
- ✅ Масштабируемость

**Если нужно переключиться на polling** (только для development):

```python
# В telegram_service.py добавьте метод
async def start_polling(self):
    from telegram.ext import Application
    app = Application.builder().token(self.bot_token).build()
    # Добавьте handlers
    await app.run_polling()
```

## Troubleshooting

### Webhook не работает

```bash
# Проверьте webhook
cd /app/backend
python3 -c "
from telegram import Bot
import asyncio
import os
from dotenv import load_dotenv
load_dotenv('.env')
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
info = asyncio.run(bot.get_webhook_info())
print(f'URL: {info.url}')
print(f'Pending: {info.pending_update_count}')
print(f'Last error: {info.last_error_message}')
"
```

### Бот не отвечает

1. Проверьте логи backend:
```bash
tail -f /var/log/supervisor/backend.out.log
```

2. Проверьте, что backend запущен:
```bash
sudo supervisorctl status backend
```

3. Перезапустите backend:
```bash
sudo supervisorctl restart backend
```

### Удалить webhook (для тестирования)

```bash
cd /app/backend
python3 -c "
from telegram import Bot
import asyncio
import os
from dotenv import load_dotenv
load_dotenv('.env')
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
asyncio.run(bot.delete_webhook(drop_pending_updates=True))
print('Webhook deleted')
"
```

## Мониторинг

### Проверить активность бота

```bash
# В логах backend ищите:
grep "telegram" /var/log/supervisor/backend.out.log | tail -20
```

### Проверить количество пользователей

```bash
# MongoDB query
mongosh
use shipbot_database
db.telegram_users.countDocuments()
db.telegram_users.find().pretty()
```

## Безопасность

1. **Никогда не коммитьте токены** в git
2. **Используйте WEBHOOK_SECRET** для валидации запросов
3. **Ограничьте доступ к webhook endpoint** (уже реализовано)
4. **Регулярно ротируйте токены** через @BotFather

## Следующие шаги

- [ ] Добавить полный wizard создания лейбла в Telegram
- [ ] Добавить команду /orders для просмотра заказов
- [ ] Добавить команду /track для отслеживания посылки
- [ ] Добавить inline keyboards для выбора опций
- [ ] Настроить продакшн бота
- [ ] Добавить rate limiting для защиты от спама
