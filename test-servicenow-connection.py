#!/usr/bin/env python3
"""
Test ServiceNow Connection
Tests the ServiceNow integration by creating a connection and fetching incidents
"""
import sys
import os
import asyncio
import json
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher


async def test_servicenow_connection():
    """Test ServiceNow connection"""
    print("=" * 60)
    print("ServiceNow Connection Test")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    try:
        # Get ServiceNow connection
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tool_name == "servicenow",
            TicketingToolConnection.is_active == True
        ).first()
        
        if not connection:
            print("❌ No active ServiceNow connection found")
            print()
            print("Please create a connection first using:")
            print("  POST /api/v1/ticketing-connections")
            print()
            print("Example request body:")
            print(json.dumps({
                "tool_name": "servicenow",
                "connection_type": "api_poll",
                "api_base_url": "https://your-instance.service-now.com",
                "sync_interval_minutes": 5,
                "meta_data": {
                    "username": "your-username",  # For Basic Auth
                    "password": "your-password",   # For Basic Auth
                    # OR for OAuth:
                    # "client_id": "your-client-id",
                    # "client_secret": "your-client-secret"
                }
            }, indent=2))
            return
        
        print(f"✅ Found ServiceNow connection ID: {connection.id}")
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
        else:
            meta_data = {}
        
        print("Connection Metadata:")
        if meta_data.get("username"):
            print(f"   Auth Method: Basic Auth")
            print(f"   Username: {meta_data.get('username')}")
            print(f"   Password: {'*' * len(meta_data.get('password', ''))}")
        elif meta_data.get("client_id"):
            print(f"   Auth Method: OAuth 2.0")
            print(f"   Client ID: {meta_data.get('client_id')}")
            print(f"   Client Secret: {'*' * len(meta_data.get('client_secret', ''))}")
            if meta_data.get("access_token"):
                print(f"   Access Token: {'*' * 20}... (exists)")
                print(f"   Expires At: {meta_data.get('expires_at')}")
        else:
            print("   ⚠️  No authentication credentials found!")
        print()
        
        # Test fetching tickets
        print("Testing connection by fetching incidents...")
        print("-" * 60)
        
        fetcher = ServiceNowTicketFetcher()
        try:
            tickets = await fetcher.fetch_tickets(
                api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                connection_meta=meta_data,
                username=meta_data.get("username"),
                password=meta_data.get("password"),
                client_id=meta_data.get("client_id"),
                client_secret=meta_data.get("client_secret"),
                since=None,  # Fetch recent tickets
                limit=10  # Just test with a few tickets
            )
            
            print(f"✅ Successfully fetched {len(tickets)} incidents")
            print()
            
            if tickets:
                print("Sample incidents:")
                for i, ticket in enumerate(tickets[:5], 1):
                    print(f"\n{i}. {ticket['title']}")
                    print(f"   Number: {ticket['external_id']}")
                    print(f"   Status: {ticket['status']}")
                    print(f"   Severity: {ticket['severity']}")
                    if ticket.get('metadata', {}).get('servicenow_state'):
                        print(f"   ServiceNow State: {ticket['metadata']['servicenow_state']}")
            else:
                print("   No incidents found (this is OK if there are no recent incidents)")
            
            # Update connection status
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "success"
            connection.last_error = None
            
            # Persist any token updates
            if meta_data:
                connection.meta_data = json.dumps(meta_data)
            
            db.commit()
            
            print()
            print("=" * 60)
            print("✅ Connection test successful!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error fetching incidents: {e}")
            print()
            import traceback
            print("Full error traceback:")
            traceback.print_exc()
            
            # Update connection status
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "error"
            connection.last_error = str(e)[:500]
            db.commit()
            
            print()
            print("=" * 60)
            print("❌ Connection test failed!")
            print("=" * 60)
            print()
            print("Troubleshooting:")
            print("1. Verify ServiceNow instance URL is correct")
            print("2. Check credentials (username/password or OAuth client_id/secret)")
            print("3. Ensure user has permissions to read incidents")
            print("4. Check ServiceNow instance is accessible from this server")
            print("5. Review error message above for specific issues")
            
        finally:
            await fetcher.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_servicenow_connection())









