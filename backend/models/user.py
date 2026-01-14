from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class User(BaseModel):
    """User model for Telegram bot users"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    balance: float = Field(default=0.0, description="User balance in USD")
    total_orders: int = Field(default=0, description="Total number of orders")
    total_spent: float = Field(default=0.0, description="Total amount spent on labels")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TelegramUser(BaseModel):
    """Telegram user model (legacy compatibility)"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime = None
    last_interaction: datetime = None
    total_orders: int = 0


class UserCreate(BaseModel):
    """Model for creating a new user"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserBalanceUpdate(BaseModel):
    """Model for updating user balance"""
    telegram_id: str
    amount: float = Field(description="Amount to add (positive) or subtract (negative)")
    reason: Optional[str] = Field(default=None, description="Reason for balance change")


class UserResponse(BaseModel):
    """User response model (without sensitive data)"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    balance: float
    total_orders: int
    total_spent: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
