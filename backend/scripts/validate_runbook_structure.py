"""
Validate the generated runbook structure
"""
import sys
import os
import yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.runbook.generation.spec_post_processor import SpecPostProcessor
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator

# The runbook from the user
runbook_yaml = """
runbook_id: rb-network-vpn-connection
version: 1.0.0
title: Fix Trouble connecting to VPN
service: network
env: prod
risk: low
description: This runbook addresses issues preventing a client from successfully connecting to a VPN server. It will diagnose common problems such as VPN service failures, local network interface issues, and firewall blocks, then attempt to remediate them to restore VPN connectivity.

inputs:
- name: host_ip
  type: string
  required: true
  description: IP address of the VPN server to which the client is trying to connect.
- name: interface
  type: string
  required: false
  description: Network interface name (e.g., eth0, ens33)
  default: eth0
- name: vpn_internal_resource_ip
  type: string
  required: true
  description: Vpn Internal Resource Ip parameter
- name: vpn_service_name
  type: string
  required: true
  description: Name of the VPN service (e.g., openvpn, strongswan)

prechecks:
- description: Verify local host has an IP assigned to the target interface.
  command: ip addr show {{interface}} | grep 'inet '
  expected_output: inet
  severity: safe
  skip_in_auto_mode: false
- description: Ensure basic internet connectivity from the client.
  command: ping -c 4 8.8.8.8
  expected_output: 0% packet loss
  severity: safe
  skip_in_auto_mode: false
- description: Ensure DNS resolution is functioning on the client.
  command: nslookup google.com
  expected_output: Address
  severity: safe
  skip_in_auto_mode: false

steps:
- name: Check VPN Client Service Status
  step_number: 1
  type: command
  command: systemctl status {{vpn_service_name}}
  description: Checks if the VPN client service is running and its current status.
  expected_output: active (running)
  purpose: diagnose
  severity: safe
  skip_in_auto_mode: false
  on_success: 2
  on_failure: 3
- name: Ping VPN Server IP
  step_number: 2
  type: command
  command: ping -c 4 {{host_ip}}
  description: Tests basic network reachability to the VPN server IP address.
  expected_output: 0% packet loss
  purpose: diagnose
  severity: safe
  skip_in_auto_mode: false
  on_success: 5
  on_failure: 4
- name: Restart VPN Client Service
  step_number: 3
  type: command
  command: sudo systemctl restart {{vpn_service_name}}
  description: Attempts to restart the VPN client service to resolve transient issues.
  expected_output: Command executed successfully
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
  on_success: 2
  on_failure: 7
- name: Restart Local Network Interface
  step_number: 4
  type: command
  command: sudo ip link set dev {{interface}} down && sudo ip link set dev {{interface}} up
  description: Restarts the local network interface to clear any potential network stack issues.
  expected_output: Command executed successfully
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
  on_success: 2
  on_failure: 7
- name: Attempt VPN Reconnection
  step_number: 5
  type: command
  command: sudo systemctl start {{vpn_service_name}}
  description: Attempts to establish the VPN connection after performing previous remediation steps.
  expected_output: Command executed successfully
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
  on_success: 6
  on_failure: 7
- name: Verify VPN Connectivity to Internal Resource
  step_number: 6
  type: command
  command: ping -c 4 {{vpn_internal_resource_ip}}
  description: Verifies that a resource reachable only through the VPN is now accessible.
  expected_output: 0% packet loss
  purpose: verify
  severity: safe
  skip_in_auto_mode: false
  on_success: 8
  on_failure: 7
- name: Escalate to Network Team
  step_number: 7
  type: manual
  description: Automated remediation failed. Escalate to the network team for further investigation.
  purpose: verify
  severity: high
  skip_in_auto_mode: false
- name: Issue Resolved
  step_number: 8
  type: manual
  description: The VPN connection issue has been resolved.
  purpose: verify
  severity: safe
  skip_in_auto_mode: false

postchecks:
- description: Final verification of VPN connectivity to an internal resource.
  command: ping -c 4 {{vpn_internal_resource_ip}}
  expected_output: 0% packet loss
  severity: safe
  skip_in_auto_mode: false
"""

print("=" * 80)
print("VALIDATING RUNBOOK STRUCTURE")
print("=" * 80)

# Parse YAML
spec = yaml.safe_load(runbook_yaml)

# Check structure
print("\n1. STRUCTURE CHECK:")
print(f"   ✓ Prechecks: {len(spec.get('prechecks', []))} checks")
print(f"   ✓ Steps: {len(spec.get('steps', []))} steps")
print(f"   ✓ Postchecks: {len(spec.get('postchecks', []))} checks")
print(f"   ✓ Inputs: {len(spec.get('inputs', []))} inputs")

# Check step ordering
print("\n2. STEP ORDERING CHECK:")
steps = spec.get('steps', [])
diagnose_count = 0
remediate_count = 0
verify_count = 0
current_phase = 0  # 0=diagnose, 1=remediate, 2=verify

phase_order = {"diagnose": 0, "remediate": 1, "verify": 2}
ordering_errors = []

for i, step in enumerate(steps, 1):
    purpose = step.get('purpose', '').lower()
    phase = phase_order.get(purpose, 1)
    
    if purpose == "diagnose":
        diagnose_count += 1
    elif purpose == "remediate":
        remediate_count += 1
    elif purpose == "verify":
        verify_count += 1
    
    if phase < current_phase:
        ordering_errors.append(
            f"   ✗ Step {i} ('{step.get('name')}') with purpose '{purpose}' "
            f"appears after a later-phase step"
        )
    else:
        print(f"   ✓ Step {i}: {step.get('name')} [{purpose}]")
    
    current_phase = max(current_phase, phase)

if ordering_errors:
    print("\n   ORDERING ERRORS:")
    for error in ordering_errors:
        print(f"   {error}")
else:
    print(f"\n   ✓ Correct phase order: {diagnose_count} diagnose → {remediate_count} remediate → {verify_count} verify")

# Check branching targets
print("\n3. BRANCHING TARGETS CHECK:")
branching_errors = []
valid_step_numbers = {step.get('step_number') for step in steps}

for step in steps:
    step_num = step.get('step_number')
    step_name = step.get('name', 'Unknown')
    
    for branch_type in ['on_success', 'on_failure']:
        target = step.get(branch_type)
        if target is not None:
            if target not in valid_step_numbers:
                branching_errors.append(
                    f"   ✗ Step {step_num} ('{step_name}') has {branch_type}={target}, "
                    f"but step {target} does not exist"
                )
            else:
                print(f"   ✓ Step {step_num} → {branch_type}: {target}")

if branching_errors:
    print("\n   BRANCHING ERRORS:")
    for error in branching_errors:
        print(f"   {error}")
else:
    print("   ✓ All branching targets are valid")

# Check input references
print("\n4. INPUT REFERENCES CHECK:")
defined_inputs = {inp.get('name') for inp in spec.get('inputs', [])}
import re
placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')

missing_inputs = set()
for section in ['prechecks', 'steps', 'postchecks']:
    for item in spec.get(section, []):
        command = item.get('command', '')
        if command:
            placeholders = placeholder_pattern.findall(command)
            for placeholder in placeholders:
                if placeholder not in defined_inputs:
                    missing_inputs.add(placeholder)

if missing_inputs:
    print(f"   ✗ Missing inputs: {sorted(missing_inputs)}")
else:
    print("   ✓ All referenced inputs are defined")

# Run post-processor
print("\n5. POST-PROCESSING:")
processor = SpecPostProcessor()
processed_spec = processor.post_process(spec.copy(), "VPN connectivity issue", "prod", "low")

# Check if anything changed
if processed_spec != spec:
    print("   ⚠ Post-processor made changes (this is normal for auto-fixes)")
else:
    print("   ✓ No changes needed")

# Run validator
print("\n6. VALIDATION:")
validator = RunbookQualityValidator()
is_valid, errors = validator.validate(processed_spec, "VPN connectivity issue")

if is_valid:
    print("   ✓ Runbook is VALID")
else:
    print("   ✗ Runbook has VALIDATION ERRORS:")
    for error in errors:
        print(f"     - {error}")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)




