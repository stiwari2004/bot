#!/usr/bin/env python3
"""
Script to index all approved runbooks into the vector store
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.runbook import Runbook
from app.services.runbook_generator import RunbookGeneratorService


async def index_all_runbooks():
    """Index all approved runbooks into the vector store"""
    db = SessionLocal()
    try:
        # Get all approved runbooks
        runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == 1,
            Runbook.status == "approved"
        ).all()
        
        print(f"Found {len(runbooks)} approved runbooks to index")
        
        generator = RunbookGeneratorService()
        
        for runbook in runbooks:
            print(f"\nProcessing runbook {runbook.id}: {runbook.title}")
            try:
                await generator._index_runbook_for_search(runbook, db)
                print(f"  ✓ Successfully indexed")
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"\n✅ Done! Indexed {len(runbooks)} runbooks")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(index_all_runbooks())


