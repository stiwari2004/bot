"""
Fix orphaned runbook references in tickets
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.services.runbook.ticket_cleanup_service import TicketCleanupService
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from sqlalchemy.orm.attributes import flag_modified

print("=" * 80)
print("FIXING ORPHANED RUNBOOK REFERENCES")
print("=" * 80)

db = SessionLocal()
cleanup_service = TicketCleanupService()

try:
    # Find all archived/deleted runbooks
    archived_runbooks = db.query(Runbook).filter(
        Runbook.is_active != "active"
    ).all()
    
    print(f"\nFound {len(archived_runbooks)} archived/deleted runbook(s)")
    
    total_cleaned = 0
    for runbook in archived_runbooks:
        print(f"\nCleaning up references to runbook #{runbook.id}: {runbook.title}")
        cleaned = cleanup_service.cleanup_runbook_references(
            db,
            runbook.id,
            runbook.tenant_id
        )
        if cleaned > 0:
            print(f"  ✓ Cleaned up {cleaned} ticket reference(s)")
            total_cleaned += cleaned
        else:
            print(f"  ✓ No references found (already clean)")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: Cleaned up {total_cleaned} orphaned reference(s)")
    print(f"{'='*80}")
    
    # Verify cleanup
    print(f"\nVerifying cleanup...")
    tickets = db.query(Ticket).filter(Ticket.meta_data.isnot(None)).all()
    orphaned_count = 0
    
    for ticket in tickets:
        if not ticket.meta_data:
            continue
        
        if isinstance(ticket.meta_data, str):
            try:
                ticket_meta = json.loads(ticket.meta_data)
            except:
                continue
        else:
            ticket_meta = ticket.meta_data
        
        # Check matched_runbooks
        matched_runbooks = ticket_meta.get("matched_runbooks", [])
        if isinstance(matched_runbooks, list):
            for rb_ref in matched_runbooks:
                if isinstance(rb_ref, dict):
                    rb_id = rb_ref.get("id")
                    if rb_id:
                        rb = db.query(Runbook).filter(Runbook.id == rb_id).first()
                        if not rb or rb.is_active != "active":
                            orphaned_count += 1
                            print(f"  ⚠ Ticket #{ticket.id} still references archived runbook #{rb_id}")
        
        # Check runbook_id field
        runbook_id = ticket_meta.get("runbook_id")
        if runbook_id:
            rb = db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if not rb or rb.is_active != "active":
                orphaned_count += 1
                print(f"  ⚠ Ticket #{ticket.id} still references archived runbook #{runbook_id} in runbook_id field")
    
    if orphaned_count == 0:
        print(f"\n✓ Verification complete: No orphaned references found!")
    else:
        print(f"\n⚠ Verification found {orphaned_count} remaining orphaned reference(s)")
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()




