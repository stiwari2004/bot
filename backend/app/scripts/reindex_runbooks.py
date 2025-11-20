#!/usr/bin/env python3
"""
Re-index all approved runbooks for vector search.

This script indexes all approved runbooks that are currently missing
from the vector store, making them searchable via the Ticket Analyzer.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
# Import all models to ensure relationships are loaded
from app.models import tenant, user, document, chunk, embedding, runbook, execution, audit
from app.models import system_config, runbook_usage, runbook_similarity, runbook_citation
from app.models.runbook import Runbook
from app.services.runbook.generation import RunbookGeneratorService


async def reindex_all_approved_runbooks():
    """Re-index all approved runbooks for search"""
    db: Session = SessionLocal()
    
    try:
        # Get all approved runbooks
        approved_runbooks = db.query(Runbook).filter(
            Runbook.status == 'approved'
        ).order_by(Runbook.id).all()
        
        print(f"\nFound {len(approved_runbooks)} approved runbooks to index\n")
        
        if not approved_runbooks:
            print("No approved runbooks found. Nothing to do.")
            return
        
        # Initialize the generator service
        generator = RunbookGeneratorService()
        
        # Track progress
        indexed_count = 0
        skipped_count = 0
        error_count = 0
        
        for runbook in approved_runbooks:
            try:
                print(f"Indexing runbook {runbook.id}: {runbook.title[:60]}...", end=" ")
                
                # Check if already indexed
                from app.models.document import Document
                runbook_path = f"runbook_{runbook.id}.md"
                existing_doc = db.query(Document).filter(
                    Document.path == runbook_path,
                    Document.tenant_id == runbook.tenant_id
                ).first()
                
                if existing_doc:
                    print("SKIPPED (already indexed)")
                    skipped_count += 1
                    continue
                
                # Index the runbook
                await generator._index_runbook_for_search(runbook, db)
                print("✓ INDEXED")
                indexed_count += 1
                
            except Exception as e:
                print(f"✗ ERROR: {e}")
                error_count += 1
                db.rollback()
                continue
        
        # Print summary
        print("\n" + "="*70)
        print("INDEXING COMPLETE")
        print("="*70)
        print(f"Total runbooks:      {len(approved_runbooks)}")
        print(f"Newly indexed:       {indexed_count}")
        print(f"Skipped (existing):  {skipped_count}")
        print(f"Errors:              {error_count}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def main():
    """Main entry point"""
    print("\nRe-indexing all approved runbooks for vector search...")
    asyncio.run(reindex_all_approved_runbooks())


if __name__ == "__main__":
    main()

