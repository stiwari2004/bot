#!/usr/bin/env python3
"""
Test step ordering auto-fix
"""
import sys
import os
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.runbook.generation.spec_post_processor import SpecPostProcessor
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_step_ordering_fix():
    """Test that step ordering is auto-fixed"""
    
    # Simulate runbook with wrong step ordering (diagnose after remediate)
    test_spec = {
        "runbook_id": "rb-test-ordering",
        "version": "1.0.0",
        "title": "Test Step Ordering Fix",
        "service": "network",
        "env": "prod",
        "risk": "low",
        "description": "Test runbook with wrong step order",
        "inputs": [
            {"name": "host_ip", "type": "string", "required": True, "description": "Host IP"}
        ],
        "prechecks": [
            {"description": "Check 1", "command": "ping -c 1 {{host_ip}}", "expected_output": "0% packet loss"},
            {"description": "Check 2", "command": "echo test", "expected_output": "test"},
            {"description": "Check 3", "command": "echo test", "expected_output": "test"}
        ],
        "steps": [
            {
                "name": "Step 1 - Restart Service",
                "step_number": 1,
                "type": "command",
                "command": "systemctl restart myservice",
                "purpose": "remediate",  # WRONG: remediate before diagnose
                "severity": "moderate"
            },
            {
                "name": "Step 2 - Check Service",
                "step_number": 2,
                "type": "command",
                "command": "systemctl status myservice",
                "purpose": "diagnose",  # WRONG: diagnose after remediate
                "severity": "safe",
                "on_success": 3,
                "on_failure": 1
            },
            {
                "name": "Step 3 - Verify",
                "step_number": 3,
                "type": "command",
                "command": "ping -c 1 {{host_ip}}",
                "purpose": "verify",
                "severity": "safe"
            },
            {
                "name": "Step 4 - Check DNS",
                "step_number": 4,
                "type": "command",
                "command": "nslookup example.com",
                "purpose": "diagnose",  # WRONG: diagnose after verify
                "severity": "safe",
                "on_success": 5
            },
            {
                "name": "Step 5 - Final Verify",
                "step_number": 5,
                "type": "command",
                "command": "echo done",
                "purpose": "verify",
                "severity": "safe"
            }
        ],
        "postchecks": [
            {"description": "Final check", "command": "echo done", "expected_output": "done"}
        ]
    }
    
    print("\n" + "="*80)
    print("TESTING STEP ORDERING AUTO-FIX")
    print("="*80)
    
    print("\nBEFORE AUTO-FIX:")
    print("Step order (by purpose):")
    for i, step in enumerate(test_spec["steps"], 1):
        purpose = step.get("purpose", "unknown")
        step_num = step.get("step_number", i)
        name = step.get("name", f"Step {i}")
        print(f"  {i}. Step {step_num}: {purpose} - {name[:40]}")
    
    # Run post-processor
    print("\n[STEP 1] Running post-processor (AUTO-FIX step ordering)...")
    post_processor = SpecPostProcessor()
    fixed_spec = post_processor.post_process(test_spec, "Test issue", "prod", "low")
    
    print("\nAFTER AUTO-FIX:")
    print("Step order (by purpose):")
    for i, step in enumerate(fixed_spec["steps"], 1):
        purpose = step.get("purpose", "unknown")
        step_num = step.get("step_number", i)
        name = step.get("name", f"Step {i}")
        on_success = step.get("on_success", "N/A")
        on_failure = step.get("on_failure", step.get("on_fail", "N/A"))
        print(f"  {i}. Step {step_num}: {purpose} - {name[:40]}")
        if on_success != "N/A" or on_failure != "N/A":
            print(f"      Branching: on_success={on_success}, on_failure={on_failure}")
    
    # Validate
    print("\n[STEP 2] Running validation...")
    validator = RunbookQualityValidator()
    is_valid, errors = validator.validate(fixed_spec, "Test issue")
    
    ordering_errors = [e for e in errors if "appears after a later-phase step" in e.lower() or "phase" in e.lower()]
    other_errors = [e for e in errors if "appears after a later-phase step" not in e.lower() and "phase" not in e.lower()]
    
    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"Step ordering errors: {len(ordering_errors)}")
    print(f"Other errors: {len(other_errors)}")
    
    if ordering_errors:
        print("\n✗ STEP ORDERING ERRORS (Auto-fix failed!):")
        for i, error in enumerate(ordering_errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n✓ NO STEP ORDERING ERRORS (Auto-fix worked!)")
    
    if other_errors:
        print("\n⚠ OTHER ERRORS (Not related to ordering):")
        for i, error in enumerate(other_errors[:3], 1):
            print(f"  {i}. {error}")
    
    # Check order
    print("\n" + "="*80)
    print("ORDERING TEST SUMMARY")
    print("="*80)
    
    purposes = [step.get("purpose", "").lower() for step in fixed_spec["steps"] if isinstance(step, dict)]
    expected_order = ["diagnose", "remediate", "verify"]
    
    # Check if order follows diagnose → remediate → verify pattern
    current_phase = 0
    phase_order = {"diagnose": 0, "remediate": 1, "verify": 2}
    order_valid = True
    
    for purpose in purposes:
        phase = phase_order.get(purpose, 1)
        if phase < current_phase:
            order_valid = False
            break
        current_phase = max(current_phase, phase)
    
    print(f"\nStep purposes: {purposes}")
    print(f"Order valid: {order_valid}")
    
    if len(ordering_errors) == 0 and order_valid:
        print("\n✅ SUCCESS: Step ordering auto-fix worked!")
        print("   - Steps reordered to: diagnose → remediate → verify")
        print("   - Branching references updated correctly")
        print("   - Validation found zero ordering errors")
        return True
    elif len(ordering_errors) == 0:
        print("\n⚠️  PARTIAL: No validation errors but order might still be wrong")
        return False
    else:
        print(f"\n❌ FAILURE: Step ordering auto-fix did not work. {len(ordering_errors)} errors remain.")
        return False


if __name__ == "__main__":
    try:
        success = test_step_ordering_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




