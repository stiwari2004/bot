"""
Test script to verify dependency-aware step reordering
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.runbook.generation.spec_post_processor import SpecPostProcessor

# Test case: VPN connectivity runbook with Step 3 that depends on Step 5
test_spec = {
    "runbook_id": "rb-network-vpn-connectivity",
    "version": "1.0.0",
    "title": "Fix Trouble connecting to VPN",
    "service": "network",
    "env": "prod",
    "risk": "low",
    "description": "Test runbook",
    "inputs": [],
    "prechecks": [],
    "steps": [
        {
            "name": "Check VPN Client Service Status",
            "step_number": 1,
            "type": "command",
            "command": "systemctl status {{vpn_service_name}}",
            "purpose": "diagnose",
            "on_success": 2,
            "on_failure": 4
        },
        {
            "name": "Ping VPN Server",
            "step_number": 2,
            "type": "command",
            "command": "ping -c 4 {{host_ip}}",
            "purpose": "diagnose",
            "on_success": 6,
            "on_failure": 5
        },
        {
            "name": "Re-ping VPN Server After Firewall Change",
            "step_number": 3,
            "type": "command",
            "command": "ping -c 4 {{host_ip}}",
            "description": "Re-tests connectivity to the VPN server after disabling the local firewall.",
            "purpose": "diagnose",
            "on_success": 6,
            "on_failure": 9
        },
        {
            "name": "Restart VPN Client Service",
            "step_number": 4,
            "type": "command",
            "command": "sudo systemctl restart {{vpn_service_name}}",
            "purpose": "remediate",
            "on_success": 2,
            "on_failure": 9
        },
        {
            "name": "Temporarily Disable Local Firewall",
            "step_number": 5,
            "type": "command",
            "command": "sudo ufw disable",
            "description": "Temporarily disables the local firewall",
            "purpose": "remediate",
            "on_success": 3,
            "on_failure": 9
        },
        {
            "name": "Restart Network Interface",
            "step_number": 6,
            "type": "command",
            "command": "sudo ip link set dev {{interface}} down",
            "purpose": "remediate",
            "on_success": 7,
            "on_failure": 9
        },
        {
            "name": "Clear Local DNS Cache",
            "step_number": 7,
            "type": "command",
            "command": "sudo systemd-resolve --flush-caches",
            "purpose": "remediate",
            "on_success": 8,
            "on_failure": 8
        },
        {
            "name": "Verify VPN Connection Established",
            "step_number": 8,
            "type": "command",
            "command": "ip addr show | grep 'inet '",
            "purpose": "verify",
            "on_success": 10,
            "on_failure": 9
        },
        {
            "name": "Escalate to L2/L3",
            "step_number": 9,
            "type": "manual",
            "description": "Escalating to a higher support tier",
            "purpose": "verify"
        }
    ],
    "postchecks": []
}

print("=" * 80)
print("BEFORE REORDERING:")
print("=" * 80)
for i, step in enumerate(test_spec["steps"], 1):
    print(f"Step {step.get('step_number')}: {step.get('name')} [{step.get('purpose')}]")

processor = SpecPostProcessor()
result = processor.post_process(test_spec, "VPN connectivity issue", "prod", "low")

print("\n" + "=" * 80)
print("AFTER REORDERING:")
print("=" * 80)
for i, step in enumerate(result["steps"], 1):
    print(f"Step {step.get('step_number')}: {step.get('name')} [{step.get('purpose')}]")
    if step.get('on_success'):
        print(f"  → on_success: {step.get('on_success')}")
    if step.get('on_failure'):
        print(f"  → on_failure: {step.get('on_failure')}")

print("\n" + "=" * 80)
print("VERIFICATION:")
print("=" * 80)
# Check if Step 3 (Re-ping After Firewall Change) comes after Step 5 (Disable Firewall)
step_3_idx = None
step_5_idx = None
for i, step in enumerate(result["steps"], 1):
    if "Re-ping VPN Server After Firewall Change" in step.get("name", ""):
        step_3_idx = i
    if "Temporarily Disable Local Firewall" in step.get("name", ""):
        step_5_idx = i

if step_3_idx and step_5_idx:
    if step_3_idx > step_5_idx:
        print(f"✓ SUCCESS: Step 3 (Re-ping After Firewall) is at position {step_3_idx}, "
              f"which is AFTER Step 5 (Disable Firewall) at position {step_5_idx}")
    else:
        print(f"✗ FAILED: Step 3 is at position {step_3_idx}, "
              f"which is BEFORE Step 5 at position {step_5_idx}")
else:
    print(f"Could not find steps: step_3_idx={step_3_idx}, step_5_idx={step_5_idx}")




