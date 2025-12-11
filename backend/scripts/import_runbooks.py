#!/usr/bin/env python3
"""
Import runbooks into a tenant
Usage: python scripts/import_runbooks.py --input /app/exports/runbooks.json --target-tenant-id 1
"""
import sys
import os
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.runbook import Runbook
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def import_runbooks(input_path: str, target_tenant_id: int, skip_existing: bool = True):
    """Import runbooks into a tenant"""
    await init_db()
    db: Session = SessionLocal()
    
    try:
        # Read export file
        with open(input_path, 'r') as f:
            export_data = json.load(f)
        
        runbooks_data = export_data.get("runbooks", [])
        logger.info(f"Importing {len(runbooks_data)} runbooks to tenant {target_tenant_id}")
        
        imported = 0
        skipped = 0
        errors = 0
        
        for rb_data in runbooks_data:
            try:
                # Check if runbook with same title already exists
                existing = db.query(Runbook).filter(
                    Runbook.tenant_id == target_tenant_id,
                    Runbook.title == rb_data["title"]
                ).first()
                
                if existing and skip_existing:
                    logger.info(f"Skipping existing runbook: {rb_data['title']}")
                    skipped += 1
                    continue
                
                # Create new runbook
                runbook = Runbook(
                    tenant_id=target_tenant_id,
                    title=rb_data["title"],
                    body_md=rb_data["body_md"],
                    meta_data=rb_data.get("meta_data"),
                    confidence=rb_data.get("confidence"),
                    status=rb_data.get("status", "approved"),  # Default to approved when importing
                    is_active=rb_data.get("is_active", "active"),
                )
                
                db.add(runbook)
                db.commit()
                db.refresh(runbook)
                
                logger.info(f"✅ Imported runbook: {rb_data['title']} (ID: {runbook.id})")
                imported += 1
                
            except Exception as e:
                logger.error(f"Error importing runbook {rb_data.get('title', 'unknown')}: {e}")
                db.rollback()
                errors += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Import complete!")
        print(f"{'='*60}")
        print(f"Imported: {imported}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error importing runbooks: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import runbooks into a tenant")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--target-tenant-id", type=int, required=True, help="Target tenant ID")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip runbooks with existing titles")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(import_runbooks(
            input_path=args.input,
            target_tenant_id=args.target_tenant_id,
            skip_existing=args.skip_existing
        ))
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

