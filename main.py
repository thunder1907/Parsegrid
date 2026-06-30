import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router
from models.database import Base, async_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initializes the database models on startup."""
    try:
        async with async_engine.begin() as conn:
            # Emits the DDL to create tables (only if they don't exist)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern lifespan event handler for FastAPI initialization and teardown.
    """
    # Startup phase
    logger.info("Starting up application and running database initialization...")
    await init_db()
    
    yield  # Application serves requests while suspended here
    
    # Shutdown phase
    logger.info("Shutting down application...")
    await async_engine.dispose()
    logger.info("Database engine connections closed.")


# Instantiate the FastAPI application
app = FastAPI(
    title="Document Extraction API",
    description="Intelligent API for processing and extracting structured data from PDF contracts using AI.",
    version="1.0.0",
    lifespan=lifespan
)

# Connect the routing layer
app.include_router(router)
