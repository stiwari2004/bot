"""
Fix orphaned runbook references using direct SQL
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text

print("=" * 80)
print("FIXING ORPHANED RUNBOOK REFERENCES (SQL)")
print("=" * 80)

with engine.begin() as conn:  # Use begin() for transaction
    # Get all archived runbooks
    archived_result = conn.execute(text("""
        SELECT id, tenant_id, title
        FROM runbooks
        WHERE is_active != 'active'
    """))
    archived_runbooks = archived_result.fetchall()
    
    print(f"\nFound {len(archived_runbooks)} archived/deleted runbook(s)")
    
    total_cleaned = 0
    
    for rb_id, tenant_id, title in archived_runbooks:
        print(f"\nCleaning up references to runbook #{rb_id}: {title}")
        
        # Get all tickets for this tenant
        tickets_result = conn.execute(text("""
            SELECT id, meta_data
            FROM tickets
            WHERE tenant_id = :tenant_id
            AND meta_data IS NOT NULL
        """), {"tenant_id": tenant_id})
        tickets = tickets_result.fetchall()
        
        cleaned_count = 0
        
        for ticket_id, meta_data in tickets:
            if not meta_data:
                continue
            
            # Parse metadata
            if isinstance(meta_data, str):
                try:
                    ticket_meta = json.loads(meta_data)
                except:
                    continue
            else:
                ticket_meta = dict(meta_data)
            
            updated = False
            
            # Remove from matched_runbooks
            if "matched_runbooks" in ticket_meta:
                if isinstance(ticket_meta["matched_runbooks"], list):
                    original_count = len(ticket_meta["matched_runbooks"])
                    ticket_meta["matched_runbooks"] = [
                        rb for rb in ticket_meta["matched_runbooks"]
                        if isinstance(rb, dict) and rb.get("id") != rb_id
                    ]
                    if len(ticket_meta["matched_runbooks"]) < original_count:
                        updated = True
            
            # Remove from runbook_id field
            if "runbook_id" in ticket_meta and ticket_meta["runbook_id"] == rb_id:
                del ticket_meta["runbook_id"]
                updated = True
            
            if updated:
                # Update ticket metadata
                conn.execute(text("""
                    UPDATE tickets
                    SET meta_data = :meta_data
                    WHERE id = :ticket_id
                """), {
                    "meta_data": json.dumps(ticket_meta),
                    "ticket_id": ticket_id
                })
                cleaned_count += 1
        
        if cleaned_count > 0:
            print(f"  ✓ Cleaned up {cleaned_count} ticket reference(s)")
            total_cleaned += cleaned_count
        else:
            print(f"  ✓ No references found (already clean)")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: Cleaned up {total_cleaned} orphaned reference(s)")
    print(f"{'='*80}")
    
    # Verify cleanup
    print(f"\nVerifying cleanup...")
    verify_result = conn.execute(text("""
        SELECT t.id, t.meta_data
        FROM tickets t
        WHERE t.meta_data IS NOT NULL
    """))
    tickets = verify_result.fetchall()
    
    orphaned_count = 0
    for ticket_id, meta_data in tickets:
        if not meta_data:
            continue
        
        if isinstance(meta_data, str):
            try:
                ticket_meta = json.loads(meta_data)
            except:
                continue
        else:
            ticket_meta = dict(meta_data)
        
        # Check matched_runbooks
        matched_runbooks = ticket_meta.get("matched_runbooks", [])
        if isinstance(matched_runbooks, list):
            for rb_ref in matched_runbooks:
                if isinstance(rb_ref, dict):
                    rb_id = rb_ref.get("id")
                    if rb_id:
                        rb_check = conn.execute(text("""
                            SELECT id, is_active
                            FROM runbooks
                            WHERE id = :rb_id
                        """), {"rb_id": rb_id})
                        rb_row = rb_check.fetchone()
                        if not rb_row or (rb_row and rb_row[1] != "active"):
                            orphaned_count += 1
                            print(f"  ⚠ Ticket #{ticket_id} still references archived runbook #{rb_id}")
        
        # Check runbook_id field
        runbook_id = ticket_meta.get("runbook_id")
        if runbook_id:
            rb_check = conn.execute(text("""
                SELECT id, is_active
                FROM runbooks
                WHERE id = :rb_id
            """), {"rb_id": runbook_id})
            rb_row = rb_check.fetchone()
            if not rb_row or (rb_row and rb_row[1] != "active"):
                orphaned_count += 1
                print(f"  ⚠ Ticket #{ticket_id} still references archived runbook #{runbook_id} in runbook_id field")
    
    if orphaned_count == 0:
        print(f"\n✓ Verification complete: No orphaned references found!")
    else:
        print(f"\n⚠ Verification found {orphaned_count} remaining orphaned reference(s)")
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)




