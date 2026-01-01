#!/usr/bin/env python3
"""
Batch script to promote approved runbooks from dev to production
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.services.runbook_promotion_service import get_runbook_promotion_service
from app.models.runbook import Runbook


def sync_approved_runbooks(tenant_id: int = 1, approved_by: int = 1, dry_run: bool = False):
    """Promote all approved dev runbooks that haven't been promoted yet"""
    db = SessionLocal()
    try:
        # Get all approved dev runbooks
        approved_dev_runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == tenant_id,
            Runbook.environment == "dev",
            Runbook.status == "approved"
        ).all()
        
        print(f"Found {len(approved_dev_runbooks)} approved dev runbooks")
        
        promotion_service = get_runbook_promotion_service()
        results = []
        
        for runbook in approved_dev_runbooks:
            # Check if already promoted
            existing_prod = db.query(Runbook).filter(
                Runbook.promoted_from_id == runbook.id,
                Runbook.environment == "production"
            ).first()
            
            if existing_prod:
                print(f"  ⏭  Runbook {runbook.id} ({runbook.title[:50]}...) already promoted as {existing_prod.id}")
                results.append({"id": runbook.id, "status": "already_promoted", "prod_id": existing_prod.id})
                continue
            
            # Validate
            is_valid, error_msg = promotion_service.validate_runbook_for_promotion(
                db, runbook.id, tenant_id
            )
            
            if not is_valid:
                print(f"  ✗  Runbook {runbook.id} ({runbook.title[:50]}...) invalid: {error_msg}")
                results.append({"id": runbook.id, "status": "invalid", "error": error_msg})
                continue
            
            if dry_run:
                print(f"  ✓  Runbook {runbook.id} ({runbook.title[:50]}...) would be promoted")
                results.append({"id": runbook.id, "status": "would_promote"})
                continue
            
            # Promote
            print(f"  →  Promoting runbook {runbook.id} ({runbook.title[:50]}...)...")
            prod_runbook, error_msg = promotion_service.promote_runbook(
                db=db,
                dev_runbook_id=runbook.id,
                tenant_id=tenant_id,
                approved_by=approved_by,
                dry_run=False
            )
            
            if error_msg:
                print(f"  ✗  Failed: {error_msg}")
                results.append({"id": runbook.id, "status": "failed", "error": error_msg})
            else:
                print(f"  ✓  Promoted as {prod_runbook.id}")
                results.append({"id": runbook.id, "status": "promoted", "prod_id": prod_runbook.id})
        
        # Summary
        print("\n" + "="*60)
        print("Summary:")
        promoted = len([r for r in results if r["status"] == "promoted"])
        already_promoted = len([r for r in results if r["status"] == "already_promoted"])
        invalid = len([r for r in results if r["status"] == "invalid"])
        failed = len([r for r in results if r["status"] == "failed"])
        would_promote = len([r for r in results if r["status"] == "would_promote"])
        
        if dry_run:
            print(f"  Would promote: {would_promote}")
        else:
            print(f"  Promoted: {promoted}")
        print(f"  Already promoted: {already_promoted}")
        print(f"  Invalid: {invalid}")
        print(f"  Failed: {failed}")
        print("="*60)
        
        return 0 if (promoted > 0 or would_promote > 0) and failed == 0 else 1
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync approved runbooks from dev to production")
    parser.add_argument("--tenant-id", type=int, default=1, help="Tenant ID (default: 1)")
    parser.add_argument("--approved-by", type=int, default=1, help="User ID who approved (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be promoted without actually promoting")
    
    args = parser.parse_args()
    
    exit_code = sync_approved_runbooks(
        args.tenant_id,
        args.approved_by,
        args.dry_run
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

