from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TelegramUser(BaseModel):
    """Telegram user model"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime = None
    last_interaction: datetime = None
    total_orders: int = 0