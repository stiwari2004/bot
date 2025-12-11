"""
Simple check for runbook #45 - direct SQL query to avoid relationship issues
"""
import sys
import os
import yaml
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text

print("=" * 80)
print("CHECKING RUNBOOK #45 AND 360-DEGREE INPUT EXTRACTION")
print("=" * 80)

with engine.connect() as conn:
    # Get runbook 45
    result = conn.execute(text("""
        SELECT id, title, body_md, meta_data, created_at, tenant_id
        FROM runbooks
        WHERE id = 45
    """))
    runbook_row = result.fetchone()
    
    if not runbook_row:
        print("✗ Runbook #45 not found in database")
        sys.exit(1)
    
    runbook_id, title, body_md, meta_data, created_at, tenant_id = runbook_row
    print(f"\n✓ Runbook #45 found: {title}")
    print(f"  Created: {created_at}")
    print(f"  Tenant ID: {tenant_id}")
    
    # Parse runbook YAML
    try:
        runbook_yaml = body_md
        # Extract YAML from markdown if needed
        if "```yaml" in runbook_yaml:
            import re
            yaml_match = re.search(r'```yaml\n(.*?)\n```', runbook_yaml, re.DOTALL)
            if yaml_match:
                runbook_yaml = yaml_match.group(1)
        
        spec = yaml.safe_load(runbook_yaml)
        print(f"\n✓ Runbook YAML parsed successfully")
        
        # Check inputs
        inputs = spec.get("inputs", [])
        print(f"\n1. INPUTS SECTION:")
        print(f"   Total inputs: {len(inputs)}")
        required_inputs = []
        for inp in inputs:
            if isinstance(inp, dict):
                name = inp.get("name", "unknown")
                required = inp.get("required", False)
                default = inp.get("default", "N/A")
                print(f"   - {name} (required={required}, default={default})")
                if required:
                    required_inputs.append(name)
        
        # Check metadata
        print(f"\n2. RUNBOOK METADATA:")
        if meta_data:
            if isinstance(meta_data, str):
                meta = json.loads(meta_data)
            else:
                meta = meta_data
            print(f"   Meta keys: {list(meta.keys())}")
            
            # Check for extraction-related metadata
            if "extracted_inputs" in meta:
                print(f"   ✓ Extracted inputs found in metadata!")
                print(f"     {meta['extracted_inputs']}")
            else:
                print(f"   ⚠ No extracted_inputs in metadata")
            
            # Check ticket_id
            if "ticket_id" in meta:
                ticket_id = meta["ticket_id"]
                print(f"   ✓ Associated with ticket #{ticket_id}")
        else:
            print(f"   ⚠ No metadata found")
        
        # Check associated ticket
        if meta_data:
            meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
            ticket_id = meta.get("ticket_id")
            
            if ticket_id:
                print(f"\n3. CHECKING TICKET #{ticket_id}:")
                ticket_result = conn.execute(text("""
                    SELECT id, source, title, description, meta_data, raw_payload
                    FROM tickets
                    WHERE id = :ticket_id
                """), {"ticket_id": ticket_id})
                ticket_row = ticket_result.fetchone()
                
                if ticket_row:
                    t_id, t_source, t_title, t_desc, t_meta, t_raw = ticket_row
                    print(f"   ✓ Ticket found: {t_title}")
                    print(f"   Source: {t_source}")
                    
                    # Check ticket metadata for extracted inputs
                    if t_meta:
                        if isinstance(t_meta, str):
                            ticket_meta = json.loads(t_meta)
                        else:
                            ticket_meta = t_meta
                        
                        if "extracted_inputs" in ticket_meta:
                            print(f"\n   ✓ Extracted inputs stored in ticket metadata!")
                            print(f"     {ticket_meta['extracted_inputs']}")
                        else:
                            print(f"\n   ⚠ No extracted_inputs in ticket metadata")
                            print(f"     (This means extraction hasn't run yet for this ticket)")
                    
                    # Try extraction now
                    print(f"\n4. TESTING INPUT EXTRACTION:")
                    try:
                        from app.services.runbook.input_extractor import RunbookInputExtractor
                        from app.models.runbook import Runbook
                        from app.models.ticket import Ticket
                        from app.core.database import SessionLocal
                        import asyncio
                        
                        db = SessionLocal()
                        try:
                            ticket_obj = db.query(Ticket).filter(Ticket.id == ticket_id).first()
                            runbook_obj = db.query(Runbook).filter(Runbook.id == 45).first()
                            
                            if ticket_obj and runbook_obj:
                                extractor = RunbookInputExtractor()
                                result = asyncio.run(extractor.extract_inputs(ticket_obj, runbook_obj, db))
                                
                                print(f"   ✓ Extraction completed")
                                print(f"     Extracted: {len(result.get('extracted', {}))} inputs")
                                print(f"     Missing: {len(result.get('missing', []))} inputs")
                                
                                if result.get('extracted'):
                                    print(f"\n   Extracted inputs:")
                                    for key, value in result.get('extracted', {}).items():
                                        confidence = result.get('confidence', {}).get(key, 0.0)
                                        print(f"     - {key}: {value} (confidence: {confidence:.2f})")
                                
                                if result.get('missing'):
                                    print(f"\n   Missing inputs:")
                                    for inp in result.get('missing', []):
                                        print(f"     - {inp}")
                                else:
                                    print(f"\n   ✓ All required inputs extracted!")
                            else:
                                print(f"   ⚠ Could not load ticket/runbook objects")
                        finally:
                            db.close()
                    except Exception as e:
                        print(f"   ✗ Extraction test failed: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"   ✗ Ticket #{ticket_id} not found")
        
        # Check for learned mappings
        print(f"\n5. LEARNED MAPPINGS:")
        mapping_result = conn.execute(text("""
            SELECT input_name, source, metadata_path, confidence, usage_count, is_active
            FROM metadata_mappings
            WHERE is_active = TRUE
            ORDER BY usage_count DESC
            LIMIT 10
        """))
        mappings = mapping_result.fetchall()
        if mappings:
            print(f"   ✓ Found {len(mappings)} active mapping(s):")
            for mapping in mappings:
                input_name, source, metadata_path, confidence, usage_count, is_active = mapping
                print(f"     - {input_name} -> {metadata_path} "
                      f"(source: {source}, confidence: {confidence:.2f}, "
                      f"usage: {usage_count})")
        else:
            print(f"   ⚠ No learned mappings found yet")
            print(f"     (This is normal if no user input has been provided yet)")
        
        # Check for mapping flags
        print(f"\n6. MAPPING FLAGS (Low Confidence):")
        flag_result = conn.execute(text("""
            SELECT input_name, metadata_path, confidence, usage_count
            FROM metadata_mappings
            WHERE confidence < 0.8 AND is_active = TRUE
            ORDER BY confidence ASC
        """))
        flags = flag_result.fetchall()
        if flags:
            print(f"   ⚠ Found {len(flags)} flag(s) for review:")
            for flag in flags:
                input_name, metadata_path, confidence, usage_count = flag
                print(f"     - {input_name} -> {metadata_path} "
                      f"(confidence: {confidence:.2f}, usage: {usage_count})")
        else:
            print(f"   ✓ No flags (all mappings have high confidence)")
        
        # Check runbook structure
        print(f"\n7. RUNBOOK STRUCTURE:")
        prechecks = spec.get("prechecks", [])
        steps = spec.get("steps", [])
        postchecks = spec.get("postchecks", [])
        print(f"   Prechecks: {len(prechecks)}")
        print(f"   Steps: {len(steps)}")
        print(f"   Postchecks: {len(postchecks)}")
        
        # Check step purposes
        if steps:
            purposes = {}
            for step in steps:
                if isinstance(step, dict):
                    purpose = step.get("purpose", "unknown")
                    purposes[purpose] = purposes.get(purpose, 0) + 1
            print(f"   Step purposes: {purposes}")
        
        # Check if auto-fixes were applied
        print(f"\n8. AUTO-FIX STATUS:")
        if meta_data:
            meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
            if "generated_by" in meta:
                print(f"   Generation mode: {meta.get('generated_by')}")
            if "critique_issues" in meta:
                print(f"   ⚠ Critique issues found: {len(meta.get('critique_issues', []))}")
            if "critique_warnings" in meta:
                print(f"   ⚠ Critique warnings: {len(meta.get('critique_warnings', []))}")
        
        print("\n" + "=" * 80)
        print("CHECK COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error parsing runbook: {e}")
        import traceback
        traceback.print_exc()




