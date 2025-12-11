#!/usr/bin/env python3
"""
Test the full runbook generation flow with auto-fix
Simulates what happens during real generation
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


def test_full_generation_flow():
    """Test the full flow: LLM output -> Post-processor -> Validation"""
    
    # Simulate what Gemini might generate (with missing inputs)
    simulated_llm_yaml = """
runbook_id: rb-network-vpn-connection-fail
version: 1.0.0
title: Fix VPN Connection Failure
service: network
env: prod
risk: medium
description: Fix VPN connection issues with packet loss on interface

inputs:
  - name: host_ip
    type: string
    required: true
    description: Target host IP address

prechecks:
  - description: Check network interface status
    command: ip addr show {{interface}} | grep 'inet '
    expected_output: inet 
  - description: Ping VPN server to check connectivity
    command: ping -c 4 {{vpn_server_ip}}
    expected_output: 0% packet loss
  - description: Check DNS resolution
    command: nslookup {{vpn_server_hostname}}
    expected_output: Address

steps:
  - name: Check VPN Service Status
    step_number: 1
    type: command
    command: systemctl status {{vpn_service_name}}
    description: Check if VPN service is running
    expected_output: active (running)
    on_success: 3
    on_failure: 2
    purpose: diagnose
    severity: safe
  - name: Restart VPN Service
    step_number: 2
    type: command
    command: sudo systemctl restart {{vpn_service_name}}
    description: Restart the VPN service
    expected_output: Command executed successfully
    on_success: 3
    on_failure: 4
    purpose: remediate
    severity: moderate
  - name: Restart Network Interface
    step_number: 3
    type: command
    command: sudo ip link set dev {{interface}} down && sudo ip link set dev {{interface}} up
    description: Restart the network interface
    expected_output: Command executed successfully
    on_success: 5
    on_failure: 4
    purpose: remediate
    severity: moderate
  - name: Verify Connectivity
    step_number: 4
    type: command
    command: ping -c 4 {{vpn_server_ip}}
    description: Verify VPN server is reachable
    expected_output: 0% packet loss
    purpose: verify
    severity: safe
  - name: Check Firewall Rules
    step_number: 5
    type: command
    command: "{{firewall_tool}} status | grep -i vpn"
    description: Check firewall rules for VPN
    expected_output: VPN rules found
    on_success: 6
    on_failure: 7
    purpose: diagnose
    severity: safe
  - name: Escalate
    step_number: 6
    type: manual
    description: Escalate to network team if all fixes fail
    purpose: verify
    severity: safe

postchecks:
  - description: Final connectivity check
    command: ping -c 4 {{gateway_ip}}
    expected_output: 0% packet loss
"""
    
    print("\n" + "="*80)
    print("TESTING FULL GENERATION FLOW WITH AUTO-FIX")
    print("="*80)
    
    # Step 1: Parse YAML (simulating what comes from LLM)
    print("\n[STEP 1] Parsing LLM-generated YAML...")
    try:
        spec = yaml.safe_load(simulated_llm_yaml)
        print(f"  ✓ Parsed successfully")
        print(f"  Inputs defined: {len(spec.get('inputs', []))}")
        for inp in spec.get('inputs', []):
            print(f"    - {inp.get('name')}")
    except Exception as e:
        print(f"  ✗ Parse failed: {e}")
        return False
    
    # Step 2: Post-processor (AUTO-FIX happens here)
    print("\n[STEP 2] Running post-processor (AUTO-FIX)...")
    post_processor = SpecPostProcessor()
    fixed_spec = post_processor.post_process(spec, "VPN connection failing", "prod", "medium")
    
    print(f"  Inputs after auto-fix: {len(fixed_spec.get('inputs', []))}")
    original_inputs = {inp.get('name') for inp in spec.get('inputs', [])}
    fixed_inputs = {inp.get('name') for inp in fixed_spec.get('inputs', [])}
    added_inputs = fixed_inputs - original_inputs
    
    print(f"  Original inputs: {sorted(original_inputs)}")
    print(f"  Fixed inputs: {sorted(fixed_inputs)}")
    
    if added_inputs:
        print(f"\n  ✓ Auto-fix added {len(added_inputs)} missing input(s):")
        for inp_name in sorted(added_inputs):
            inp = next((i for i in fixed_spec.get('inputs', []) if i.get('name') == inp_name), None)
            if inp:
                required = inp.get('required', False)
                default = inp.get('default', 'N/A')
                desc = inp.get('description', 'N/A')[:50]
                print(f"    - {inp_name} (required={required}, default={default})")
                print(f"      Description: {desc}")
    else:
        print(f"  ⚠ No inputs were added (all were already defined)")
    
    # Step 3: Validation
    print("\n[STEP 3] Running validation...")
    validator = RunbookQualityValidator()
    is_valid, errors = validator.validate(fixed_spec, "VPN connection failing")
    
    # Separate input errors from other errors
    input_errors = [e for e in errors if "undefined input" in e.lower() or "references undefined" in e.lower()]
    other_errors = [e for e in errors if "undefined input" not in e.lower() and "references undefined" not in e.lower()]
    
    print(f"  Validation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"  Input errors: {len(input_errors)}")
    print(f"  Other errors: {len(other_errors)}")
    
    if input_errors:
        print("\n  ✗ INPUT VALIDATION ERRORS (Auto-fix failed!):")
        for i, error in enumerate(input_errors[:5], 1):
            print(f"    {i}. {error[:100]}...")
    else:
        print("\n  ✓ NO INPUT VALIDATION ERRORS (Auto-fix worked!)")
    
    if other_errors:
        print("\n  ⚠ OTHER VALIDATION ERRORS (Not related to inputs):")
        for i, error in enumerate(other_errors[:3], 1):
            print(f"    {i}. {error[:100]}...")
        if len(other_errors) > 3:
            print(f"    ... and {len(other_errors) - 3} more")
    
    # Summary
    print("\n" + "="*80)
    print("GENERATION FLOW TEST SUMMARY")
    print("="*80)
    
    # Check what was referenced in commands
    import re
    placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
    all_commands = []
    for section in ['prechecks', 'steps', 'postchecks']:
        for item in fixed_spec.get(section, []):
            if isinstance(item, dict) and item.get('command'):
                all_commands.append(item['command'])
    
    referenced_placeholders = set()
    for cmd in all_commands:
        referenced_placeholders.update(placeholder_pattern.findall(cmd))
    
    print(f"\nReferenced placeholders in commands: {sorted(referenced_placeholders)}")
    print(f"Inputs defined after auto-fix: {sorted(fixed_inputs)}")
    
    missing_after_fix = referenced_placeholders - fixed_inputs
    
    if len(input_errors) == 0 and len(missing_after_fix) == 0:
        print("\n✅ SUCCESS: Auto-fix worked perfectly!")
        print("   - All missing inputs were automatically added")
        print("   - Validation found zero input errors")
        print("   - Runbook is ready to use")
        return True
    elif len(input_errors) == 0:
        print(f"\n⚠️  PARTIAL: Auto-fix added inputs but {len(missing_after_fix)} still missing: {missing_after_fix}")
        return False
    else:
        print(f"\n❌ FAILURE: Auto-fix did not work. {len(input_errors)} input errors remain.")
        return False


if __name__ == "__main__":
    try:
        success = test_full_generation_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

