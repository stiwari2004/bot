"""
Super Admin inquiry management - view and approve trial intake submissions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.inquiry_service import InquiryService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class InquiryResponse(BaseModel):
    """Inquiry response"""

    id: int
    name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    company_size: Optional[str]
    infrastructure_type: Optional[str]
    itsm_tools: Optional[str]
    monitoring_tools: Optional[str]
    top_incident_pain: Optional[str]
    node_count_estimate: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True


class InquiryListResponse(BaseModel):
    """Paginated inquiry list response"""

    inquiries: List[InquiryResponse]
    total: int
    skip: int
    limit: int


class UpdateInquiryStatusRequest(BaseModel):
    """Update inquiry status"""

    status: str  # new, contacted, approved, converted, closed


@router.get("/inquiries", response_model=InquiryListResponse)
async def list_inquiries(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """List trial intake inquiries (super admin only)"""
    result = InquiryService.list_inquiries(
        skip=skip,
        limit=limit,
        status=status_filter,
        db=db,
    )

    inquiry_responses = [
        InquiryResponse(
            id=i.id,
            name=i.name,
            email=i.email,
            phone=i.phone,
            company=i.company,
            company_size=i.company_size,
            infrastructure_type=i.infrastructure_type,
            itsm_tools=i.itsm_tools,
            monitoring_tools=i.monitoring_tools,
            top_incident_pain=i.top_incident_pain,
            node_count_estimate=i.node_count_estimate,
            status=i.status,
            created_at=i.created_at.isoformat() if i.created_at else "",
        )
        for i in result["inquiries"]
    ]

    return InquiryListResponse(
        inquiries=inquiry_responses,
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"],
    )


@router.patch("/inquiries/{inquiry_id}", response_model=InquiryResponse)
async def update_inquiry_status(
    inquiry_id: int,
    body: UpdateInquiryStatusRequest,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Update inquiry status (super admin only)"""
    try:
        inquiry = InquiryService.update_inquiry_status(
            inquiry_id,
            body.status,
            db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found",
        )

    return InquiryResponse(
        id=inquiry.id,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        company=inquiry.company,
        company_size=inquiry.company_size,
        infrastructure_type=inquiry.infrastructure_type,
        itsm_tools=inquiry.itsm_tools,
        monitoring_tools=inquiry.monitoring_tools,
        top_incident_pain=inquiry.top_incident_pain,
        node_count_estimate=inquiry.node_count_estimate,
        status=inquiry.status,
        created_at=inquiry.created_at.isoformat() if inquiry.created_at else "",
    )
