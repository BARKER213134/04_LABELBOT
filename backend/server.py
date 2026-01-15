from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from database import connect_db, close_db
from routes import orders, admin, telegram, statistics, users, oxapay, broadcast
from config import get_settings

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("Starting ShipBot API...")
    await connect_db()
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