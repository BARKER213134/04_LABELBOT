from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.settings import APIKeyConfig
from config import get_settings, Settings
from database import get_database
from services.security import verify_admin, api_limiter, check_rate_limit, get_client_ip
from datetime import datetime
import logging

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/api-config")
async def get_api_config(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)  # Требует аутентификации
):
    """Retrieve current API key configuration (protected)"""
    # Rate limiting
    check_rate_limit(get_client_ip(request), api_limiter)
    
    config = await db.api_config.find_one({"_id": "api_config"})
    
    if not config:
        return {
            "environment": settings.environment,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    return {
        "environment": config.get("environment", "sandbox"),
        "updated_at": config.get("updated_at", datetime.utcnow().isoformat()),
        "updated_by": config.get("updated_by", "admin")
    }


@router.post("/api-config")
async def update_api_config(
    request: Request,
    new_config: APIKeyConfig,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)  # Требует аутентификации
):
    """Update API key environment configuration (protected)"""
    # Rate limiting
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        config_data = {
            "_id": "api_config",
            "environment": new_config.environment,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": admin  # Используем имя авторизованного пользователя
        }
        
        await db.api_config.update_one(
            {"_id": "api_config"},
            {"$set": config_data},
            upsert=True
        )
        
        logger.info(f"[ADMIN] Config updated to {new_config.environment} by {admin}")
        
        # Clear environment cache
        from routes.telegram import clear_environment_cache
        await clear_environment_cache()
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "environment": new_config.environment
        }
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )
