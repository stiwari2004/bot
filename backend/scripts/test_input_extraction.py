"""
Test script for input extraction functionality
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.runbook.input_extractor import RunbookInputExtractor
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.core.database import SessionLocal

# Create a test ticket with Datadog metadata
test_ticket_data = {
    "id": 999,
    "source": "datadog",
    "title": "VPN connectivity issue",
    "description": "Unable to connect to VPN server 10.0.1.5",
    "meta_data": {
        "host": "server-01.example.com",
        "tags": ["host:server-01.example.com", "service:openvpn", "interface:eth0"],
        "ip": "10.0.1.5"
    },
    "raw_payload": {
        "host": "server-01.example.com",
        "tags": ["host:server-01.example.com", "service:openvpn", "interface:eth0", "gateway:192.168.1.1"],
        "service": "openvpn"
    }
}

# Create a test runbook spec
test_runbook_spec = {
    "inputs": [
        {"name": "host_ip", "type": "string", "required": True},
        {"name": "gateway_ip", "type": "string", "required": True},
        {"name": "interface", "type": "string", "required": False, "default": "eth0"},
        {"name": "vpn_service_name", "type": "string", "required": True}
    ]
}

print("=" * 80)
print("TESTING INPUT EXTRACTION")
print("=" * 80)

# Create mock ticket and runbook objects
class MockTicket:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)

class MockRunbook:
    def __init__(self):
        import yaml
        self.body_md = yaml.safe_dump(test_runbook_spec)

ticket = MockTicket(test_ticket_data)
runbook = MockRunbook()

# Test extraction
extractor = RunbookInputExtractor()
db = SessionLocal()

try:
    result = asyncio.run(extractor.extract_inputs(ticket, runbook, db))
    
    print("\n1. EXTRACTION RESULT:")
    print(f"   Extracted: {result.get('extracted', {})}")
    print(f"   Missing: {result.get('missing', [])}")
    print(f"   Confidence: {result.get('confidence', {})}")
    
    print("\n2. VALIDATION:")
    extracted = result.get('extracted', {})
    missing = result.get('missing', [])
    
    if "host_ip" in extracted:
        print(f"   ✓ host_ip extracted: {extracted['host_ip']}")
    else:
        print(f"   ✗ host_ip missing")
    
    if "vpn_service_name" in extracted:
        print(f"   ✓ vpn_service_name extracted: {extracted['vpn_service_name']}")
    else:
        print(f"   ✗ vpn_service_name missing")
    
    if "interface" in extracted:
        print(f"   ✓ interface extracted: {extracted['interface']}")
    else:
        print(f"   ✗ interface missing")
    
    if len(missing) == 0:
        print("\n   ✓ All required inputs extracted!")
    else:
        print(f"\n   ⚠ Missing inputs: {missing}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()




