"""
Debug endpoint for authentication issues
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/debug/user/{email}")
async def debug_user(email: str, db: Session = Depends(get_db)):
    """Debug endpoint to check user status"""
    try:
        user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
        if not user:
            return {
                "found": False,
                "message": f"User with email {email} not found"
            }
        
        return {
            "found": True,
            "user_id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "failed_login_attempts": user.failed_login_attempts or 0,
            "has_password_hash": bool(user.password_hash),
            "password_hash_length": len(user.password_hash) if user.password_hash else 0,
            "password_hash_prefix": user.password_hash[:20] + "..." if user.password_hash else None,
            "tenant_id": user.tenant_id,
            "role": user.role
        }
    except Exception as e:
        logger.error(f"Error in debug_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

