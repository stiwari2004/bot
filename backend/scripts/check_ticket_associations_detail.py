"""
Detailed check of ticket associations for specific tickets
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text

print("=" * 80)
print("DETAILED TICKET ASSOCIATION CHECK")
print("=" * 80)

with engine.connect() as conn:
    # Check tickets #2 and #3 specifically
    for ticket_id in [2, 3]:
        print(f"\n{'='*80}")
        print(f"TICKET #{ticket_id}")
        print(f"{'='*80}")
        
        result = conn.execute(text("""
            SELECT id, title, source, meta_data
            FROM tickets
            WHERE id = :ticket_id
        """), {"ticket_id": ticket_id})
        ticket = result.fetchone()
        
        if not ticket:
            print(f"   ✗ Ticket #{ticket_id} not found")
            continue
        
        t_id, t_title, t_source, t_meta = ticket
        print(f"   Title: {t_title}")
        print(f"   Source: {t_source}")
        
        if not t_meta:
            print(f"   ⚠ No metadata")
            continue
        
        if isinstance(t_meta, str):
            try:
                ticket_meta = json.loads(t_meta)
            except:
                print(f"   ✗ Failed to parse metadata JSON")
                continue
        else:
            ticket_meta = t_meta
        
        print(f"\n   Metadata keys: {list(ticket_meta.keys())}")
        
        # Check matched_runbooks
        matched_runbooks = ticket_meta.get("matched_runbooks", [])
        if matched_runbooks:
            print(f"\n   matched_runbooks: {len(matched_runbooks)} runbook(s)")
            for i, rb_ref in enumerate(matched_runbooks):
                if isinstance(rb_ref, dict):
                    rb_id = rb_ref.get("id")
                    rb_title = rb_ref.get("title", "N/A")
                    print(f"      [{i+1}] Runbook ID: {rb_id}, Title: {rb_title}")
                    
                    # Check if runbook exists and is active
                    rb_check = conn.execute(text("""
                        SELECT id, title, is_active
                        FROM runbooks
                        WHERE id = :rb_id
                    """), {"rb_id": rb_id})
                    rb_row = rb_check.fetchone()
                    
                    if not rb_row:
                        print(f"         ✗ Runbook NOT FOUND in database")
                    elif rb_row[2] != "active":
                        print(f"         ⚠ Runbook is ARCHIVED/DELETED (is_active: {rb_row[2]})")
                        print(f"         ⚠ ORPHANED REFERENCE - should be removed!")
                    else:
                        print(f"         ✓ Runbook is ACTIVE")
        else:
            print(f"\n   matched_runbooks: None or empty")
        
        # Check runbook_id field
        runbook_id = ticket_meta.get("runbook_id")
        if runbook_id:
            print(f"\n   runbook_id field: {runbook_id}")
            rb_check = conn.execute(text("""
                SELECT id, title, is_active
                FROM runbooks
                WHERE id = :rb_id
            """), {"rb_id": runbook_id})
            rb_row = rb_check.fetchone()
            
            if not rb_row:
                print(f"      ✗ Runbook NOT FOUND in database")
            elif rb_row[2] != "active":
                print(f"      ⚠ Runbook is ARCHIVED/DELETED (is_active: {rb_row[2]})")
                print(f"      ⚠ ORPHANED REFERENCE - should be removed!")
            else:
                print(f"      ✓ Runbook is ACTIVE")
        else:
            print(f"\n   runbook_id field: None")
        
        # Check for other runbook references
        for key in ticket_meta.keys():
            if "runbook" in key.lower() and key not in ["matched_runbooks", "runbook_id"]:
                print(f"\n   Other runbook field '{key}': {ticket_meta[key]}")
    
    # Check runbooks 33, 38, 41 to see what tickets they reference
    print(f"\n{'='*80}")
    print("CHECKING RUNBOOKS 33, 38, 41 METADATA")
    print(f"{'='*80}")
    
    for rb_id in [33, 38, 41]:
        result = conn.execute(text("""
            SELECT id, title, meta_data, is_active
            FROM runbooks
            WHERE id = :rb_id
        """), {"rb_id": rb_id})
        rb = result.fetchone()
        
        if not rb:
            print(f"\n   Runbook #{rb_id}: NOT FOUND")
            continue
        
        rb_id_val, title, meta_data, is_active = rb
        print(f"\n   Runbook #{rb_id_val}: {title}")
        print(f"   Status: {'ARCHIVED' if is_active != 'active' else 'ACTIVE'}")
        
        if meta_data:
            if isinstance(meta_data, str):
                try:
                    rb_meta = json.loads(meta_data)
                except:
                    print(f"      ✗ Failed to parse metadata")
                    continue
            else:
                rb_meta = meta_data
            
            ticket_id = rb_meta.get("ticket_id")
            if ticket_id:
                print(f"      → References ticket #{ticket_id} in metadata")
                
                # Check if ticket still references this runbook
                t_check = conn.execute(text("""
                    SELECT id, meta_data
                    FROM tickets
                    WHERE id = :ticket_id
                """), {"ticket_id": ticket_id})
                t_row = t_check.fetchone()
                
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
                                if isinstance(rb_ref, dict) and rb_ref.get("id") == rb_id_val:
                                    has_ref = True
                                    print(f"      ⚠ Ticket #{ticket_id} STILL references this runbook in matched_runbooks!")
                        if runbook_id_field == rb_id_val:
                            has_ref = True
                            print(f"      ⚠ Ticket #{ticket_id} STILL references this runbook in runbook_id field!")
                        
                        if not has_ref:
                            print(f"      ✓ Ticket #{ticket_id} does NOT reference this runbook (cleanup worked)")
    
    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)




