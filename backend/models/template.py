from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class Template(BaseModel):
    """Template model for saving shipment data"""
    template_id: str
    user_telegram_id: str
    name: str = Field(max_length=50, description="Template name")
    
    # Sender data
    ship_from_name: Optional[str] = None
    ship_from_address: Optional[str] = None
    ship_from_city: Optional[str] = None
    ship_from_state: Optional[str] = None
    ship_from_zip: Optional[str] = None
    ship_from_phone: Optional[str] = None
    
    # Recipient data
    ship_to_name: Optional[str] = None
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_zip: Optional[str] = None
    ship_to_phone: Optional[str] = None
    
    # Package data
    package_weight: Optional[float] = None
    package_length: Optional[float] = None
    package_width: Optional[float] = None
    package_height: Optional[float] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = Field(default=0, description="How many times template was used")


class TemplateCreate(BaseModel):
    """Model for creating a template"""
    name: str = Field(max_length=50)
    user_telegram_id: str


class TemplateResponse(BaseModel):
    """Template response model"""
    template_id: str
    name: str
    ship_from_name: Optional[str] = None
    ship_from_city: Optional[str] = None
    ship_to_name: Optional[str] = None
    ship_to_city: Optional[str] = None
    use_count: int
    created_at: datetime
