from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection - ULTRA FAST"""
    try:
        settings = get_settings()
        mongo_url = settings.mongo_url
        
        Database.client = AsyncIOMotorClient(
            mongo_url, 
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
            socketTimeoutMS=3000,
            maxPoolSize=20,
            minPoolSize=5,
            maxIdleTimeMS=10000,
            retryWrites=True,
            retryReads=True,
            w=1,  # Faster writes (no waiting for replication)
            journal=False,  # Faster writes (no journaling)
        )
        Database.db = Database.client[settings.db_name]
        logger.info(f"Connected to MongoDB: {settings.db_name}")
            
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db