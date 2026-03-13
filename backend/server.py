from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import asyncio
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("=" * 50)
logger.info("Starting ShipBot API server...")
logger.info("=" * 50)

try:
    ROOT_DIR = Path(__file__).parent
    env_file = ROOT_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded .env from {env_file}")
except Exception as e:
    logger.warning(f"Error loading .env: {e}")

try:
    from config import get_settings
    settings = get_settings()
    logger.info(f"Settings loaded: environment={settings.environment}, db={settings.db_name}")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    raise

_routes_loaded = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    global _routes_loaded
    logger.info("Lifespan startup...")

    try:
        from database import connect_db, close_db
        await connect_db()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    try:
        from services.security import set_admin_password
        if settings.admin_password:
            set_admin_password(settings.admin_password)
            logger.info("Admin security initialized")
    except Exception as e:
        logger.error(f"Security init failed: {e}")

    # Load routes LAZILY inside lifespan so server binds to port faster
    try:
        from routes import orders, admin, telegram, statistics, users, oxapay, broadcast
        api_router = APIRouter(prefix="/api")

        @api_router.get("/")
        async def root():
            return {"message": "ShipBot API is running"}

        @api_router.get("/health")
        async def api_health_check():
            return {"status": "healthy", "environment": settings.environment}

        api_router.include_router(orders.router)
        api_router.include_router(admin.router)
        api_router.include_router(telegram.router)
        api_router.include_router(statistics.router)
        api_router.include_router(users.router)
        api_router.include_router(oxapay.router)
        api_router.include_router(broadcast.router)
        app.include_router(api_router)
        _routes_loaded = True
        logger.info("Routes loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load routes: {e}")

    # Preload telegram bot in BACKGROUND
    async def _background_bot_preload():
        try:
            from routes.telegram import _preload_bot
            await _preload_bot()
            logger.info("Bot preloaded successfully (background)")
        except Exception as e:
            logger.error(f"Bot preload failed: {e}")

    asyncio.create_task(_background_bot_preload())

    yield
    logger.info("Shutting down...")
    try:
        from database import close_db
        await close_db()
    except Exception:
        pass

app = FastAPI(
    title="ShipBot API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# Health check available IMMEDIATELY - before any routes load
@app.get("/health")
async def root_health_check():
    return {"status": "healthy", "environment": settings.environment}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
