#!/usr/bin/env python3
"""Quick script to check OAuth tokens in database"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.ticketing_tool_connection import TicketingToolConnection
import json

db = SessionLocal()
try:
    connections = db.query(TicketingToolConnection).filter(
        TicketingToolConnection.tool_name == "manageengine"
    ).all()
    
    for conn in connections:
        meta_data = json.loads(conn.meta_data) if conn.meta_data else {}
        has_token = bool(meta_data.get("access_token"))
        print(f"Connection ID: {conn.id}")
        print(f"  API Base URL: {conn.api_base_url}")
        print(f"  Has access_token: {has_token}")
        print(f"  Has client_id: {bool(meta_data.get('client_id'))}")
        print(f"  Has client_secret: {bool(meta_data.get('client_secret'))}")
        print(f"  Last sync status: {conn.last_sync_status}")
        print(f"  Last error: {conn.last_error}")
        if has_token:
            token = meta_data.get("access_token", "")
            print(f"  Token (first 20 chars): {token[:20]}...")
        print()
finally:
    db.close()



