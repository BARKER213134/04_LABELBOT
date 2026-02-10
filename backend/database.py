from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection with optimized settings"""
    try:
        settings = get_settings()
        mongo_url = settings.mongo_url
        
        logger.info(f"Connecting to MongoDB... (db: {settings.db_name})")
        Database.client = AsyncIOMotorClient(
            mongo_url, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            retryWrites=True,
            retryReads=True
        )
        Database.db = Database.client[settings.db_name]
        
        # Test connection (but don't block startup)
        try:
            await Database.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.db_name}")
        except Exception as e:
            logger.warning(f"Initial ping failed, but connection pool is ready: {e}")
            
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.warning("Server will start but database operations may fail")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()
        logger.info("Closed MongoDB connection")

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db