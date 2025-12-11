#!/usr/bin/env python3
"""
Export runbooks from a tenant for migration/sharing
Usage: python scripts/export_runbooks.py --tenant-id 1 --status approved --output /app/exports/runbooks.json
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.runbook import Runbook
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def export_runbooks(tenant_id: int, status: str = None, output_path: str = None):
    """Export runbooks from a tenant"""
    await init_db()
    db: Session = SessionLocal()
    
    try:
        # Build query
        query = db.query(Runbook).filter(Runbook.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Runbook.status == status)
        
        runbooks = query.all()
        
        logger.info(f"Found {len(runbooks)} runbooks to export")
        
        # Export data
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "status_filter": status,
            "count": len(runbooks),
            "runbooks": []
        }
        
        for runbook in runbooks:
            runbook_data = {
                "id": runbook.id,
                "title": runbook.title,
                "body_md": runbook.body_md,
                "meta_data": runbook.meta_data,
                "confidence": float(runbook.confidence) if runbook.confidence else None,
                "status": runbook.status,
                "is_active": runbook.is_active,
                "created_at": runbook.created_at.isoformat() if runbook.created_at else None,
                "updated_at": runbook.updated_at.isoformat() if runbook.updated_at else None,
            }
            export_data["runbooks"].append(runbook_data)
        
        # Write to file
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"✅ Exported {len(runbooks)} runbooks to {output_path}")
        else:
            # Print to stdout
            print(json.dumps(export_data, indent=2))
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting runbooks: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export runbooks from a tenant")
    parser.add_argument("--tenant-id", type=int, required=True, help="Tenant ID to export from")
    parser.add_argument("--status", help="Filter by status (draft, approved, archived)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(export_runbooks(
            tenant_id=args.tenant_id,
            status=args.status,
            output_path=args.output
        ))
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

