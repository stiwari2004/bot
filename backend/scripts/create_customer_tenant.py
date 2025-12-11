#!/usr/bin/env python3
"""
Script to create a customer tenant with a custom slug/path
Usage: python create_customer_tenant.py --name "Customer Name" --slug "customer-name" --email "customer@example.com" --password "secure123"
"""
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_password_hash
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_customer_tenant(
    name: str,
    slug: str,
    email: str,
    password: str,
    full_name: str = None,
    description: str = None
):
    """Create a customer tenant with a custom slug"""
    db: Session = SessionLocal()
    try:
        # Check if tenant with this name or slug already exists
        existing_tenant = db.query(Tenant).filter(
            (Tenant.name == name) | (Tenant.subdomain_slug == slug)
        ).first()
        
        if existing_tenant:
            logger.error(f"Tenant with name '{name}' or slug '{slug}' already exists (ID: {existing_tenant.id})")
            return None, None
        
        # Create tenant
        tenant = Tenant(
            name=name,
            subdomain_slug=slug,
            description=description or f"Customer tenant: {name}",
            is_active=True,
            deployment_type='saas',
            platform_managed=True,
            is_msp=False
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        logger.info(f"✅ Created tenant: {tenant.name} (ID: {tenant.id}, slug: {tenant.subdomain_slug})")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.error(f"User with email '{email}' already exists")
            return tenant, None
        
        # Create admin user for this tenant
        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name or name,
            role="tenant_admin",  # Give them tenant admin role
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"✅ Created user: {user.email} (ID: {user.id}, role: {user.role})")
        
        print(f"\n{'='*60}")
        print(f"✅ Customer tenant created successfully!")
        print(f"{'='*60}")
        print(f"Tenant Name: {tenant.name}")
        print(f"Tenant ID: {tenant.id}")
        print(f"Slug/Path: /c/{tenant.subdomain_slug}")
        print(f"\nUser Email: {user.email}")
        print(f"User Password: {password}")
        print(f"User Role: {user.role}")
        print(f"\nAccess URL: https://demo.resolvify.tech/c/{tenant.subdomain_slug}")
        print(f"{'='*60}\n")
        
        return tenant, user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tenant: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a customer tenant with custom slug")
    parser.add_argument("--name", required=True, help="Tenant name (e.g., 'Acme Corp')")
    parser.add_argument("--slug", required=True, help="URL slug (e.g., 'acme-corp')")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--password", required=True, help="Admin user password")
    parser.add_argument("--full-name", help="Admin user full name (defaults to tenant name)")
    parser.add_argument("--description", help="Tenant description")
    
    args = parser.parse_args()
    
    # Validate slug (alphanumeric and hyphens only)
    if not args.slug.replace('-', '').replace('_', '').isalnum():
        print("❌ Error: Slug must contain only alphanumeric characters, hyphens, and underscores")
        sys.exit(1)
    
    try:
        tenant, user = create_customer_tenant(
            name=args.name,
            slug=args.slug,
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            description=args.description
        )
        
        if tenant and user:
            print("✅ Success!")
            sys.exit(0)
        else:
            print("❌ Failed to create tenant/user")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

