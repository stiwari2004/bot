#!/usr/bin/env python3
"""
Check runbook #41 format and auto-fix status
"""
import sys
import os
import yaml
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.runbook import Runbook
from app.core.logging import get_logger

logger = get_logger(__name__)


def check_runbook_41():
    """Check runbook #41 format and structure"""
    
    db = SessionLocal()
    try:
        runbook = db.query(Runbook).filter(Runbook.id == 41).first()
        
        if not runbook:
            print("❌ Runbook #41 not found!")
            return False
        
        print("\n" + "="*80)
        print(f"RUNBOOK #41 ANALYSIS")
        print("="*80)
        print(f"\nID: {runbook.id}")
        print(f"Title: {runbook.title}")
        print(f"Service: {runbook.service}")
        print(f"Status: {runbook.status}")
        print(f"Body length: {len(runbook.body_md) if runbook.body_md else 0} chars")
        
        # Extract YAML from markdown
        yaml_match = re.search(r'```yaml\n(.*?)```', runbook.body_md, re.DOTALL)
        if not yaml_match:
            print("\n❌ No YAML found in body_md!")
            return False
        
        yaml_content = yaml_match.group(1).strip()
        spec = yaml.safe_load(yaml_content)
        
        # Check section order in YAML string
        print("\n" + "-"*80)
        print("SECTION ORDER CHECK (in YAML string)")
        print("-"*80)
        
        yaml_lines = yaml_content.split('\n')
        section_positions = {}
        for i, line in enumerate(yaml_lines, 1):
            stripped = line.strip()
            if stripped == "prechecks:":
                section_positions["prechecks"] = i
            elif stripped == "steps:":
                section_positions["steps"] = i
            elif stripped == "postchecks:":
                section_positions["postchecks"] = i
        
        print(f"Prechecks position: {section_positions.get('prechecks', 'NOT FOUND')}")
        print(f"Steps position: {section_positions.get('steps', 'NOT FOUND')}")
        print(f"Postchecks position: {section_positions.get('postchecks', 'NOT FOUND')}")
        
        # Check if order is correct
        order_correct = True
        if "prechecks" in section_positions and "steps" in section_positions:
            if section_positions["prechecks"] > section_positions["steps"]:
                order_correct = False
                print("❌ ERROR: prechecks comes AFTER steps!")
        if "steps" in section_positions and "postchecks" in section_positions:
            if section_positions["steps"] > section_positions["postchecks"]:
                order_correct = False
                print("❌ ERROR: steps comes AFTER postchecks!")
        
        if order_correct:
            print("✅ Section order is CORRECT: prechecks → steps → postchecks")
        else:
            print("❌ Section order is WRONG!")
        
        # Check structure
        print("\n" + "-"*80)
        print("STRUCTURE CHECK")
        print("-"*80)
        
        prechecks = spec.get("prechecks", [])
        steps = spec.get("steps", [])
        postchecks = spec.get("postchecks", [])
        inputs = spec.get("inputs", [])
        
        print(f"Inputs: {len(inputs)}")
        print(f"Prechecks: {len(prechecks)} (expected: 3)")
        print(f"Steps: {len(steps)}")
        print(f"Postchecks: {len(postchecks)} (expected: 1)")
        
        # Check if auto-fix worked (check for corrected purposes)
        print("\n" + "-"*80)
        print("AUTO-FIX STATUS CHECK")
        print("-"*80)
        
        # Check step purposes
        remediation_count = 0
        diagnose_count = 0
        verify_count = 0
        
        for step in steps:
            if isinstance(step, dict):
                purpose = step.get("purpose", "").lower()
                if purpose == "remediate":
                    remediation_count += 1
                elif purpose == "diagnose":
                    diagnose_count += 1
                elif purpose == "verify":
                    verify_count += 1
        
        print(f"Step purposes: {diagnose_count} diagnose, {remediation_count} remediate, {verify_count} verify")
        
        # Check if inputs are all defined
        all_commands = []
        for section in [prechecks, steps, postchecks]:
            for item in section:
                if isinstance(item, dict) and item.get("command"):
                    all_commands.append(item["command"])
        
        # Find all placeholders
        placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
        referenced_inputs = set()
        for cmd in all_commands:
            referenced_inputs.update(placeholder_pattern.findall(cmd))
        
        defined_inputs = {inp.get("name") for inp in inputs if isinstance(inp, dict)}
        missing_inputs = referenced_inputs - defined_inputs
        
        if missing_inputs:
            print(f"❌ Missing inputs: {sorted(missing_inputs)}")
        else:
            print(f"✅ All inputs defined: {sorted(defined_inputs)}")
        
        # Check step ordering (should be diagnose → remediate → verify)
        print("\n" + "-"*80)
        print("STEP ORDERING CHECK")
        print("-"*80)
        
        purposes_order = []
        for step in steps:
            if isinstance(step, dict):
                purposes_order.append(step.get("purpose", "unknown"))
        
        print(f"Step order by purpose: {' → '.join(purposes_order[:10])}{'...' if len(purposes_order) > 10 else ''}")
        
        phase_order = {"diagnose": 0, "remediate": 1, "verify": 2}
        current_phase = 0
        ordering_correct = True
        
        for purpose in purposes_order:
            phase = phase_order.get(purpose.lower(), 1)
            if phase < current_phase:
                ordering_correct = False
                break
            current_phase = max(current_phase, phase)
        
        if ordering_correct:
            print("✅ Step ordering is CORRECT: diagnose → remediate → verify")
        else:
            print("❌ Step ordering is WRONG (diagnose after remediate/verify)")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        all_good = (
            order_correct and
            len(prechecks) == 3 and
            len(postchecks) == 1 and
            len(missing_inputs) == 0 and
            ordering_correct and
            remediation_count >= 2
        )
        
        if all_good:
            print("✅ All checks passed! Runbook #41 is correctly formatted.")
        else:
            print("⚠️  Some issues found:")
            if not order_correct:
                print("  - Section order is wrong")
            if len(prechecks) != 3:
                print(f"  - Prechecks count: {len(prechecks)} (expected 3)")
            if len(postchecks) != 1:
                print(f"  - Postchecks count: {len(postchecks)} (expected 1)")
            if missing_inputs:
                print(f"  - Missing inputs: {sorted(missing_inputs)}")
            if not ordering_correct:
                print("  - Step ordering is wrong")
            if remediation_count < 2:
                print(f"  - Remediation steps: {remediation_count} (expected at least 2)")
        
        return all_good
        
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = check_runbook_41()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Check failed: {e}", exc_info=True)
        print(f"\n❌ CHECK FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




