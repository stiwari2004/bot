"""
Check runbook #45 and verify 360-degree input extraction system
"""
import sys
import os
import yaml
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
# Import all models first to ensure relationships are set up
from app.models import tenant, user, runbook, ticket, metadata_mapping
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.models.metadata_mapping import MetadataMapping
from app.services.runbook.input_extractor import RunbookInputExtractor
import asyncio

print("=" * 80)
print("CHECKING RUNBOOK #45 AND 360-DEGREE INPUT EXTRACTION")
print("=" * 80)

db = SessionLocal()

try:
    # Get runbook 45
    runbook = db.query(Runbook).filter(Runbook.id == 45).first()
    
    if not runbook:
        print("✗ Runbook #45 not found in database")
        sys.exit(1)
    
    print(f"\n✓ Runbook #45 found: {runbook.title}")
    print(f"  Created: {runbook.created_at}")
    print(f"  Service: {runbook.service if hasattr(runbook, 'service') else 'N/A'}")
    print(f"  Status: {runbook.status if hasattr(runbook, 'status') else 'N/A'}")
    
    # Parse runbook YAML
    try:
        runbook_yaml = runbook.body_md
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
        for inp in inputs:
            if isinstance(inp, dict):
                name = inp.get("name", "unknown")
                required = inp.get("required", False)
                default = inp.get("default", "N/A")
                print(f"   - {name} (required={required}, default={default})")
        
        # Check metadata
        print(f"\n2. RUNBOOK METADATA:")
        if runbook.meta_data:
            meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
            print(f"   Meta keys: {list(meta.keys())}")
            
            # Check for extraction-related metadata
            if "extracted_inputs" in meta:
                print(f"   ✓ Extracted inputs found in metadata!")
                print(f"     {meta['extracted_inputs']}")
            else:
                print(f"   ⚠ No extracted_inputs in metadata")
        else:
            print(f"   ⚠ No metadata found")
        
        # Check if runbook is associated with any tickets
        print(f"\n3. TICKET ASSOCIATIONS:")
        # Check tickets that might reference this runbook
        tickets = db.query(Ticket).all()
        associated_tickets = []
        for ticket in tickets:
            if ticket.meta_data:
                meta = ticket.meta_data if isinstance(ticket.meta_data, dict) else json.loads(ticket.meta_data)
                matched_runbooks = meta.get("matched_runbooks", [])
                if isinstance(matched_runbooks, list):
                    for rb in matched_runbooks:
                        if isinstance(rb, dict) and rb.get("id") == 45:
                            associated_tickets.append(ticket.id)
        
        if associated_tickets:
            print(f"   ✓ Found {len(associated_tickets)} associated ticket(s): {associated_tickets}")
            
            # Check extraction for first associated ticket
            if associated_tickets:
                ticket_id = associated_tickets[0]
                ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
                if ticket:
                    print(f"\n4. INPUT EXTRACTION FOR TICKET #{ticket_id}:")
                    print(f"   Ticket source: {ticket.source}")
                    print(f"   Ticket title: {ticket.title}")
                    
                    # Try extraction
                    extractor = RunbookInputExtractor()
                    try:
                        result = asyncio.run(extractor.extract_inputs(ticket, runbook, db))
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
                        
                        # Check if extraction result is stored in ticket metadata
                        if ticket.meta_data:
                            ticket_meta = ticket.meta_data if isinstance(ticket.meta_data, dict) else json.loads(ticket.meta_data)
                            if "extracted_inputs" in ticket_meta:
                                print(f"\n   ✓ Extracted inputs stored in ticket metadata")
                            else:
                                print(f"\n   ⚠ Extracted inputs NOT stored in ticket metadata")
                    except Exception as e:
                        print(f"   ✗ Extraction failed: {e}")
                        import traceback
                        traceback.print_exc()
        else:
            print(f"   ⚠ No associated tickets found")
        
        # Check for learned mappings
        print(f"\n5. LEARNED MAPPINGS:")
        mappings = db.query(MetadataMapping).filter(MetadataMapping.is_active == True).all()
        if mappings:
            print(f"   ✓ Found {len(mappings)} active mapping(s):")
            for mapping in mappings:
                print(f"     - {mapping.input_name} -> {mapping.metadata_path} "
                      f"(source: {mapping.source}, confidence: {mapping.confidence:.2f}, "
                      f"usage: {mapping.usage_count})")
        else:
            print(f"   ⚠ No learned mappings found yet")
        
        # Check for mapping flags
        print(f"\n6. MAPPING FLAGS (Low Confidence):")
        flags = db.query(MetadataMapping).filter(
            MetadataMapping.confidence < 0.8,
            MetadataMapping.is_active == True
        ).all()
        if flags:
            print(f"   ⚠ Found {len(flags)} flag(s) for review:")
            for flag in flags:
                print(f"     - {flag.input_name} -> {flag.metadata_path} "
                      f"(confidence: {flag.confidence:.2f})")
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
        
        print("\n" + "=" * 80)
        print("CHECK COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error parsing runbook: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

