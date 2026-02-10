"""
AI Thank You Message Generator
Generates unique business-style thank you messages after label creation
"""
import os
import logging
import uuid
import random
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

# Fun emojis for thank you messages
THANK_YOU_EMOJIS = [
    "🎉", "✨", "🌟", "💫", "🚀", "📦", "🎁", "💝", "🙏", "👏",
    "🤝", "💪", "🔥", "⭐", "🌈", "☀️", "🎊", "💯", "👍", "😊",
    "🤩", "🥳", "💐", "🌺", "🍀", "🎯", "💎", "🏆", "🎈", "🌻"
]

# Different message styles/themes for variety
MESSAGE_STYLES = [
    "философский (с мудрым изречением о пути посылки)",
    "поэтический (с красивой метафорой)",
    "тёплый и домашний (как от доброй бабушки)",
    "энергичный и мотивирующий (заряжающий энтузиазмом)",
    "юмористический (с лёгкой шуткой про доставку)",
    "романтический (о путешествии посылки)",
    "вдохновляющий (про новые возможности)",
    "благодарный (с акцентом на ценность клиента)",
    "сезонный (упоминая погоду/время года)",
    "дружеский (как от старого друга)"
]

# Random phrases to add variety
RANDOM_THEMES = [
    "упомяни что посылка несёт частичку заботы",
    "пожелай чтобы посылка доехала со скоростью ветра",
    "расскажи что каждая посылка - это маленькое чудо",
    "сравни отправку посылки с запуском кораблика в плавание",
    "пожелай чтобы день был таким же успешным как отправка",
    "упомяни что за посылкой следят добрые глаза",
    "пожелай получателю улыбку при вскрытии",
    "расскажи что посылки любят путешествовать",
    "пожелай лёгкой дороги и тёплой встречи",
    "сравни посылку с посланием счастья"
]


def get_random_emojis(count: int = 3) -> str:
    """Get random emojis for the message"""
    selected = random.sample(THANK_YOU_EMOJIS, min(count, len(THANK_YOU_EMOJIS)))
    return " ".join(selected)


async def generate_thank_you_message(carrier_name: str = "", tracking_number: str = "") -> str:
    """
    Generate a unique thank you message using AI
    
    Args:
        carrier_name: Name of the shipping carrier (not used in message)
        tracking_number: Tracking number for the shipment (not used in message)
    
    Returns:
        Generated thank you message with emojis
    """
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.warning("EMERGENT_LLM_KEY not found, using default message")
            return get_default_message()
        
        # Create unique session for each message
        session_id = f"thank_you_{uuid.uuid4().hex[:8]}"
        
        # Pick random style and theme for this message
        style = random.choice(MESSAGE_STYLES)
        theme = random.choice(RANDOM_THEMES)
        
        # Random additional instructions
        extras = random.choice([
            "Используй необычное сравнение.",
            "Добавь пожелание удачи.",
            "Упомяни что-то про хорошее настроение.",
            "Закончи добрым пожеланием на день.",
            "Будь особенно тёплым и душевным.",
            "Добавь немного лёгкого юмора.",
            "Используй красивую метафору.",
            "Пожелай чего-то неожиданного и приятного."
        ])
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=(
                "Ты - креативный и душевный автор благодарственных сообщений для сервиса доставки. "
                "Каждое сообщение должно быть УНИКАЛЬНЫМ и отличаться от предыдущих! "
                "Используй разные формулировки, структуры предложений, пожелания. "
                "НИКОГДА не начинай одинаково. Избегай шаблонных фраз. "
                "Язык: только русский, БЕЗ английских слов. "
                "НЕ упоминай название службы доставки или перевозчика. "
                "Сообщение: 2-3 предложения, живое и запоминающееся. "
                "НЕ используй emoji и markdown - только текст."
            )
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = (
            f"Напиши уникальное благодарственное сообщение клиенту за отправку посылки.\n"
            f"Стиль сообщения: {style}\n"
            f"Идея для сообщения: {theme}\n"
            f"Дополнительно: {extras}\n"
            f"Случайное число для уникальности: {random.randint(1000, 9999)}"
        )
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        if response:
            # Add random emojis
            emojis_start = get_random_emojis(2)
            emojis_end = get_random_emojis(2)
            message = f"{emojis_start} {response.strip()} {emojis_end}"
            logger.info(f"Generated thank you message: {message[:50]}...")
            return message
        else:
            return get_default_message()
            
    except Exception as e:
        logger.error(f"Error generating thank you message: {e}")
        return get_default_message()


def get_default_message() -> str:
    """Return default thank you message if AI fails"""
    messages = [
        "Спасибо, что доверяете нам свои посылки! Пусть этот день будет наполнен радостью и приятными сюрпризами!",
        "Благодарим от всего сердца! Желаем вам солнечного настроения и только хороших новостей!",
        "Ваша посылка уже в пути к счастливому получателю! Пусть удача сопутствует вам во всём!",
        "Спасибо за доверие! Пусть каждый ваш день начинается с улыбки и заканчивается успехом!",
        "Вы прекрасны! Желаем вам лёгкости в делах и тепла в душе. Отличного дня!",
        "Посылка отправилась в своё маленькое путешествие! Пусть она принесёт радость получателю!",
        "Каждая посылка - это частичка заботы. Спасибо, что делитесь теплом!",
        "Ваша посылка уже мчится навстречу приключениям! Хорошего вам дня!",
        "Отправлено с любовью - доставлено с заботой! Благодарим вас!",
        "Пусть эта посылка станет приятным сюрпризом! Спасибо, что вы с нами!"
    ]
    emojis_start = get_random_emojis(2)
    emojis_end = get_random_emojis(2)
    return f"{emojis_start} {random.choice(messages)} {emojis_end}"
