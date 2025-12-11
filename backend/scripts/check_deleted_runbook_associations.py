"""
Check for deleted runbook associations that weren't cleaned up
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text

print("=" * 80)
print("CHECKING DELETED RUNBOOK ASSOCIATIONS")
print("=" * 80)

with engine.connect() as conn:
    # Search for runbook with title containing "Fix VPN Connection Issue"
    result = conn.execute(text("""
        SELECT id, title, meta_data, created_at, is_active
        FROM runbooks
        WHERE title ILIKE '%Fix VPN Connection Issue%'
        ORDER BY created_at DESC
    """))
    runbooks = result.fetchall()
    
    if not runbooks:
        print("\n⚠ No runbook found with title 'Fix VPN Connection Issue'")
        print("   (It may have been deleted)")
    else:
        print(f"\n✓ Found {len(runbooks)} runbook(s) with matching title:")
        for rb in runbooks:
            rb_id, title, meta_data, created_at, is_active = rb
            status = "ARCHIVED/DELETED" if is_active != "active" else "ACTIVE"
            print(f"\n   Runbook ID: {rb_id}")
            print(f"   Title: {title}")
            print(f"   Status: {status} (is_active: {is_active})")
            print(f"   Created: {created_at}")
            
            # Check metadata for ticket association
            if meta_data:
                if isinstance(meta_data, str):
                    meta = json.loads(meta_data)
                else:
                    meta = meta_data
                
                ticket_id = meta.get("ticket_id")
                if ticket_id:
                    print(f"   ⚠ Associated with ticket #{ticket_id} in metadata")
    
    # Check all tickets for references to deleted runbooks
    print("\n" + "=" * 80)
    print("CHECKING TICKETS FOR ORPHANED RUNBOOK REFERENCES")
    print("=" * 80)
    
    # Get all tickets with meta_data
    ticket_result = conn.execute(text("""
        SELECT id, title, source, meta_data
        FROM tickets
        WHERE meta_data IS NOT NULL
        ORDER BY id DESC
        LIMIT 50
    """))
    tickets = ticket_result.fetchall()
    
    orphaned_refs = []
    for ticket in tickets:
        t_id, t_title, t_source, t_meta = ticket
        if not t_meta:
            continue
        
        if isinstance(t_meta, str):
            try:
                ticket_meta = json.loads(t_meta)
            except:
                continue
        else:
            ticket_meta = t_meta
        
        # Check for matched_runbooks
        matched_runbooks = ticket_meta.get("matched_runbooks", [])
        if isinstance(matched_runbooks, list):
            for rb_ref in matched_runbooks:
                if isinstance(rb_ref, dict):
                    rb_id = rb_ref.get("id")
                    if rb_id:
                        # Check if runbook exists
                        rb_check = conn.execute(text("""
                            SELECT id, title, is_active
                            FROM runbooks
                            WHERE id = :rb_id
                        """), {"rb_id": rb_id})
                        rb_row = rb_check.fetchone()
                        
                        if not rb_row or (rb_row and rb_row[2] != "active"):  # Not found or archived/deleted
                            orphaned_refs.append({
                                "ticket_id": t_id,
                                "ticket_title": t_title,
                                "ticket_source": t_source,
                                "runbook_id": rb_id,
                                "runbook_title": rb_ref.get("title", "Unknown"),
                                "status": "ARCHIVED/DELETED" if rb_row and rb_row[2] != "active" else "NOT FOUND"
                            })
        
        # Check for runbook_id field
        runbook_id = ticket_meta.get("runbook_id")
        if runbook_id:
            rb_check = conn.execute(text("""
                SELECT id, title, is_active
                FROM runbooks
                WHERE id = :rb_id
            """), {"rb_id": runbook_id})
            rb_row = rb_check.fetchone()
            
            if not rb_row or (rb_row and rb_row[2] != "active"):  # Not found or archived/deleted
                orphaned_refs.append({
                    "ticket_id": t_id,
                    "ticket_title": t_title,
                    "ticket_source": t_source,
                    "runbook_id": runbook_id,
                    "runbook_title": "N/A",
                    "status": "ARCHIVED/DELETED" if rb_row and rb_row[2] != "active" else "NOT FOUND"
                })
    
    if orphaned_refs:
        print(f"\n⚠ Found {len(orphaned_refs)} orphaned runbook reference(s):")
        for ref in orphaned_refs:
            print(f"\n   Ticket #{ref['ticket_id']}: {ref['ticket_title']}")
            print(f"   Source: {ref['ticket_source']}")
            print(f"   References runbook #{ref['runbook_id']} ({ref['status']})")
            print(f"   Runbook title: {ref['runbook_title']}")
    else:
        print("\n✓ No orphaned references found")
    
    # Check for runbook with "VPN" in title that might be deleted
    print("\n" + "=" * 80)
    print("CHECKING ALL VPN-RELATED RUNBOOKS")
    print("=" * 80)
    
    vpn_result = conn.execute(text("""
        SELECT id, title, meta_data, is_active
        FROM runbooks
        WHERE title ILIKE '%VPN%' OR title ILIKE '%vpn%'
        ORDER BY created_at DESC
        LIMIT 10
    """))
    vpn_runbooks = vpn_result.fetchall()
    
    if vpn_runbooks:
        print(f"\nFound {len(vpn_runbooks)} VPN-related runbook(s):")
        for rb in vpn_runbooks:
            rb_id, title, meta_data, is_active = rb
            status = "ARCHIVED/DELETED" if is_active != "active" else "ACTIVE"
            print(f"\n   ID: {rb_id}, Title: {title}, Status: {status}")
            
            if meta_data:
                if isinstance(meta_data, str):
                    meta = json.loads(meta_data)
                else:
                    meta = meta_data
                ticket_id = meta.get("ticket_id")
                if ticket_id:
                    print(f"      → Associated with ticket #{ticket_id}")
                    
                    # Check if ticket still references this runbook
                    ticket_check = conn.execute(text("""
                        SELECT id, meta_data
                        FROM tickets
                        WHERE id = :ticket_id
                    """), {"ticket_id": ticket_id})
                    t_row = ticket_check.fetchone()
                    
                    if t_row:
                        t_id, t_meta = t_row
                        if t_meta:
                            if isinstance(t_meta, str):
                                t_meta_dict = json.loads(t_meta)
                            else:
                                t_meta_dict = t_meta
                            
                            matched = t_meta_dict.get("matched_runbooks", [])
                            runbook_id_field = t_meta_dict.get("runbook_id")
                            
                            has_ref = False
                            if isinstance(matched, list):
                                for rb_ref in matched:
                                    if isinstance(rb_ref, dict) and rb_ref.get("id") == rb_id:
                                        has_ref = True
                                        print(f"      ⚠ Ticket #{ticket_id} STILL references this runbook in matched_runbooks!")
                            if runbook_id_field == rb_id:
                                has_ref = True
                                print(f"      ⚠ Ticket #{ticket_id} STILL references this runbook in runbook_id field!")
                            
                            if not has_ref and is_active != "active":
                                print(f"      ✓ Ticket #{ticket_id} does NOT reference this deleted runbook (clean)")
    
    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)

