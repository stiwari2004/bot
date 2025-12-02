#!/usr/bin/env python3
"""Quick script to check ManageEngine connection status"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.ticketing_tool_connection import TicketingToolConnection
import json

db = SessionLocal()
try:
    connection = db.query(TicketingToolConnection).filter(
        TicketingToolConnection.tool_name == "manageengine"
    ).first()
    
    if not connection:
        print("❌ No ManageEngine connection found")
        sys.exit(1)
    
    print(f"✅ Connection found: ID={connection.id}")
    print(f"   Active: {connection.is_active}")
    print(f"   Connection Type: {connection.connection_type}")
    print(f"   API Base URL: {connection.api_base_url}")
    print(f"   Last Sync: {connection.last_sync_at}")
    print(f"   Last Sync Status: {connection.last_sync_status}")
    print(f"   Last Error: {connection.last_error}")
    
    if connection.meta_data:
        meta = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
        has_token = bool(meta.get("access_token"))
        print(f"   Has Access Token: {has_token}")
    
    # Check if connection type is correct for polling
    if connection.connection_type != "api_poll":
        print(f"\n⚠️  WARNING: Connection type is '{connection.connection_type}', not 'api_poll'")
        print("   The poller only polls connections with connection_type='api_poll'")
        print("   Update the connection type to enable automatic polling")
    else:
        print("\n✅ Connection type is correct for polling")
    
    if not connection.is_active:
        print("\n⚠️  WARNING: Connection is not active")
        print("   Set is_active=true to enable polling")
    
finally:
    db.close()




