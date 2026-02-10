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
    "✨", "🌟", "📦", "🙏", "👏", "🤝", "⭐", "💯", "👍", "✅"
]

# Different message variations for variety
MESSAGE_VARIATIONS = [
    "поблагодари за заказ и пожелай успешной доставки",
    "выскажи благодарность и пожелай хорошего дня",
    "поблагодари за доверие и пожелай удачи",
    "выскажи признательность за выбор сервиса",
    "поблагодари и пожелай чтобы посылка дошла быстро",
    "выскажи благодарность и пожелай отличного настроения",
    "поблагодари за использование сервиса",
    "пожелай успешного получения посылки"
]


def get_random_emojis(count: int = 2) -> str:
    """Get random emojis for the message"""
    selected = random.sample(THANK_YOU_EMOJIS, min(count, len(THANK_YOU_EMOJIS)))
    return " ".join(selected)


async def generate_thank_you_message(carrier_name: str = "", tracking_number: str = "") -> str:
    """
    Generate a unique thank you message using AI
    """
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.warning("EMERGENT_LLM_KEY not found, using default message")
            return get_default_message()
        
        session_id = f"thank_you_{uuid.uuid4().hex[:8]}"
        
        variation = random.choice(MESSAGE_VARIATIONS)
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=(
                "Ты - профессиональный ассистент сервиса доставки. "
                "Пиши краткие, вежливые благодарственные сообщения в деловом стиле. "
                "Сообщение: 1-2 коротких предложения. "
                "Стиль: профессиональный, дружелюбный, без излишней поэзии и метафор. "
                "Язык: русский. "
                "НЕ используй: emoji, markdown, названия перевозчиков. "
                "НЕ пиши: стихи, сложные метафоры, слишком эмоциональный текст."
            )
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"Напиши короткое деловое благодарственное сообщение клиенту. Задача: {variation}. ID: {random.randint(100, 999)}"
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        if response:
            emojis = get_random_emojis(1)
            message = f"{emojis} {response.strip()}"
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
        "Благодарим за заказ! Желаем успешной доставки.",
        "Спасибо за доверие! Хорошего дня.",
        "Благодарим за использование сервиса! Удачи.",
        "Спасибо за заказ! Пусть посылка дойдёт быстро.",
        "Благодарим! Желаем отличного настроения.",
        "Спасибо, что выбрали нас! Успешной доставки.",
        "Благодарим за заказ! Всего доброго.",
        "Спасибо! Желаем удачного дня."
    ]
    emoji = random.choice(THANK_YOU_EMOJIS)
    return f"{emoji} {random.choice(messages)}"
