"""
Troubleshooting AI Agent - FastAPI Main Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
from app.api.v1.api import api_router

# Setup structured logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Troubleshooting AI Agent")
    await init_db()
    logger.info("Database initialized")
    
    # Preload embedding model to avoid first-request delay
    # Use lazy loading with timeout to prevent blocking startup on constrained systems
    # On 6GB RAM systems, model loading can take 2-3 minutes or fail
    import os
    preload_embedding = os.getenv("PRELOAD_EMBEDDING_MODEL", "false").lower() in ("1", "true", "yes")
    
    if preload_embedding:
        try:
            logger.info("Preloading embedding model (this may take 30-60 seconds)...")
            import asyncio
            from app.core.vector_store import get_shared_embedding_model
            
            # Load model with timeout to prevent infinite blocking
            try:
                model = await asyncio.wait_for(
                    asyncio.to_thread(get_shared_embedding_model),
                    timeout=120.0  # 2 minute timeout
                )
                logger.info(f"✅ Embedding model loaded: {settings.EMBEDDING_MODEL}")
            except asyncio.TimeoutError:
                logger.warning("Embedding model loading timed out after 2 minutes")
                logger.warning("Model will be loaded on first use (may cause delay)")
        except Exception as e:
            logger.error(f"Failed to preload embedding model: {e}", exc_info=True)
            logger.warning("Embedding model will be loaded on first use (may cause delay)")
    else:
        logger.info("Embedding model preloading disabled (PRELOAD_EMBEDDING_MODEL=false)")
        logger.info("Model will be loaded on first use (lazy loading)")
    
    # Start ticketing poller service (optional, can be disabled via env var)
    enable_poller = os.getenv("ENABLE_TICKETING_POLLER", "true").lower() in ("1", "true", "yes")
    if enable_poller:
        try:
            from app.services.ticketing_poller import start_poller
            await start_poller()
            logger.info("Ticketing poller service started")
        except Exception as e:
            logger.error(f"Failed to start ticketing poller: {e}", exc_info=True)
    else:
        logger.info("Ticketing poller service disabled (ENABLE_TICKETING_POLLER=false)")
    
    yield
    # Shutdown
    logger.info("Shutting down Troubleshooting AI Agent")
    
    # Stop ticketing poller service
    try:
        from app.services.ticketing_poller import stop_poller
        # Use asyncio.wait_for to ensure we don't block shutdown
        import asyncio
        try:
            await asyncio.wait_for(stop_poller(), timeout=5.0)
            logger.info("Ticketing poller service stopped")
        except asyncio.TimeoutError:
            logger.warning("Ticketing poller service stop timed out")
    except Exception as e:
        logger.warning(f"Error stopping ticketing poller: {e}")


# Create FastAPI application
app = FastAPI(
    title="Troubleshooting AI Agent",
    description="AI-powered IT infrastructure troubleshooting and runbook generation",
    version="1.0.0",
    lifespan=lifespan
)

# Request ID middleware (must be first)
app.add_middleware(RequestIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include OAuth callback route directly (needs to be at /oauth/callback)
try:
    from app.api.v1.endpoints import ticketing_connections
    from app.core.database import get_db
    from fastapi import Depends, Query
    from sqlalchemy.orm import Session
    
    if ticketing_connections:
        @app.get("/oauth/callback")
        async def oauth_callback_route(
            code: str = Query(...),
            state: str = Query(...),
            error: str = Query(None),
            db: Session = Depends(get_db)
        ):
            """OAuth callback handler"""
            return await ticketing_connections.oauth_callback(
                code=code, state=state, error=error, db=db
            )
except ImportError:
    pass

# Serve static files (test interface)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Test interface redirect
@app.get("/test")
async def test_interface():
    """Redirect to test interface"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/test.html")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

