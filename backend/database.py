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
        mongo_url = settings.mongo_url
        
        logger.info(f"Connecting to MongoDB... (db: {settings.db_name})")
        Database.client = AsyncIOMotorClient(
            mongo_url, 
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        Database.db = Database.client[settings.db_name]
        
        # Test connection
        await Database.client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.db_name}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Don't raise - allow server to start, will retry on requests
        logger.warning("Server will start but database operations may fail")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()
        logger.info("Closed MongoDB connection")

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db