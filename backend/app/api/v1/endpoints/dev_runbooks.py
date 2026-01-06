"""
Dev Runbook Management Endpoints
Endpoints for managing runbooks in the dev environment
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.runbook import Runbook
from app.services.runbook_promotion_service import get_runbook_promotion_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/dev/runbooks")
async def list_dev_runbooks(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all runbooks in dev environment
    
    Args:
        status_filter: Filter by status (draft, approved, archived)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of dev runbooks
    """
    try:
        query = db.query(Runbook).filter(
            Runbook.tenant_id == current_user.tenant_id,
            Runbook.environment == "dev"
        )
        
        if status_filter:
            query = query.filter(Runbook.status == status_filter)
        
        runbooks = query.order_by(Runbook.created_at.desc()).all()
        
        return {
            "runbooks": [
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "confidence": float(r.confidence) if r.confidence else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "promoted_from_id": r.promoted_from_id,
                    "promoted_at": r.promoted_at.isoformat() if r.promoted_at else None,
                }
                for r in runbooks
            ],
            "total": len(runbooks)
        }
    except Exception as e:
        logger.error(f"Error listing dev runbooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dev runbooks: {str(e)}"
        )


@router.get("/dev/runbooks/{runbook_id}")
async def get_dev_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific dev runbook
    
    Args:
        runbook_id: Runbook ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Runbook details
    """
    try:
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id,
            Runbook.environment == "dev"
        ).first()
        
        if not runbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dev runbook not found"
            )
        
        # Get promotion history
        promotion_service = get_runbook_promotion_service()
        promotion_history = promotion_service.get_promotion_history(
            db, runbook_id, current_user.tenant_id
        )
        
        return {
            "id": runbook.id,
            "title": runbook.title,
            "body_md": runbook.body_md,
            "meta_data": runbook.meta_data,
            "status": runbook.status,
            "confidence": float(runbook.confidence) if runbook.confidence else None,
            "environment": runbook.environment,
            "created_at": runbook.created_at.isoformat() if runbook.created_at else None,
            "updated_at": runbook.updated_at.isoformat() if runbook.updated_at else None,
            "promotion_history": promotion_history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dev runbook {runbook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dev runbook: {str(e)}"
        )


@router.post("/dev/runbooks/{runbook_id}/promote")
async def promote_runbook(
    runbook_id: int,
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Promote a runbook from dev to production
    
    Args:
        runbook_id: Dev runbook ID to promote
        dry_run: If True, validate but don't promote
        db: Database session
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Promotion result
    """
    try:
        # Check if user has admin permissions (super admin or tenant admin)
        # Super admin can promote any runbook, tenant admin can promote runbooks in their tenant
        is_admin = (
            current_user.role == "super_admin" or 
            current_user.role == "tenant_admin" or
            current_user.role == "msp_admin"
        )
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required to promote runbooks to production"
            )
        
        promotion_service = get_runbook_promotion_service()
        
        if dry_run:
            # Validate only
            is_valid, error_msg = promotion_service.validate_runbook_for_promotion(
                db, runbook_id, current_user.tenant_id
            )
            return {
                "valid": is_valid,
                "error": error_msg,
                "dry_run": True
            }
        
        # Promote runbook
        prod_runbook, error_msg = promotion_service.promote_runbook(
            db=db,
            dev_runbook_id=runbook_id,
            tenant_id=current_user.tenant_id,
            approved_by=current_user.id,
            dry_run=False
        )
        
        if error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return {
            "success": True,
            "dev_runbook_id": runbook_id,
            "production_runbook_id": prod_runbook.id,
            "promoted_at": prod_runbook.promoted_at.isoformat() if prod_runbook.promoted_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting runbook {runbook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote runbook: {str(e)}"
        )


@router.get("/dev/runbooks/pending-promotion")
async def get_pending_promotion_runbooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get runbooks pending promotion (approved in dev, not yet promoted)
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of runbooks pending promotion
    """
    try:
        # Get approved dev runbooks that haven't been promoted
        approved_dev_runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == current_user.tenant_id,
            Runbook.environment == "dev",
            Runbook.status == "approved"
        ).all()
        
        pending = []
        for runbook in approved_dev_runbooks:
            # Check if already promoted
            existing_prod = db.query(Runbook).filter(
                Runbook.promoted_from_id == runbook.id,
                Runbook.environment == "production"
            ).first()
            
            if not existing_prod:
                # Validate
                promotion_service = get_runbook_promotion_service()
                is_valid, error_msg = promotion_service.validate_runbook_for_promotion(
                    db, runbook.id, current_user.tenant_id
                )
                
                pending.append({
                    "id": runbook.id,
                    "title": runbook.title,
                    "status": runbook.status,
                    "confidence": float(runbook.confidence) if runbook.confidence else None,
                    "created_at": runbook.created_at.isoformat() if runbook.created_at else None,
                    "valid_for_promotion": is_valid,
                    "validation_error": error_msg
                })
        
        return {
            "pending": pending,
            "total": len(pending)
        }
        
    except Exception as e:
        logger.error(f"Error getting pending promotion runbooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending promotion runbooks: {str(e)}"
        )

