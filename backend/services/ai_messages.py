"""
AI Thank You Message Generator
Generates unique business-style thank you messages after label creation
"""
import os
import logging
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


async def generate_thank_you_message(carrier_name: str = "", tracking_number: str = "") -> str:
    """
    Generate a unique thank you message using AI
    
    Args:
        carrier_name: Name of the shipping carrier
        tracking_number: Tracking number for the shipment
    
    Returns:
        Generated thank you message
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
                "Ты - вежливый бизнес-ассистент сервиса доставки White Label Shipping. "
                "Твоя задача - написать короткое благодарственное сообщение клиенту после создания shipping label. "
                "Стиль: деловой, но дружелюбный. Язык: русский. "
                "Сообщение должно быть 1-2 предложения + пожелание хорошего дня/удачи. "
                "Каждый раз генерируй уникальное сообщение, используй разные формулировки. "
                "НЕ используй emoji. НЕ используй markdown форматирование."
            )
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"Напиши благодарственное сообщение клиенту за создание лейбла через {carrier_name}."
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        if response:
            logger.info(f"Generated thank you message: {response[:50]}...")
            return response.strip()
        else:
            return get_default_message()
            
    except Exception as e:
        logger.error(f"Error generating thank you message: {e}")
        return get_default_message()


def get_default_message() -> str:
    """Return default thank you message if AI fails"""
    import random
    messages = [
        "Благодарим вас за использование нашего сервиса! Желаем вам отличного дня и успешной доставки.",
        "Спасибо за ваш заказ! Надеемся, что доставка пройдёт быстро и без проблем. Хорошего дня!",
        "Благодарим за доверие к нашему сервису! Пусть ваша посылка доберётся вовремя. Удачи!",
        "Спасибо, что выбрали нас! Желаем вам продуктивного дня и быстрой доставки.",
        "Благодарим вас за заказ! Пусть этот день принесёт вам только хорошие новости. До встречи!"
    ]
    return random.choice(messages)
