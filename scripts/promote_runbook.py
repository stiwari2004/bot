#!/usr/bin/env python3
"""
CLI tool for promoting runbooks from dev to production
"""
import sys
import os
import argparse
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.services.runbook_promotion_service import get_runbook_promotion_service
from app.models.runbook import Runbook


def promote_runbook(dev_runbook_id: int, tenant_id: int, approved_by: int = 1, dry_run: bool = False):
    """Promote a runbook from dev to production"""
    db = SessionLocal()
    try:
        promotion_service = get_runbook_promotion_service()
        
        if dry_run:
            print(f"Dry run: Validating runbook {dev_runbook_id}...")
            is_valid, error_msg = promotion_service.validate_runbook_for_promotion(
                db, dev_runbook_id, tenant_id
            )
            if is_valid:
                print(f"✓ Runbook {dev_runbook_id} is valid for promotion")
                return 0
            else:
                print(f"✗ Runbook {dev_runbook_id} is NOT valid: {error_msg}")
                return 1
        
        print(f"Promoting runbook {dev_runbook_id} to production...")
        prod_runbook, error_msg = promotion_service.promote_runbook(
            db=db,
            dev_runbook_id=dev_runbook_id,
            tenant_id=tenant_id,
            approved_by=approved_by,
            dry_run=False
        )
        
        if error_msg:
            print(f"✗ Promotion failed: {error_msg}")
            return 1
        
        print(f"✓ Successfully promoted runbook {dev_runbook_id} to production as {prod_runbook.id}")
        print(f"  Production runbook ID: {prod_runbook.id}")
        print(f"  Promoted at: {prod_runbook.promoted_at}")
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Promote runbook from dev to production")
    parser.add_argument("runbook_id", type=int, help="Dev runbook ID to promote")
    parser.add_argument("--tenant-id", type=int, default=1, help="Tenant ID (default: 1)")
    parser.add_argument("--approved-by", type=int, default=1, help="User ID who approved (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Validate but don't promote")
    
    args = parser.parse_args()
    
    exit_code = promote_runbook(
        args.runbook_id,
        args.tenant_id,
        args.approved_by,
        args.dry_run
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

