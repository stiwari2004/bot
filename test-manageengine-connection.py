#!/usr/bin/env python3
"""Test ManageEngine connection and polling"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
import json
import asyncio
from datetime import datetime, timedelta, timezone

async def test_connection():
    """Test ManageEngine connection"""
    db = SessionLocal()
    try:
        # Get ManageEngine connection
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tool_name == "manageengine",
            TicketingToolConnection.is_active == True
        ).first()
        
        if not connection:
            print("❌ No active ManageEngine connection found")
            return
        
        print(f"✅ Found connection ID: {connection.id}")
        print(f"   Tool: {connection.tool_name}")
        print(f"   Active: {connection.is_active}")
        print(f"   Connection Type: {connection.connection_type}")
        print(f"   API Base URL: {connection.api_base_url}")
        print(f"   Last Sync: {connection.last_sync_at}")
        print(f"   Last Sync Status: {connection.last_sync_status}")
        print(f"   Last Error: {connection.last_error}")
        print()
        
        # Parse meta_data
        if connection.meta_data:
            meta_data = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
            has_token = bool(meta_data.get("access_token"))
            has_refresh = bool(meta_data.get("refresh_token"))
            print(f"   Has Access Token: {has_token}")
            print(f"   Has Refresh Token: {has_refresh}")
            if has_token:
                token = meta_data.get("access_token", "")
                print(f"   Token (first 20 chars): {token[:20]}...")
        else:
            print("   ⚠️  No meta_data found")
            return
        
        print()
        print("Testing connection...")
        
        # Test fetching tickets
        fetcher = ManageEngineTicketFetcher()
        api_base_url = connection.api_base_url or ""
        if not api_base_url.startswith("http"):
            api_base_url = f"https://{api_base_url}"
        
        try:
            tickets = await fetcher.fetch_tickets(
                api_base_url=api_base_url,
                connection_meta=meta_data,
                since=datetime.now(timezone.utc) - timedelta(hours=24),
                limit=10
            )
            
            print(f"✅ Successfully fetched {len(tickets)} tickets")
            if tickets:
                print("\nRecent tickets:")
                for ticket in tickets[:5]:
                    print(f"   - {ticket.get('external_id')}: {ticket.get('title')[:50]}... (Status: {ticket.get('status')})")
            else:
                print("   (No tickets found in last 24 hours)")
                
        except Exception as e:
            print(f"❌ Failed to fetch tickets: {e}")
            import traceback
            traceback.print_exc()
        
        await fetcher.close()
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_connection())

