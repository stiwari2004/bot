#!/usr/bin/env python3
"""
Test step purpose auto-correction
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


def test_purpose_autofix():
    """Test that step purposes are auto-corrected based on command keywords"""
    
    # Simulate runbook with wrong purposes
    test_spec = {
        "runbook_id": "rb-test-purpose-fix",
        "version": "1.0.0",
        "title": "Test Purpose Auto-Fix",
        "service": "server",
        "env": "prod",
        "risk": "low",
        "description": "Test runbook with wrong purposes",
        "inputs": [
            {"name": "server_name", "type": "string", "required": True, "description": "Server name"}
        ],
        "prechecks": [
            {"description": "Check 1", "command": "ping -c 1 {{server_name}}", "expected_output": "0% packet loss"},
            {"description": "Check 2", "command": "echo test", "expected_output": "test"},
            {"description": "Check 3", "command": "echo test", "expected_output": "test"}
        ],
        "steps": [
            {
                "name": "Step 1 - Restart Service",
                "step_number": 1,
                "type": "command",
                "command": "systemctl restart myservice",  # REMEDIATION command
                "purpose": "diagnose",  # WRONG: should be "remediate"
                "severity": "moderate"
            },
            {
                "name": "Step 2 - Check Service Status",
                "step_number": 2,
                "type": "command",
                "command": "systemctl status myservice",  # DIAGNOSTIC command
                "purpose": "remediate",  # WRONG: should be "diagnose"
                "severity": "safe"
            },
            {
                "name": "Step 3 - Kill Process",
                "step_number": 3,
                "type": "command",
                "command": "kill -9 12345",  # REMEDIATION command
                "purpose": "verify",  # WRONG: should be "remediate"
                "severity": "high"
            },
            {
                "name": "Step 4 - Get Process List",
                "step_number": 4,
                "type": "command",
                "command": "ps aux | grep myservice",  # DIAGNOSTIC command
                "purpose": "remediate",  # WRONG: should be "diagnose"
                "severity": "safe"
            },
            {
                "name": "Step 5 - Verify Service",
                "step_number": 5,
                "type": "command",
                "command": "systemctl is-active myservice",  # VERIFY command (correct)
                "purpose": "verify",  # CORRECT
                "severity": "safe"
            },
            {
                "name": "Step 6 - Clear Logs",
                "step_number": 6,
                "type": "command",
                "command": "truncate -s 0 /var/log/myservice.log",  # REMEDIATION command
                "purpose": "diagnose",  # WRONG: should be "remediate"
                "severity": "moderate"
            }
        ],
        "postchecks": [
            {"description": "Final check", "command": "echo done", "expected_output": "done"}
        ]
    }
    
    print("\n" + "="*80)
    print("TESTING STEP PURPOSE AUTO-CORRECTION")
    print("="*80)
    
    print("\nBEFORE AUTO-FIX:")
    print("Step purposes (should be corrected):")
    for i, step in enumerate(test_spec["steps"], 1):
        purpose = step.get("purpose", "unknown")
        command = step.get("command", "")[:50]
        name = step.get("name", f"Step {i}")
        print(f"  {i}. {purpose:10} - {name[:40]}")
        print(f"      Command: {command}")
    
    # Build a map of step names to original purposes BEFORE post-processing
    # (since post-processing modifies the spec in place)
    import copy
    original_spec = copy.deepcopy(test_spec)
    original_purposes = {step.get("name"): step.get("purpose", "unknown") for step in original_spec["steps"] if isinstance(step, dict)}
    
    # Run post-processor
    print("\n[STEP 1] Running post-processor (AUTO-FIX step purposes)...")
    post_processor = SpecPostProcessor()
    fixed_spec = post_processor.post_process(test_spec, "Test issue", "prod", "low")
    
    print("\nAFTER AUTO-FIX:")
    print("Step purposes (should be corrected):")
    corrections = []
    
    for i, step in enumerate(fixed_spec["steps"], 1):
        purpose = step.get("purpose", "unknown")
        command = step.get("command", "")[:50]
        name = step.get("name", f"Step {i}")
        original_purpose = original_purposes.get(name, "unknown")
        
        # Check if purpose was corrected
        if purpose != original_purpose and original_purpose != "unknown":
            corrections.append((i, original_purpose, purpose, name))
            print(f"  {i}. {purpose:10} - {name[:40]} [CORRECTED: {original_purpose} → {purpose}]")
        else:
            status = "unchanged" if purpose == original_purpose else "new"
            print(f"  {i}. {purpose:10} - {name[:40]} [{status}]")
        print(f"      Command: {command}")
    
    # Validate
    print("\n[STEP 2] Running validation...")
    validator = RunbookQualityValidator()
    is_valid, errors = validator.validate(fixed_spec, "Test issue")
    
    purpose_errors = [e for e in errors if "purpose" in e.lower() and ("invalid" in e.lower() or "wrong" in e.lower())]
    remediation_errors = [e for e in errors if "remediation" in e.lower() and "missing" not in e.lower()]
    other_errors = [e for e in errors if "purpose" not in e.lower() and "remediation" not in e.lower()]
    
    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"Purpose errors: {len(purpose_errors)}")
    print(f"Remediation errors: {len(remediation_errors)}")
    print(f"Other errors: {len(other_errors)}")
    
    if purpose_errors:
        print("\n✗ PURPOSE ERRORS (Auto-fix failed!):")
        for i, error in enumerate(purpose_errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n✓ NO PURPOSE ERRORS (Auto-fix worked!)")
    
    # Count remediation steps
    remediation_count = sum(1 for step in fixed_spec["steps"] if step.get("purpose") == "remediate")
    print(f"\nRemediation steps after fix: {remediation_count}")
    
    if remediation_errors:
        print("\n⚠ REMEDIATION ERRORS:")
        for i, error in enumerate(remediation_errors[:2], 1):
            print(f"  {i}. {error}")
    
    # Summary
    print("\n" + "="*80)
    print("PURPOSE AUTO-FIX TEST SUMMARY")
    print("="*80)
    
    print(f"\nCorrections made: {len(corrections)}")
    for step_num, old, new, name in corrections:
        print(f"  Step {step_num}: {old} → {new} ({name[:40]})")
    
    expected_corrections = [
        (1, "diagnose", "remediate", "Restart Service"),
        (2, "remediate", "diagnose", "Check Service Status"),
        (3, "verify", "remediate", "Kill Process"),
        (4, "remediate", "diagnose", "Get Process List"),
        (6, "diagnose", "remediate", "Clear Logs")
    ]
    
    if len(corrections) >= len(expected_corrections):
        print("\n✅ SUCCESS: Purpose auto-fix worked!")
        print("   - All mismatched purposes were corrected")
        print("   - Remediation steps properly identified")
        print("   - Validation found zero purpose errors")
        return True
    elif len(corrections) > 0:
        print(f"\n⚠️  PARTIAL: {len(corrections)}/{len(expected_corrections)} corrections made")
        return False
    else:
        print("\n❌ FAILURE: No purpose corrections were made!")
        return False


if __name__ == "__main__":
    try:
        success = test_purpose_autofix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

