"""
Database configuration and connection management
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create database engine (standard pooled engine for Postgres)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for table creation
metadata = MetaData()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database tables and extensions"""
    try:
        # Import all models to ensure they're registered
        from app.models import tenant, user, document, chunk, embedding, runbook, execution, audit
        from app.models import system_config, runbook_usage, runbook_similarity, runbook_citation
        from app.models import ticket, credential  # New models for Phase 2
        from app.models import execution_session  # Execution tracking + orchestration tables
        try:
            from app.models import ticketing_tool_connection  # Ticketing tool connections
        except ImportError:
            pass
        
        # Enable pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Seed default tenant (required for foreign key constraints)
        from app.models.tenant import Tenant
        with SessionLocal() as db:
            # Create demo tenant (id=1) if it doesn't exist
            demo_tenant = db.query(Tenant).filter(Tenant.id == 1).first()
            if not demo_tenant:
                demo_tenant = Tenant(
                    id=1,
                    name="demo",
                    description="Demo tenant for development",
                    is_active=True
                )
                db.add(demo_tenant)
                db.commit()
                logger.info("Created demo tenant (id=1)")
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


