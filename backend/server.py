from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting ShipBot API server...")
logger.info("=" * 50)

try:
    ROOT_DIR = Path(__file__).parent
    env_file = ROOT_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded .env from {env_file}")
    else:
        logger.info("No .env file found, using environment variables")
except Exception as e:
    logger.warning(f"Error loading .env: {e}")

try:
    from config import get_settings
    settings = get_settings()
    logger.info(f"Settings loaded: environment={settings.environment}, db={settings.db_name}")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    raise

try:
    from database import connect_db, close_db
    logger.info("Database module loaded")
except Exception as e:
    logger.error(f"Failed to import database: {e}")
    raise

try:
    from routes import orders, admin, telegram, statistics, users, oxapay, broadcast
    logger.info("Routes modules loaded")
except Exception as e:
    logger.error(f"Failed to import routes: {e}")
    raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("Lifespan startup...")
    try:
        await connect_db()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Don't raise - let server start anyway
    yield
    logger.info("Shutting down...")
    await close_db()

app = FastAPI(
    title="ShipBot API",
    version="1.0.0",
    description="Shipping label management with Telegram bot integration",
    lifespan=lifespan,
    redirect_slashes=False
)

# Root level health check for Kubernetes probes
@app.get("/health")
async def root_health_check():
    return {"status": "healthy", "environment": settings.environment}

# Create API router
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {"message": "ShipBot API is running"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment
    }

# Include routers
api_router.include_router(orders.router)
api_router.include_router(admin.router)
api_router.include_router(telegram.router)
api_router.include_router(statistics.router)
api_router.include_router(users.router)
api_router.include_router(oxapay.router)
api_router.include_router(broadcast.router)

app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)