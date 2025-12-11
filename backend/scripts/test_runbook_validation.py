#!/usr/bin/env python3
"""
Test script to verify runbook input validation
Tests that validation catches missing input references
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_validation_with_missing_inputs():
    """Test validation with a runbook that has missing input references"""
    
    # Create a test runbook spec with missing inputs
    test_spec = {
        "runbook_id": "rb-test-validation",
        "version": "1.0.0",
        "title": "Test Runbook with Missing Inputs",
        "service": "network",
        "env": "prod",
        "risk": "low",
        "description": "Test runbook to verify input validation",
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
    
    validator = RunbookQualityValidator()
    issue_description = "Test issue for validation"
    
    print("\n" + "="*80)
    print("TESTING RUNBOOK INPUT VALIDATION")
    print("="*80)
    print(f"\nTest runbook has only 1 input defined: 'host_ip'")
    print(f"But references these missing inputs:")
    print(f"  - interface (used in precheck 1, step 4)")
    print(f"  - gateway_ip (used in precheck 2, postcheck)")
    print(f"  - vpn_service_name (used in steps 1, 2)")
    print(f"  - vpn_server_hostname (used in step 3)")
    print(f"  - firewall_tool (used in steps 5, 6)")
    print("\nRunning validation...\n")
    
    is_valid, errors = validator.validate(test_spec, issue_description)
    
    print("="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print(f"is_valid: {is_valid}")
    print(f"error_count: {len(errors)}")
    print("\n" + "-"*80)
    print("VALIDATION ERRORS:")
    print("-"*80)
    
    if errors:
        input_errors = [e for e in errors if "undefined input" in e.lower() or "references undefined" in e.lower()]
        other_errors = [e for e in errors if "undefined input" not in e.lower() and "references undefined" not in e.lower()]
        
        if input_errors:
            print("\n🔴 INPUT VALIDATION ERRORS (Expected):")
            for i, error in enumerate(input_errors, 1):
                print(f"  {i}. {error}")
        
        if other_errors:
            print("\n⚠️  OTHER VALIDATION ERRORS:")
            for i, error in enumerate(other_errors, 1):
                print(f"  {i}. {error}")
    else:
        print("❌ NO ERRORS FOUND - Validation is NOT working!")
        return False
    
    print("\n" + "="*80)
    print("VALIDATION TEST SUMMARY")
    print("="*80)
    
    # Check if we caught the missing inputs
    missing_inputs_expected = ["interface", "gateway_ip", "vpn_service_name", "vpn_server_hostname", "firewall_tool"]
    caught_inputs = []
    
    for error in errors:
        for missing_input in missing_inputs_expected:
            if missing_input in error.lower():
                if missing_input not in caught_inputs:
                    caught_inputs.append(missing_input)
    
    print(f"\nExpected to catch: {len(missing_inputs_expected)} missing inputs")
    print(f"Actually caught: {len(caught_inputs)} missing inputs")
    print(f"\nCaught inputs: {caught_inputs}")
    print(f"Missed inputs: {[i for i in missing_inputs_expected if i not in caught_inputs]}")
    
    if len(caught_inputs) == len(missing_inputs_expected):
        print("\n✅ SUCCESS: All missing inputs were caught!")
        return True
    elif len(caught_inputs) > 0:
        print(f"\n⚠️  PARTIAL: Caught {len(caught_inputs)}/{len(missing_inputs_expected)} missing inputs")
        return False
    else:
        print("\n❌ FAILURE: No missing inputs were caught!")
        return False


if __name__ == "__main__":
    try:
        success = test_validation_with_missing_inputs()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




