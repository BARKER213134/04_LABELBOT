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
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=(
                "Ты - душевный и позитивный ассистент сервиса доставки. "
                "Твоя задача - написать тёплое, душевное благодарственное сообщение клиенту. "
                "Сообщение должно поднимать настроение и заряжать позитивом! "
                "Язык: только русский, БЕЗ английских слов. "
                "НЕ упоминай название службы доставки или перевозчика. "
                "Сообщение должно быть 2-3 предложения с пожеланием хорошего дня/удачи/настроения. "
                "Будь креативным, используй разные формулировки каждый раз. "
                "Можно использовать метафоры, добрые пожелания, позитивные фразы. "
                "НЕ используй emoji - они будут добавлены автоматически. НЕ используй markdown."
            )
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = "Напиши душевное благодарственное сообщение клиенту за оформление посылки. Подними ему настроение!"
        
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
        "Вы прекрасны! Желаем вам лёгкости в делах и тепла в душе. Отличного дня!"
    ]
    emojis_start = get_random_emojis(2)
    emojis_end = get_random_emojis(2)
    return f"{emojis_start} {random.choice(messages)} {emojis_end}"
