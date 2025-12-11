#!/usr/bin/env python3
"""
Quick script to check backend startup issues
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import engine, SessionLocal
from sqlalchemy import text

setup_logging("INFO")
logger = get_logger(__name__)

async def check_backend_status():
    """Check various backend components"""
    print("=" * 60)
    print("Backend Status Check")
    print("=" * 60)
    
    # 1. Check configuration
    print("\n1. Configuration:")
    print(f"   DATABASE_URL: {settings.DATABASE_URL[:50]}..." if settings.DATABASE_URL else "   DATABASE_URL: NOT SET")
    print(f"   ENVIRONMENT: {settings.ENVIRONMENT}")
    print(f"   PRELOAD_EMBEDDING_MODEL: {os.getenv('PRELOAD_EMBEDDING_MODEL', 'false')}")
    print(f"   ENABLE_TICKETING_POLLER: {os.getenv('ENABLE_TICKETING_POLLER', 'true')}")
    
    # 2. Check database connection
    print("\n2. Database Connection:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # 3. Check database initialization
    print("\n3. Database Initialization:")
    try:
        from app.core.database import init_db
        await init_db()
        print("   ✅ Database initialization successful")
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Check embedding model (if preload enabled)
    if os.getenv("PRELOAD_EMBEDDING_MODEL", "false").lower() in ("1", "true", "yes"):
        print("\n4. Embedding Model:")
        try:
            from app.core.vector_store import get_shared_embedding_model
            print("   Loading embedding model (this may take 30-60 seconds)...")
            model = await asyncio.wait_for(
                get_shared_embedding_model(),
                timeout=120.0
            )
            print(f"   ✅ Embedding model loaded: {settings.EMBEDDING_MODEL}")
        except asyncio.TimeoutError:
            print("   ⚠️  Embedding model loading timed out (2 minutes)")
        except Exception as e:
            print(f"   ❌ Embedding model loading failed: {e}")
    else:
        print("\n4. Embedding Model:")
        print("   ⏭️  Preloading disabled (will load on first use)")
    
    # 5. Check ticketing poller (if enabled)
    if os.getenv("ENABLE_TICKETING_POLLER", "true").lower() in ("1", "true", "yes"):
        print("\n5. Ticketing Poller:")
        try:
            from app.services.ticketing_poller import start_poller
            print("   Starting poller...")
            await asyncio.wait_for(start_poller(), timeout=10.0)
            print("   ✅ Ticketing poller started")
        except asyncio.TimeoutError:
            print("   ⚠️  Ticketing poller start timed out (10 seconds)")
        except Exception as e:
            print(f"   ❌ Ticketing poller start failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n5. Ticketing Poller:")
        print("   ⏭️  Disabled via ENABLE_TICKETING_POLLER=false")
    
    print("\n" + "=" * 60)
    print("Status check complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        asyncio.run(check_backend_status())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()







