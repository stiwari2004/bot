"""
Test authentication endpoints for demo purposes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()


@router.post("/create-test-user")
async def create_test_user(db: Session = Depends(get_db)):
    """Create a test user for demo purposes"""
    try:
        # Create test tenant if it doesn't exist
        test_tenant = db.query(Tenant).filter(Tenant.name == "test").first()
        if not test_tenant:
            test_tenant = Tenant(
                name="test",
                description="Test tenant for demo",
                is_active=True
            )
            db.add(test_tenant)
            db.commit()
            db.refresh(test_tenant)
        
        # Create test user if it doesn't exist
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            from app.services.auth import get_password_hash
            test_user = User(
                tenant_id=test_tenant.id,
                email="test@example.com",
                password_hash=get_password_hash("test123"[:72]),
                full_name="Test User",
                role="admin",
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        return {
            "message": "Test user created successfully",
            "user_id": test_user.id,
            "tenant_id": test_user.tenant_id,
            "email": test_user.email
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test user: {str(e)}")


@router.get("/test-login")
async def test_login(db: Session = Depends(get_db)):
    """Get test user credentials"""
    try:
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            raise HTTPException(status_code=404, detail="Test user not found")
        
        return {
            "email": "test@example.com",
            "password": "test123",
            "user_id": test_user.id,
            "tenant_id": test_user.tenant_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get test user: {str(e)}")
