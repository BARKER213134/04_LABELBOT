from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection - fast startup, verify in background"""
    settings = get_settings()
    mongo_url = settings.mongo_url

    # Create Motor client immediately (Motor is lazy - no TCP connection yet)
    Database.client = AsyncIOMotorClient(
        mongo_url,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=50,
        minPoolSize=5,
        maxIdleTimeMS=30000,
        waitQueueTimeoutMS=10000,
        retryWrites=True,
        retryReads=True,
        w=1,
        readPreference='primaryPreferred',
    )
    Database.db = Database.client[settings.db_name]
    logger.info(f"MongoDB client created for: {settings.db_name} (lazy connect)")

    # Quick ping attempt (3s timeout) - non-fatal if fails
    try:
        await asyncio.wait_for(Database.client.admin.command("ping"), timeout=3.0)
        logger.info("MongoDB ping OK")
    except Exception as e:
        logger.warning(f"MongoDB ping failed (non-fatal, will retry lazily): {e}")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db
