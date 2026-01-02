"""
Reset sandbox environment to initial state
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.execution_feedback import ExecutionFeedback
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.embedding import Embedding


async def reset_sandbox():
    """Reset sandbox database to initial state"""
    print("🔄 Resetting sandbox environment...")
    
    db = SessionLocal()
    try:
        # Delete all user-created data (keep tenant and demo user)
        print("   Deleting execution data...")
        db.query(ExecutionFeedback).filter(ExecutionFeedback.session_id.in_(
            db.query(ExecutionSession.id).filter(ExecutionSession.tenant_id == 1)
        )).delete(synchronize_session=False)
        db.query(ExecutionStep).filter(ExecutionStep.session_id.in_(
            db.query(ExecutionSession.id).filter(ExecutionSession.tenant_id == 1)
        )).delete(synchronize_session=False)
        db.query(ExecutionSession).filter(ExecutionSession.tenant_id == 1).delete()
        
        print("   Deleting runbooks...")
        db.query(Runbook).filter(Runbook.tenant_id == 1).delete()
        
        print("   Deleting tickets...")
        db.query(Ticket).filter(Ticket.tenant_id == 1).delete()
        
        print("   Deleting documents and embeddings...")
        db.query(Embedding).filter(Embedding.document_id.in_(
            db.query(Document.id).filter(Document.tenant_id == 1)
        )).delete(synchronize_session=False)
        db.query(Chunk).filter(Chunk.document_id.in_(
            db.query(Document.id).filter(Document.tenant_id == 1)
        )).delete(synchronize_session=False)
        db.query(Document).filter(Document.tenant_id == 1).delete()
        
        db.commit()
        print("✅ Sandbox reset completed")
        print("\n💡 Run seed_sandbox_data.py to repopulate with sample data")
        
    except Exception as e:
        print(f"❌ Error resetting sandbox: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(reset_sandbox())



