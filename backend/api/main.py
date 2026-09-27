import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_read_only_pool, close_read_only_pool
from api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up FastAPI Backend...")
    try:
        app.state.pool = await get_read_only_pool()
        logger.info("Connected to packaged SQLite database in read-only mode.")
    except Exception as e:
        app.state.pool = None
        logger.error("Could not open packaged SQLite database: %s", e)
    yield
    # Shutdown
    logger.info("Shutting down FastAPI Backend...")
    await close_read_only_pool()
    app.state.pool = None
    logger.info("Database connection closed.")

app = FastAPI(
    title="Google Photos Discovery Engine API",
    description="API for accessing Google Photos vague retrieval frustration clusters and semantic search.",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(router)

# Vercel packages this build beside backend/. During local API-only development the
# directory may be absent; the API still starts and reports an honest 404 for pages.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app.frontend("/", directory=str(FRONTEND_DIST), fallback="index.html", check_dir=False)
