from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB
    mongo_url: str
    db_name: str
    
    # ShipEngine
    shipengine_sandbox_key: str = "TEST_demo"
    shipengine_production_key: str = "prod_demo"
    environment: str = "sandbox"
    
    # Telegram
    telegram_bot_token: str = "demo_token"
    telegram_bot_token_prod: str = "demo_token_prod"
    webhook_secret: str = "demo_secret"
    webhook_url: str = "https://demo.com"
    
    # OxaPay
    oxapay_merchant_api_key: str = ""
    
    # AI/LLM
    emergent_llm_key: str = ""
    
    # CORS
    cors_origins: str = "*"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def shipengine_api_key(self) -> str:
        """Return current environment's API key"""
        if self.environment == "sandbox":
            return self.shipengine_sandbox_key
        return self.shipengine_production_key
    
    @property
    def shipengine_api_url(self) -> str:
        return "https://api.shipengine.com"

@lru_cache
def get_settings() -> Settings:
    return Settings()