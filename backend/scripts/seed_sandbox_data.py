"""
Seed sandbox environment with sample data
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.execution_session import ExecutionSession
from app.services.auth import get_password_hash
from datetime import datetime, timezone
import json


async def seed_sandbox_data():
    """Seed sandbox database with sample data"""
    print("🌱 Seeding sandbox environment with sample data...")
    
    # Initialize database
    await init_db()
    
    db = SessionLocal()
    try:
        # Ensure demo tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == 1).first()
        if not tenant:
            tenant = Tenant(
                id=1,
                name="demo",
                description="Demo tenant for sandbox testing",
                is_active=True
            )
            db.add(tenant)
            db.commit()
            print("✅ Created demo tenant")
        else:
            print("✅ Demo tenant already exists")
        
        # Create demo user if not exists
        demo_user = db.query(User).filter(User.email == "demo@example.com").first()
        if not demo_user:
            demo_user = User(
                tenant_id=1,
                email="demo@example.com",
                password_hash=get_password_hash("demo123"),
                full_name="Demo User",
                role="admin",
                is_active=True
            )
            db.add(demo_user)
            db.commit()
            print("✅ Created demo user (email: demo@example.com, password: demo123)")
        else:
            print("✅ Demo user already exists")
        
        # Create sample tickets
        sample_tickets = [
            {
                "title": "High CPU Usage on Web Server",
                "description": "CPU usage has been consistently above 90% for the past hour on web-server-01",
                "severity": "high",
                "status": "open",
                "source": "prometheus",
                "classification": "performance",
                "environment": "prod",
                "service": "web-server"
            },
            {
                "title": "Database Connection Pool Exhausted",
                "description": "Application unable to connect to database. Connection pool shows 100% utilization",
                "severity": "critical",
                "status": "in_progress",
                "source": "custom",
                "classification": "database",
                "environment": "prod",
                "service": "database"
            },
            {
                "title": "Disk Space Low on Storage Server",
                "description": "Disk usage at 95% on /var partition. Need to clean up or expand storage",
                "severity": "medium",
                "status": "open",
                "source": "custom",
                "classification": "storage",
                "environment": "prod",
                "service": "storage-server"
            }
        ]
        
        tickets_created = 0
        for ticket_data in sample_tickets:
            existing = db.query(Ticket).filter(
                Ticket.title == ticket_data["title"],
                Ticket.tenant_id == 1
            ).first()
            
            if not existing:
                ticket = Ticket(
                    tenant_id=1,
                    title=ticket_data["title"],
                    description=ticket_data["description"],
                    severity=ticket_data["severity"],
                    status=ticket_data["status"],
                    source=ticket_data["source"],
                    classification=ticket_data["classification"],
                    environment=ticket_data.get("environment", "prod"),  # Required field
                    service=ticket_data.get("service"),  # Optional field
                    meta_data=json.dumps({
                        "created_by": "sandbox_seed",
                        "sample": True
                    })
                )
                db.add(ticket)
                tickets_created += 1
        
        if tickets_created > 0:
            db.commit()
            print(f"✅ Created {tickets_created} sample tickets")
        else:
            print("✅ Sample tickets already exist")
        
        # Create sample runbooks
        sample_runbooks = [
            {
                "title": "Fix High CPU Usage",
                "body_md": """# Fix High CPU Usage

## Overview
Troubleshoot and resolve high CPU usage on servers.

## Steps
1. Check current CPU usage: `top` or `htop`
2. Identify processes consuming CPU
3. Review system logs for errors
4. Restart problematic services if needed
5. Monitor CPU usage after resolution
""",
                "status": "approved"
            },
            {
                "title": "Resolve Database Connection Issues",
                "body_md": """# Resolve Database Connection Issues

## Overview
Diagnose and fix database connection pool exhaustion.

## Steps
1. Check database connection pool status
2. Review active connections
3. Identify connection leaks
4. Restart database service if needed
5. Verify connection pool recovery
""",
                "status": "approved"
            }
        ]
        
        runbooks_created = 0
        for rb_data in sample_runbooks:
            existing = db.query(Runbook).filter(
                Runbook.title == rb_data["title"],
                Runbook.tenant_id == 1
            ).first()
            
            if not existing:
                runbook = Runbook(
                    tenant_id=1,
                    title=rb_data["title"],
                    body_md=rb_data["body_md"],
                    status=rb_data["status"],
                    is_active="active",
                    meta_data=json.dumps({
                        "created_by": "sandbox_seed",
                        "sample": True,
                        "service": "server",
                        "env": "prod",
                        "risk": "medium"
                    })
                )
                db.add(runbook)
                runbooks_created += 1
        
        if runbooks_created > 0:
            db.commit()
            print(f"✅ Created {runbooks_created} sample runbooks")
        else:
            print("✅ Sample runbooks already exist")
        
        print("\n🎉 Sandbox seeding completed successfully!")
        print("\n📋 Summary:")
        print(f"   - Tenant: demo (ID: 1)")
        print(f"   - User: demo@example.com / demo123")
        print(f"   - Tickets: {db.query(Ticket).filter(Ticket.tenant_id == 1).count()}")
        print(f"   - Runbooks: {db.query(Runbook).filter(Runbook.tenant_id == 1).count()}")
        print("\n🌐 Access sandbox:")
        print("   - Frontend: http://localhost:3001")
        print("   - Backend: http://localhost:8001")
        
    except Exception as e:
        print(f"❌ Error seeding sandbox data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_sandbox_data())

