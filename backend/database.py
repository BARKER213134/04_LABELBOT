from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

async def connect_db():
    """Initialize database connection - OPTIMIZED for 50+ concurrent users"""
    try:
        settings = get_settings()
        mongo_url = settings.mongo_url
        
        Database.client = AsyncIOMotorClient(
            mongo_url, 
            # Timeouts
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            
            # Connection Pool - optimized for 50+ users
            maxPoolSize=50,        # Max connections per pod
            minPoolSize=10,        # Keep 10 connections warm
            maxIdleTimeMS=30000,   # Close idle connections after 30s
            waitQueueTimeoutMS=5000,  # Wait max 5s for connection
            
            # Reliability
            retryWrites=True,
            retryReads=True,
            
            # Performance
            w=1,                   # Fast writes (acknowledge from primary only)
            readPreference='primaryPreferred',  # Read from primary, fallback to secondary
            
            # Compression for faster data transfer
            compressors=['zstd', 'zlib', 'snappy'],
        )
        Database.db = Database.client[settings.db_name]
        logger.info(f"Connected to MongoDB: {settings.db_name} (pool: 10-50)")
            
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()

def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database instance"""
    return Database.db