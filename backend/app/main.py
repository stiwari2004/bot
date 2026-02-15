"""
Troubleshooting AI Agent - FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.database import init_db, engine
from app.core.logging import setup_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
from app.api.v1.api import api_router

# Setup structured logging first (needed for rate limiting messages)
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# Rate limiting (MF-10) - Optional, graceful fallback if slowapi not installed
limiter = None
_rate_limit_exceeded_handler = None
RateLimitExceeded = None

if settings.RATE_LIMIT_ENABLED:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        
        try:
            # Try to initialize limiter - it may try to read .env file
            limiter = Limiter(key_func=get_remote_address)
            # Set global limiter for use in endpoints
            from app.core.rate_limiting import set_limiter
            set_limiter(limiter)
            logger.info("Rate limiting enabled (slowapi installed)")
        except PermissionError as e:
            # If .env file has permission issues, disable rate limiting gracefully
            logger.warning(
                f"Rate limiting disabled: Permission denied reading .env file. "
                f"Error: {e}. Rate limiting will be disabled. "
                f"This is OK if all required settings are set via environment variables."
            )
            limiter = None
    except ImportError:
        logger.warning("Rate limiting disabled: slowapi not installed. Install with: pip install slowapi")
        limiter = None
else:
    logger.info("Rate limiting disabled (RATE_LIMIT_ENABLED=false)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Troubleshooting AI Agent")
    await init_db()
    logger.info("Database initialized")
    
    # Validate license activation in PaaS mode
    try:
        from app.services.license.license_activation_service import LicenseActivationService
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            activation_service = LicenseActivationService(db)
            is_valid, error, info = activation_service.validate_activation()
            if not is_valid and activation_service.is_paas_mode():
                logger.error(f"License validation failed in PaaS mode: {error}")
                logger.error("Application will start but operations may be restricted. Please activate your license key.")
            elif is_valid and activation_service.is_paas_mode():
                logger.info(f"License validated successfully. Activated on: {info.get('server_fingerprint', 'unknown')[:16]}...")
        except Exception as e:
            logger.warning(f"License validation check failed (non-critical): {e}")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"License validation check failed (non-critical): {e}")
    
    # Start WebSocket cleanup task
    import asyncio
    from app.services.execution.websocket_manager import WebSocketManager
    cleanup_task = None
    try:
        cleanup_task = asyncio.create_task(WebSocketManager.cleanup_idle_connections())
        logger.info("WebSocket cleanup task started")
    except Exception as e:
        logger.warning(f"Failed to start WebSocket cleanup task: {e}")
    
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
                    get_shared_embedding_model(),  # Now async
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
    
    # Start alert poller service (optional, can be disabled via env var)
    enable_alert_poller = os.getenv("ENABLE_ALERT_POLLER", "true").lower() in ("1", "true", "yes")
    if enable_alert_poller:
        try:
            from app.services.alert_poller import start_poller as start_alert_poller
            await start_alert_poller()
            logger.info("Alert poller service started")
        except Exception as e:
            logger.error(f"Failed to start alert poller: {e}", exc_info=True)
    else:
        logger.info("Alert poller service disabled (ENABLE_ALERT_POLLER=false)")
    
    # Start report scheduler service (optional, can be disabled via env var)
    enable_report_scheduler = os.getenv("ENABLE_REPORT_SCHEDULER", "true").lower() in ("1", "true", "yes")
    if enable_report_scheduler:
        try:
            from app.services.reporting.report_scheduler import ReportScheduler
            scheduler_interval = int(os.getenv("REPORT_SCHEDULER_INTERVAL", "300"))  # Default: 5 minutes
            await ReportScheduler.start(check_interval=scheduler_interval)
            logger.info(f"Report scheduler service started (check interval: {scheduler_interval}s)")
        except Exception as e:
            logger.error(f"Failed to start report scheduler: {e}", exc_info=True)
    else:
        logger.info("Report scheduler service disabled (ENABLE_REPORT_SCHEDULER=false)")
    
    yield
    
    # Shutdown: Stop report scheduler
    try:
        from app.services.reporting.report_scheduler import ReportScheduler
        await ReportScheduler.stop()
    except Exception:
        pass
    # Shutdown
    logger.info("Shutting down Troubleshooting AI Agent")
    
    # Cancel WebSocket cleanup task
    if cleanup_task is not None:
        try:
            cleanup_task.cancel()
            await asyncio.wait_for(cleanup_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception as e:
            logger.warning(f"Error cancelling WebSocket cleanup task: {e}")
        logger.info("WebSocket cleanup task stopped")
    
    # Stop ticketing poller service
    try:
        from app.services.ticketing_poller import stop_poller
        # Use asyncio.wait_for to ensure we don't block shutdown
        try:
            await asyncio.wait_for(stop_poller(), timeout=5.0)
            logger.info("Ticketing poller service stopped")
        except asyncio.TimeoutError:
            logger.warning("Ticketing poller service stop timed out")
    except Exception as e:
        logger.warning(f"Error stopping ticketing poller: {e}")
    
    # Stop alert poller service
    try:
        from app.services.alert_poller import stop_poller as stop_alert_poller
        try:
            await asyncio.wait_for(stop_alert_poller(), timeout=5.0)
            logger.info("Alert poller service stopped")
        except asyncio.TimeoutError:
            logger.warning("Alert poller service stop timed out")
    except Exception as e:
        logger.warning(f"Error stopping alert poller: {e}")


# Create FastAPI application
# Configure to work behind reverse proxy (nginx)
# root_path is used when FastAPI is behind a proxy at a subpath
app = FastAPI(
    title="Troubleshooting AI Agent",
    description="AI-powered IT infrastructure troubleshooting and runbook generation",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False  # Disable automatic trailing slash redirects to prevent HTTP redirect issues
)

# Add rate limiting if enabled (MF-10)
if limiter and RateLimitExceeded and _rate_limit_exceeded_handler:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware to handle X-Forwarded-Proto for HTTPS redirects behind nginx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-Proto for HTTPS redirects"""
    async def dispatch(self, request: Request, call_next):
        # If X-Forwarded-Proto is https, update the request URL scheme
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto == "https":
            request.scope["scheme"] = "https"
            logger.debug(f"Updated request scheme to https for {request.url.path}")
        
        response = await call_next(request)
        
        # Fix redirect location headers to use HTTPS if X-Forwarded-Proto is https
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if location:
                logger.info(f"Redirect detected: {response.status_code} -> {location}")
                if forwarded_proto == "https" and location.startswith("http://"):
                    old_location = location
                    new_location = location.replace("http://", "https://", 1)
                    response.headers["location"] = new_location
                    logger.info(f"Fixed redirect location: {old_location} -> {new_location}")
                elif forwarded_proto == "https" and not location.startswith("http"):
                    # Relative URL - should be fine, but log it
                    logger.debug(f"Redirect location is relative: {location}")
        
        return response

# Request ID middleware (must be first)
app.add_middleware(RequestIDMiddleware)
# Proxy headers middleware (before CORS, after RequestID)
app.add_middleware(ProxyHeadersMiddleware)
# Security headers middleware (after proxy, before CORS)
from app.core.security_middleware import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
# Compression middleware (after security, before CORS)
from app.core.compression_middleware import CompressionMiddleware
app.add_middleware(CompressionMiddleware)

# CORS middleware - Security: Restrict methods and headers
# In sandbox/dev mode, allow all localhost origins for easier testing
cors_origins = settings.ALLOWED_HOSTS
if settings.ENVIRONMENT.lower() in ("sandbox", "development", "dev"):
    # Allow all localhost origins and dev domain in sandbox/dev
    cors_origins = [
        "http://localhost:3000", 
        "http://localhost:3001", 
        "http://localhost:4321",  # Astro marketing site dev server
        "http://localhost:8000", 
        "http://localhost:8001",
        "https://dev.resolvify.tech",
        "https://resolvify.tech",
    ]
    logger.info(f"CORS: Allowing localhost and dev domain origins for {settings.ENVIRONMENT} environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # Restrict headers
    expose_headers=["X-Total-Count", "X-Page-Count"],  # Only expose necessary headers
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


@app.get("/health/db")
async def health_check_db():
    """Health check that verifies database connectivity. Returns 503 if DB is unreachable."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "ok"}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return Response(
            content='{"status":"unhealthy","database":"error","detail":"Database temporarily unavailable"}',
            status_code=503,
            media_type="application/json",
        )


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

