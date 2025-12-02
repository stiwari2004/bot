#!/usr/bin/env python3
"""
Check ServiceNow Connection Status
Checks if a ServiceNow connection exists and shows its details
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.ticketing_tool_connection import TicketingToolConnection


def check_connection():
    """Check ServiceNow connection status"""
    print("=" * 60)
    print("ServiceNow Connection Status Check")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    try:
        # Get all ServiceNow connections
        connections = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tool_name == "servicenow"
        ).all()
        
        if not connections:
            print("❌ No ServiceNow connections found")
            print()
            print("To create a connection:")
            print("1. Use the UI: Settings > Ticketing Connections > Add Connection")
            print("2. Use PowerShell: .\\create-servicenow-connection.ps1")
            print("3. Use API: POST /api/v1/ticketing-connections")
            return
        
        print(f"✅ Found {len(connections)} ServiceNow connection(s)")
        print()
        
        for i, connection in enumerate(connections, 1):
            print(f"Connection #{i}:")
            print(f"  ID: {connection.id}")
            print(f"  Tool: {connection.tool_name}")
            print(f"  Type: {connection.connection_type}")
            print(f"  Active: {connection.is_active}")
            print(f"  API Base URL: {connection.api_base_url}")
            print(f"  Sync Interval: {connection.sync_interval_minutes} minutes")
            print(f"  Last Sync: {connection.last_sync_at}")
            print(f"  Last Status: {connection.last_sync_status}")
            if connection.last_error:
                print(f"  Last Error: {connection.last_error[:100]}...")
            
            # Parse meta_data
            if connection.meta_data:
                try:
                    meta_data = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
                    print()
                    print("  Authentication:")
                    if meta_data.get("username"):
                        print(f"    Method: Basic Auth")
                        print(f"    Username: {meta_data.get('username')}")
                        print(f"    Password: {'*' * len(meta_data.get('password', ''))}")
                    elif meta_data.get("client_id"):
                        print(f"    Method: OAuth 2.0")
                        print(f"    Client ID: {meta_data.get('client_id')}")
                        print(f"    Client Secret: {'*' * len(meta_data.get('client_secret', ''))}")
                        if meta_data.get("access_token"):
                            print(f"    Access Token: {'*' * 20}... (exists)")
                            print(f"    Expires At: {meta_data.get('expires_at')}")
                    else:
                        print("    ⚠️  No authentication credentials found!")
                except Exception as e:
                    print(f"    ⚠️  Error parsing metadata: {e}")
            
            print()
            print("-" * 60)
            print()
        
        print("To test the connection:")
        print(f"  python test-servicenow-connection.py")
        print(f"  OR POST /api/v1/ticketing-connections/{connections[0].id}/test")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    check_connection()


