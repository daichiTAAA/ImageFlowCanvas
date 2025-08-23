import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


# Database URL with fallback support
def get_database_url():
    """Get database URL with fallback support for Nomad environment"""
    primary_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://imageflow:imageflow123@postgres-service:5432/imageflow",
    )

    # Log the detected environment
    nomad_alloc_id = os.getenv("NOMAD_ALLOC_ID")
    nomad_deployment = os.getenv("NOMAD_DEPLOYMENT")

    if nomad_alloc_id or nomad_deployment:
        logger.info(f"Detected Nomad environment - NOMAD_ALLOC_ID: {nomad_alloc_id}")
        logger.info(f"Using database URL: {primary_url}")

        # In Nomad environment, use host network mode with localhost
        if "postgres.service.consul" in primary_url:
            fallback_url = primary_url.replace("postgres.service.consul", "localhost")
            logger.info(f"Fallback database URL prepared: {fallback_url}")
            return primary_url, fallback_url
    else:
        logger.info(f"Using standard database URL: {primary_url}")

    return primary_url, None


# Get database URLs
PRIMARY_DATABASE_URL, FALLBACK_DATABASE_URL = get_database_url()

# Create async engine
engine = create_async_engine(PRIMARY_DATABASE_URL, echo=True)

# Create async session factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()


async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables with fallback support"""
    global engine, AsyncSessionLocal

    try:
        # Import all models to ensure they are registered with Base
        from app.models import pipeline, execution, pipeline_db
        from app.models import product  # ensure product models are registered
        from app.models.inspection import (
            inspectionInstruction,
            InspectionItem,
            InspectionCriteria,
            InspectionExecution,
            InspectionItemExecution,
            InspectionResult,
        )

        # Try primary database URL first
        logger.info("Attempting to connect to primary database...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Primary database connection successful")

    except Exception as primary_error:
        logger.error(f"❌ Primary database connection failed: {primary_error}")

        # If fallback URL is available, try it
        if FALLBACK_DATABASE_URL:
            logger.warning("🔄 Trying fallback database connection...")
            try:
                # Create new engine with fallback URL
                fallback_engine = create_async_engine(FALLBACK_DATABASE_URL, echo=True)

                # Test the fallback connection
                async with fallback_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                # If successful, replace the global engine and session
                engine = fallback_engine
                AsyncSessionLocal = sessionmaker(
                    engine, class_=AsyncSession, expire_on_commit=False
                )
                logger.info("✅ Fallback database connection successful")

            except Exception as fallback_error:
                logger.error(
                    f"❌ Fallback database connection also failed: {fallback_error}"
                )
                logger.error("🆘 All database connection attempts failed")
                raise primary_error  # Raise the original error
        else:
            logger.error("🆘 No fallback database URL available")
            raise primary_error
