"""
Validate the current runbook structure and check for issues
"""
import sys
import os
import yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.runbook.generation.spec_post_processor import SpecPostProcessor
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator

# The runbook from the user
runbook_yaml = """
runbook_id: rb-network-vpn-connectivity
version: 1.0.0
title: Fix Trouble connecting to VPN
service: network
env: prod
risk: low
description: This runbook addresses issues preventing successful connection to a VPN. It diagnoses common network problems, VPN client service status, and firewall configurations, then attempts to remediate by restarting services, interfaces, or adjusting firewall rules to restore VPN connectivity.

inputs:
- name: host_ip
  type: string
  required: true
  description: IP address of the VPN server
- name: gateway_ip
  type: string
  required: true
  description: Local network gateway IP address
- name: interface
  type: string
  required: false
  default: eth0
  description: Local network interface to check and potentially restart (e.g., eth0, wlan0)
- name: vpn_service_name
  type: string
  required: true
  description: Name of the VPN client service (e.g., openvpn@client, strongswan, network-manager-l2tp)

prechecks:
- description: Verify local host has an IP assigned to the target interface
  command: ip addr show {{interface}} | grep 'inet '
  expected_output: inet
- description: Ensure local network gateway is reachable
  command: ping -c 4 {{gateway_ip}}
  expected_output: 0% packet loss
- description: Check the status of the VPN client service
  command: systemctl status {{vpn_service_name}} | grep Active
  expected_output: 'Active: active (running)'

steps:
- name: Diagnose - Ping VPN Server
  step_number: 1
  type: command
  command: ping -c 4 {{host_ip}}
  description: Checks basic IP connectivity to the VPN server.
  expected_output: 0% packet loss
  on_success: 4
  on_failure: 3
  purpose: diagnose
  severity: safe
  skip_in_auto_mode: false
- name: Diagnose - Check VPN Client Logs
  step_number: 2
  type: command
  command: journalctl -u {{vpn_service_name}} --since "10 minutes ago" | tail -n 30
  description: Retrieves recent logs from the VPN client service to identify specific connection errors.
  expected_output: Command executed successfully
  on_success: 5
  on_failure: 5
  purpose: diagnose
  severity: safe
  skip_in_auto_mode: false
- name: Remediate - Restart Local Network Interface
  step_number: 3
  type: command
  command: sudo ip link set dev {{interface}} down && sudo ip link set dev {{interface}} up
  description: Restarts the local network interface to resolve potential local network stack issues.
  expected_output: Command executed successfully
  on_success: 4
  on_failure: 10
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
- name: Remediate - Restart VPN Client Service
  step_number: 4
  type: command
  command: sudo systemctl restart {{vpn_service_name}}
  description: Restarts the VPN client service to re-establish the connection.
  expected_output: Command executed successfully
  on_success: 7
  on_failure: 10
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
- name: Remediate - Temporarily Disable Firewall
  step_number: 5
  type: command
  command: sudo ufw disable
  description: Temporarily disables the Uncomplicated Firewall (UFW) to rule out firewall blocking VPN traffic.
  expected_output: Firewall stopped and disabled on system startup
  on_success: 6
  on_failure: 10
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
- name: Remediate - Restart VPN Client Service (After Firewall)
  step_number: 6
  type: command
  command: sudo systemctl restart {{vpn_service_name}}
  description: Restarts the VPN client service again after firewall adjustments.
  expected_output: Command executed successfully
  on_success: 9
  on_failure: 10
  purpose: remediate
  severity: moderate
  skip_in_auto_mode: false
- name: Verify - VPN Service Status After Restart
  step_number: 7
  type: command
  command: systemctl status {{vpn_service_name}} | grep Active
  description: Verifies if the VPN client service is active and running after restart.
  expected_output: 'Active: active (running)'
  on_success: 8
  on_failure: 2
  purpose: verify
  severity: safe
  skip_in_auto_mode: false
- name: Verify - Check for VPN Tunnel Interface
  step_number: 8
  type: command
  command: ip link show | grep tun
  description: Checks for the presence of a VPN tunnel interface (e.g., tun0, ppp0) which indicates an active VPN connection.
  expected_output: tun
  on_success: 11
  on_failure: 2
  purpose: verify
  severity: safe
  skip_in_auto_mode: false
- name: Verify - Final VPN Service Status Check
  step_number: 9
  type: command
  command: systemctl status {{vpn_service_name}} | grep Active
  description: Final verification of VPN client service status after all remediation attempts.
  expected_output: 'Active: active (running)'
  on_success: 8
  on_failure: 10
  purpose: verify
  severity: safe
  skip_in_auto_mode: false
- name: Escalate to L2/L3
  step_number: 10
  type: manual
  description: Automatic remediation failed. Escalate to a higher support tier for manual investigation.
  purpose: verify
  severity: high
  skip_in_auto_mode: false
- name: Runbook Complete - VPN Connected
  step_number: 11
  type: manual
  description: VPN connection appears to be restored. Proceed to postchecks.
  purpose: verify
  severity: safe
  skip_in_auto_mode: false

postchecks:
- description: Verify VPN tunnel interface is active after remediation
  command: ip link show | grep tun
  expected_output: tun
"""

print("=" * 80)
print("VALIDATING RUNBOOK STRUCTURE")
print("=" * 80)

# Parse YAML
try:
    spec = yaml.safe_load(runbook_yaml)
    print("✓ YAML parsing successful")
except Exception as e:
    print(f"✗ YAML parsing failed: {e}")
    sys.exit(1)

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
ordering_warnings = []

for i, step in enumerate(steps, 1):
    purpose = step.get('purpose', '').lower()
    phase = phase_order.get(purpose, 1)
    step_num = step.get('step_number', i)
    step_name = step.get('name', 'Unknown')
    
    if purpose == "diagnose":
        diagnose_count += 1
    elif purpose == "remediate":
        remediate_count += 1
    elif purpose == "verify":
        verify_count += 1
    
    if phase < current_phase:
        ordering_errors.append(
            f"   ✗ Step {step_num} ('{step_name}') with purpose '{purpose}' "
            f"appears after a later-phase step"
        )
    else:
        print(f"   ✓ Step {step_num}: {step_name[:50]} [{purpose}]")
    
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
branching_warnings = []
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
                target_step = next((s for s in steps if s.get('step_number') == target), None)
                if target_step:
                    target_purpose = target_step.get('purpose', '').lower()
                    current_purpose = step.get('purpose', '').lower()
                    
                    # Check logical flow
                    if branch_type == 'on_success' and current_purpose == 'diagnose' and target_purpose == 'remediate':
                        print(f"   ✓ Step {step_num} → {branch_type}: {target} (diagnose → remediate)")
                    elif branch_type == 'on_failure' and current_purpose == 'remediate' and target_purpose == 'verify':
                        print(f"   ✓ Step {step_num} → {branch_type}: {target} (remediate → verify/escalate)")
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
changes = []
if len(processed_spec.get('steps', [])) != len(spec.get('steps', [])):
    changes.append("Step count changed")
if processed_spec.get('steps') != spec.get('steps'):
    # Check step order
    original_order = [s.get('step_number') for s in spec.get('steps', [])]
    processed_order = [s.get('step_number') for s in processed_spec.get('steps', [])]
    if original_order != processed_order:
        changes.append("Step order changed")

if changes:
    print(f"   ⚠ Post-processor made changes: {', '.join(changes)}")
    print("\n   ORIGINAL ORDER:")
    for step in spec.get('steps', []):
        print(f"     Step {step.get('step_number')}: {step.get('name')[:40]} [{step.get('purpose')}]")
    print("\n   PROCESSED ORDER:")
    for step in processed_spec.get('steps', []):
        print(f"     Step {step.get('step_number')}: {step.get('name')[:40]} [{step.get('purpose')}]")
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




