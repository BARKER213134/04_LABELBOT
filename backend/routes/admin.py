from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.settings import APIKeyConfig
from config import get_settings, Settings
from database import get_database
from services.security import verify_admin, api_limiter, check_rate_limit, get_client_ip
from datetime import datetime
from telegram import Bot
import logging
import asyncio

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

# Maintenance mode cache
_maintenance_mode = None
_maintenance_cache_time = 0


async def get_maintenance_mode(db) -> bool:
    """Get maintenance mode status with caching"""
    global _maintenance_mode, _maintenance_cache_time
    import time
    
    current_time = time.time()
    if _maintenance_mode is not None and (current_time - _maintenance_cache_time) < 10:
        return _maintenance_mode
    
    try:
        config = await db.bot_settings.find_one({"_id": "maintenance"})
        _maintenance_mode = config.get("enabled", False) if config else False
        _maintenance_cache_time = current_time
        return _maintenance_mode
    except:
        return False


def clear_maintenance_cache():
    """Clear maintenance mode cache"""
    global _maintenance_mode, _maintenance_cache_time
    _maintenance_mode = None
    _maintenance_cache_time = 0


@router.get("/maintenance")
async def get_maintenance_status(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)
):
    """Get maintenance mode status"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    config = await db.bot_settings.find_one({"_id": "maintenance"})
    
    return {
        "enabled": config.get("enabled", False) if config else False,
        "message": config.get("message", "") if config else "",
        "updated_at": config.get("updated_at") if config else None,
        "updated_by": config.get("updated_by") if config else None
    }


@router.post("/maintenance/enable")
async def enable_maintenance(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
):
    """Enable maintenance mode and notify all users"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        # Save maintenance status
        await db.bot_settings.update_one(
            {"_id": "maintenance"},
            {"$set": {
                "_id": "maintenance",
                "enabled": True,
                "message": "🔧 Бот находится на техническом обслуживании. Пожалуйста, подождите.",
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": admin
            }},
            upsert=True
        )
        
        clear_maintenance_cache()
        
        # Send notification to all users
        bot = Bot(token=settings.telegram_bot_token)
        users = await db.telegram_users.find({}).to_list(1000)
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                telegram_id = user.get("telegram_id")
                if telegram_id:
                    # Get user language
                    lang = user.get("language", "ru")
                    
                    if lang == "en":
                        message_text = (
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "🔧 *MAINTENANCE MODE*\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            "Bot is temporarily unavailable.\n"
                            "Technical maintenance in progress.\n\n"
                            "Please wait. We will notify you\n"
                            "when the bot is back online.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━"
                        )
                    else:
                        message_text = (
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "🔧 *ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ*\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            "Бот временно недоступен.\n"
                            "Проводятся технические работы.\n\n"
                            "Пожалуйста, подождите. Мы сообщим,\n"
                            "когда бот снова заработает.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━"
                        )
                    
                    await bot.send_message(
                        chat_id=int(telegram_id),
                        text=message_text,
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                    await asyncio.sleep(0.05)  # Rate limiting
            except Exception as e:
                failed_count += 1
                logger.debug(f"Failed to notify user {user.get('telegram_id')}: {e}")
        
        logger.info(f"[MAINTENANCE] Enabled by {admin}. Notified {sent_count} users, {failed_count} failed")
        
        return {
            "success": True,
            "message": "Maintenance mode enabled",
            "users_notified": sent_count,
            "users_failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error enabling maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/disable")
async def disable_maintenance(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
):
    """Disable maintenance mode and notify all users"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        # Save maintenance status
        await db.bot_settings.update_one(
            {"_id": "maintenance"},
            {"$set": {
                "enabled": False,
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": admin
            }},
            upsert=True
        )
        
        clear_maintenance_cache()
        
        # Send notification to all users
        bot = Bot(token=settings.telegram_bot_token)
        users = await db.telegram_users.find({}).to_list(1000)
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *БОТ СНОВА РАБОТАЕТ*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Технические работы завершены!\n"
            "Бот полностью функционирует.\n\n"
            "Спасибо за терпение! 🙏\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                telegram_id = user.get("telegram_id")
                if telegram_id:
                    await bot.send_message(
                        chat_id=int(telegram_id),
                        text=message_text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                    sent_count += 1
                    await asyncio.sleep(0.05)
            except Exception as e:
                failed_count += 1
                logger.debug(f"Failed to notify user {user.get('telegram_id')}: {e}")
        
        logger.info(f"[MAINTENANCE] Disabled by {admin}. Notified {sent_count} users, {failed_count} failed")
        
        return {
            "success": True,
            "message": "Maintenance mode disabled",
            "users_notified": sent_count,
            "users_failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error disabling maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-config")
async def get_api_config(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)
):
    """Retrieve current API key configuration (protected)"""
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
    admin: str = Depends(verify_admin)
):
    """Update API key environment configuration (protected)"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        config_data = {
            "_id": "api_config",
            "environment": new_config.environment,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": admin
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
