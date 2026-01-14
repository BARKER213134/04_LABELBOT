from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection"""
    try:
        settings = get_settings()
        Database.client = AsyncIOMotorClient(settings.mongo_url)
        Database.db = Database.client[settings.db_name]
        logger.info(f"Connected to MongoDB: {settings.db_name}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()
        logger.info("Closed MongoDB connection")

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db