from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection with retry logic for DNS resolution in Kubernetes"""
    settings = get_settings()
    mongo_url = settings.mongo_url

    max_retries = 5
    retry_delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            Database.client = AsyncIOMotorClient(
                mongo_url,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=10000,
                socketTimeoutMS=15000,
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

            # Verify connection actually works (triggers DNS resolution)
            await Database.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {settings.db_name} (attempt {attempt})")
            return

        except Exception as e:
            logger.warning(f"MongoDB connection attempt {attempt}/{max_retries} failed: {e}")
            if Database.client:
                Database.client.close()
                Database.client = None
                Database.db = None

            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
            else:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts")
                # Create client without ping verification as last resort
                Database.client = AsyncIOMotorClient(
                    mongo_url,
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=15000,
                    socketTimeoutMS=15000,
                    maxPoolSize=50,
                    minPoolSize=5,
                    retryWrites=True,
                    retryReads=True,
                )
                Database.db = Database.client[settings.db_name]
                logger.warning("MongoDB client created without verification (lazy connect)")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db
