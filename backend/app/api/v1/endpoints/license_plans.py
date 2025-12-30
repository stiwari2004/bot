"""
License Plan management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.license_plan import LicensePlan
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.license_service import LicenseService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class LicensePlanCreate(BaseModel):
    plan_key: str
    plan_name: str
    description: Optional[str] = None
    default_max_seats: int = 0
    default_max_nodes: int = 0
    default_monthly_price: Optional[str] = None
    features: dict = {}
    display_order: int = 0


class LicensePlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    description: Optional[str] = None
    default_max_seats: Optional[int] = None
    default_max_nodes: Optional[int] = None
    default_monthly_price: Optional[str] = None
    features: Optional[dict] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class LicensePlanResponse(BaseModel):
    id: int
    plan_key: str
    plan_name: str
    description: Optional[str]
    default_max_seats: int
    default_max_nodes: int
    default_monthly_price: Optional[str]
    features: dict
    is_active: bool
    is_system_plan: bool
    is_custom: bool
    display_order: int
    created_at: str


@router.get("/", response_model=List[LicensePlanResponse])
async def list_license_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    include_system: bool = Query(True),
    include_custom: bool = Query(True),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all license plans"""
    try:
        query = db.query(LicensePlan)
        
        if is_active is not None:
            query = query.filter(LicensePlan.is_active == is_active)
        if not include_system:
            query = query.filter(LicensePlan.is_system_plan == False)
        if not include_custom:
            query = query.filter(LicensePlan.is_custom == False)
        
        query = query.order_by(LicensePlan.display_order, LicensePlan.plan_name)
        plans = query.offset(skip).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "plan_key": p.plan_key,
                "plan_name": p.plan_name,
                "description": p.description,
                "default_max_seats": p.default_max_seats,
                "default_max_nodes": p.default_max_nodes,
                "default_monthly_price": p.default_monthly_price,
                "features": p.features or {},
                "is_active": p.is_active,
                "is_system_plan": p.is_system_plan,
                "is_custom": p.is_custom,
                "display_order": p.display_order,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"Error listing license plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list license plans: {str(e)}")


@router.get("/{plan_id}", response_model=LicensePlanResponse)
async def get_license_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get a specific license plan"""
    try:
        plan = db.query(LicensePlan).filter(LicensePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="License plan not found")
        
        return {
            "id": plan.id,
            "plan_key": plan.plan_key,
            "plan_name": plan.plan_name,
            "description": plan.description,
            "default_max_seats": plan.default_max_seats,
            "default_max_nodes": plan.default_max_nodes,
            "default_monthly_price": plan.default_monthly_price,
            "features": plan.features or {},
            "is_active": plan.is_active,
            "is_system_plan": plan.is_system_plan,
            "is_custom": plan.is_custom,
            "display_order": plan.display_order,
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting license plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get license plan: {str(e)}")


@router.post("/", response_model=LicensePlanResponse)
async def create_license_plan(
    plan_data: LicensePlanCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new custom license plan"""
    try:
        # Check if plan_key already exists
        existing = db.query(LicensePlan).filter(LicensePlan.plan_key == plan_data.plan_key).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"License plan with key '{plan_data.plan_key}' already exists")
        
        plan = LicensePlan(
            plan_key=plan_data.plan_key,
            plan_name=plan_data.plan_name,
            description=plan_data.description,
            default_max_seats=plan_data.default_max_seats,
            default_max_nodes=plan_data.default_max_nodes,
            default_monthly_price=plan_data.default_monthly_price,
            features=plan_data.features,
            is_active=True,
            is_system_plan=False,
            is_custom=True,
            display_order=plan_data.display_order
        )
        
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        logger.info(f"Super admin {current_admin.email} created license plan: {plan.plan_key}")
        
        return {
            "id": plan.id,
            "plan_key": plan.plan_key,
            "plan_name": plan.plan_name,
            "description": plan.description,
            "default_max_seats": plan.default_max_seats,
            "default_max_nodes": plan.default_max_nodes,
            "default_monthly_price": plan.default_monthly_price,
            "features": plan.features or {},
            "is_active": plan.is_active,
            "is_system_plan": plan.is_system_plan,
            "is_custom": plan.is_custom,
            "display_order": plan.display_order,
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating license plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create license plan: {str(e)}")


@router.put("/{plan_id}", response_model=LicensePlanResponse)
async def update_license_plan(
    plan_id: int,
    plan_data: LicensePlanUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a license plan (custom plans only)"""
    try:
        plan = db.query(LicensePlan).filter(LicensePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="License plan not found")
        
        # Don't allow modifying system plans (except is_active)
        if plan.is_system_plan and plan_data.features is not None:
            raise HTTPException(status_code=400, detail="Cannot modify features of system plans. Create a custom plan instead.")
        
        if plan_data.plan_name is not None:
            plan.plan_name = plan_data.plan_name
        if plan_data.description is not None:
            plan.description = plan_data.description
        if plan_data.default_max_seats is not None:
            plan.default_max_seats = plan_data.default_max_seats
        if plan_data.default_max_nodes is not None:
            plan.default_max_nodes = plan_data.default_max_nodes
        if plan_data.default_monthly_price is not None:
            plan.default_monthly_price = plan_data.default_monthly_price
        if plan_data.features is not None:
            plan.features = plan_data.features
        if plan_data.is_active is not None:
            plan.is_active = plan_data.is_active
        if plan_data.display_order is not None:
            plan.display_order = plan_data.display_order
        
        db.commit()
        db.refresh(plan)
        
        logger.info(f"Super admin {current_admin.email} updated license plan: {plan.plan_key}")
        
        return {
            "id": plan.id,
            "plan_key": plan.plan_key,
            "plan_name": plan.plan_name,
            "description": plan.description,
            "default_max_seats": plan.default_max_seats,
            "default_max_nodes": plan.default_max_nodes,
            "default_monthly_price": plan.default_monthly_price,
            "features": plan.features or {},
            "is_active": plan.is_active,
            "is_system_plan": plan.is_system_plan,
            "is_custom": plan.is_custom,
            "display_order": plan.display_order,
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating license plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update license plan: {str(e)}")


@router.post("/initialize")
async def initialize_license_plans(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Initialize default license plans (idempotent)"""
    try:
        LicenseService.initialize_default_plans(db)
        return {"message": "Default license plans initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing license plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize license plans: {str(e)}")


@router.get("/features/list")
async def list_available_features(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all available features that can be assigned to plans"""
    return {
        "features": LicenseService.FEATURES
    }



