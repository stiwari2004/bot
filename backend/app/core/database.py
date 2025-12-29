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
        from app.models import (
            tenant,
            user,
            document,
            chunk,
            embedding,
            runbook,
            execution,
            audit,
        )
        from app.models import super_admin  # Super Admin model
        from app.models import (
            system_config,
            runbook_usage,
            runbook_similarity,
            runbook_citation,
        )
        from app.models import ticket, alert, credential  # New models for Phase 2
        from app.models import execution_session  # Execution tracking + orchestration tables
        from app.models import execution_pattern  # Execution pattern tracking
        from app.models import pattern_feedback  # Pattern feedback tracking
        from app.models import runbook_metrics  # Runbook metrics caching
        from app.models import confidence_breakdown  # Confidence breakdown tracking
        from app.models import runbook_version  # Runbook versioning
        from app.models import citation_verification  # Citation verification
        from app.models import resolution_flow  # Resolution orchestration
        from app.models import decision_analytics  # Decision engine analytics
        from app.models import metadata_mapping  # Metadata mapping for input extraction learning
        from app.models import tenant_billing_config  # Tenant billing configuration
        from app.models import tenant_subscription  # Tenant subscription/license management
        try:
            from app.models import ticketing_tool_connection  # Ticketing tool connections
        except ImportError:
            pass
        try:
            from app.models import monitoring_tool_connection  # Monitoring tool connections
        except ImportError:
            pass
        try:
            from app.models import permission, role, role_permission, user_permission  # RBAC models
        except ImportError:
            pass
        try:
            from app.models import license_plan  # License plan models
        except ImportError:
            pass
        
        # Enable required PostgreSQL extensions
        with engine.connect() as conn:
            # Enable pgvector extension for vector similarity search
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Enable pg_trgm extension for trigram-based text search (used in ExecutionPattern indexes)
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.commit()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create full-text search index for execution_patterns.issue_signature
        # This needs to be done via raw SQL as SQLAlchemy doesn't handle gin_trgm_ops well
        with engine.connect() as conn:
            try:
                # Check if index already exists
                result = conn.execute(text("""
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_execution_patterns_signature'
                """))
                if result.fetchone() is None:
                    # Create GIN index with trigram operator class for fast text search
                    conn.execute(text("""
                        CREATE INDEX idx_execution_patterns_signature 
                        ON execution_patterns 
                        USING gin (issue_signature gin_trgm_ops)
                    """))
                    conn.commit()
                    logger.info("Created full-text search index for execution_patterns.issue_signature")
            except Exception as idx_error:
                # If pg_trgm extension is not available, create a simpler index
                logger.warning(f"Could not create trigram index: {idx_error}. Creating standard index instead.")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_execution_patterns_signature 
                        ON execution_patterns (issue_signature)
                    """))
                    conn.commit()
                    logger.info("Created standard index for execution_patterns.issue_signature")
                except Exception as fallback_error:
                    logger.warning(f"Could not create fallback index: {fallback_error}")
        
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


