#!/usr/bin/env python3
"""
Test script to verify auto-fix for missing inputs
Tests that post-processor automatically adds missing inputs
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.runbook.generation.spec_post_processor import SpecPostProcessor
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_autofix_missing_inputs():
    """Test that auto-fix adds missing inputs before validation"""
    
    # Create a test runbook spec with missing inputs (same as validation test)
    test_spec = {
        "runbook_id": "rb-test-autofix",
        "version": "1.0.0",
        "title": "Test Runbook with Missing Inputs",
        "service": "network",
        "env": "prod",
        "risk": "low",
        "description": "Test runbook to verify auto-fix",
        "inputs": [
            {
                "name": "host_ip",
                "type": "string",
                "required": True,
                "description": "Only one input defined"
            }
        ],
        "prechecks": [
            {
                "description": "Check interface",
                "command": "ip addr show {{interface}} | grep 'inet '",  # Missing: interface
                "expected_output": "inet "
            },
            {
                "description": "Check gateway",
                "command": "ping -c 4 {{gateway_ip}}",  # Missing: gateway_ip
                "expected_output": "0% packet loss"
            },
            {
                "description": "DNS check",
                "command": "nslookup google.com",
                "expected_output": "Address"
            }
        ],
        "steps": [
            {
                "name": "Step 1 - Check Service",
                "step_number": 1,
                "type": "command",
                "command": "systemctl status {{vpn_service_name}}",  # Missing: vpn_service_name
                "description": "Check VPN service",
                "expected_output": "active (running)",
                "on_success": 2,
                "on_failure": 3,
                "purpose": "diagnose",
                "severity": "safe"
            },
            {
                "name": "Step 2 - Restart Service",
                "step_number": 2,
                "type": "command",
                "command": "sudo systemctl restart {{vpn_service_name}}",  # Missing: vpn_service_name
                "description": "Restart VPN service",
                "expected_output": "Command executed successfully",
                "on_success": 4,
                "on_failure": 5,
                "purpose": "remediate",
                "severity": "moderate"
            },
            {
                "name": "Step 3 - Check DNS",
                "step_number": 3,
                "type": "command",
                "command": "nslookup {{vpn_server_hostname}}",  # Missing: vpn_server_hostname
                "description": "Check DNS resolution",
                "expected_output": "Address",
                "on_success": 4,
                "on_failure": 6,
                "purpose": "diagnose",
                "severity": "safe"
            },
            {
                "name": "Step 4 - Restart Interface",
                "step_number": 4,
                "type": "command",
                "command": "sudo ip link set dev {{interface}} down && sudo ip link set dev {{interface}} up",  # Missing: interface
                "description": "Restart network interface",
                "expected_output": "Command executed successfully",
                "on_success": 7,
                "on_failure": 5,
                "purpose": "remediate",
                "severity": "moderate"
            },
            {
                "name": "Step 5 - Check Firewall",
                "step_number": 5,
                "type": "command",
                "command": "{{firewall_tool}} status",  # Missing: firewall_tool
                "description": "Check firewall status",
                "expected_output": "Status: active",
                "on_success": 6,
                "on_failure": 7,
                "purpose": "diagnose",
                "severity": "safe"
            },
            {
                "name": "Step 6 - Disable Firewall",
                "step_number": 6,
                "type": "command",
                "command": "{{firewall_tool}} disable",  # Missing: firewall_tool
                "description": "Disable firewall",
                "expected_output": "Command executed successfully",
                "on_success": 7,
                "on_failure": 8,
                "purpose": "remediate",
                "severity": "moderate"
            },
            {
                "name": "Step 7 - Verify",
                "step_number": 7,
                "type": "command",
                "command": "ping -c 4 {{host_ip}}",  # This one EXISTS
                "description": "Verify connectivity",
                "expected_output": "0% packet loss",
                "purpose": "verify",
                "severity": "safe"
            },
            {
                "name": "Step 8 - Escalate",
                "step_number": 8,
                "type": "manual",
                "description": "Escalate if all fixes fail",
                "purpose": "verify",
                "severity": "safe"
            }
        ],
        "postchecks": [
            {
                "description": "Final check",
                "command": "ping -c 4 {{gateway_ip}}",  # Missing: gateway_ip
                "expected_output": "0% packet loss"
            }
        ]
    }
    
    print("\n" + "="*80)
    print("TESTING AUTO-FIX FOR MISSING INPUTS")
    print("="*80)
    print(f"\nBEFORE AUTO-FIX:")
    print(f"  Inputs defined: {len(test_spec['inputs'])}")
    for inp in test_spec['inputs']:
        print(f"    - {inp['name']}")
    
    print(f"\nMissing inputs referenced in commands:")
    print(f"  - interface (used in precheck 1, step 4)")
    print(f"  - gateway_ip (used in precheck 2, postcheck)")
    print(f"  - vpn_service_name (used in steps 1, 2)")
    print(f"  - vpn_server_hostname (used in step 3)")
    print(f"  - firewall_tool (used in steps 5, 6)")
    
    # Run post-processor (this should auto-fix)
    post_processor = SpecPostProcessor()
    fixed_spec = post_processor.post_process(test_spec, "Test issue", "prod", "low")
    
    print(f"\nAFTER AUTO-FIX:")
    print(f"  Inputs defined: {len(fixed_spec['inputs'])}")
    for inp in fixed_spec['inputs']:
        required = inp.get('required', False)
        default = inp.get('default', 'N/A')
        print(f"    - {inp['name']} (required={required}, default={default})")
    
    # Now validate the fixed spec
    validator = RunbookQualityValidator()
    issue_description = "Test issue for validation"
    
    print("\n" + "-"*80)
    print("VALIDATING FIXED RUNBOOK:")
    print("-"*80)
    
    is_valid, errors = validator.validate(fixed_spec, issue_description)
    
    # Filter input validation errors
    input_errors = [e for e in errors if "undefined input" in e.lower() or "references undefined" in e.lower()]
    other_errors = [e for e in errors if "undefined input" not in e.lower() and "references undefined" not in e.lower()]
    
    print(f"\nis_valid: {is_valid}")
    print(f"total_errors: {len(errors)}")
    print(f"input_errors: {len(input_errors)}")
    print(f"other_errors: {len(other_errors)}")
    
    if input_errors:
        print("\n❌ INPUT VALIDATION ERRORS (Auto-fix failed!):")
        for i, error in enumerate(input_errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n✅ NO INPUT VALIDATION ERRORS (Auto-fix worked!)")
    
    if other_errors:
        print("\n⚠️  OTHER VALIDATION ERRORS (Expected - not related to inputs):")
        for i, error in enumerate(other_errors[:3], 1):  # Show first 3
            print(f"  {i}. {error}")
        if len(other_errors) > 3:
            print(f"  ... and {len(other_errors) - 3} more")
    
    print("\n" + "="*80)
    print("AUTO-FIX TEST SUMMARY")
    print("="*80)
    
    # Check if auto-fix worked
    expected_inputs = ["host_ip", "interface", "gateway_ip", "vpn_service_name", "vpn_server_hostname", "firewall_tool"]
    actual_inputs = [inp.get("name") for inp in fixed_spec["inputs"] if isinstance(inp, dict)]
    
    missing_after_fix = [inp for inp in expected_inputs if inp not in actual_inputs]
    added_by_fix = [inp for inp in actual_inputs if inp not in ["host_ip"]]  # All except the original
    
    print(f"\nExpected inputs after fix: {len(expected_inputs)}")
    print(f"Actual inputs after fix: {len(actual_inputs)}")
    print(f"\nAdded by auto-fix: {sorted(added_by_fix)}")
    print(f"Still missing: {missing_after_fix}")
    
    if len(input_errors) == 0 and len(missing_after_fix) == 0:
        print("\n✅ SUCCESS: Auto-fix worked! All missing inputs were added.")
        return True
    elif len(input_errors) == 0:
        print(f"\n⚠️  PARTIAL: Auto-fix added inputs but {len(missing_after_fix)} still missing")
        return False
    else:
        print(f"\n❌ FAILURE: Auto-fix did not work. {len(input_errors)} input errors remain.")
        return False


if __name__ == "__main__":
    try:
        success = test_autofix_missing_inputs()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




