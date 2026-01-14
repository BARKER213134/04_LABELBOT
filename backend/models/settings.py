from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class APIKeyConfig(BaseModel):
    """Configuration for API key storage"""
    environment: Literal["sandbox", "production"] = "sandbox"
    updated_at: datetime = None
    updated_by: str = "admin"