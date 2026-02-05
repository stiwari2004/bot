"""
Public trial intake API - no authentication required
For future website (resolvify) connection
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.services.inquiry_service import InquiryService

router = APIRouter()


class TrialIntakeRequest(BaseModel):
    """Trial intake form payload"""

    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    company_size: Optional[str] = None
    infrastructure_type: Optional[str] = None
    itsm_tools: Optional[List[str]] = None
    monitoring_tools: Optional[List[str]] = None
    top_incident_pain: Optional[str] = None
    node_count_estimate: Optional[str] = None


class TrialIntakeResponse(BaseModel):
    """Trial intake success response"""

    id: int
    message: str = "Thank you for your request. We'll review and get back within 1-2 business days."


@router.post("/trial-intake", response_model=TrialIntakeResponse, status_code=status.HTTP_201_CREATED)
async def submit_trial_intake(
    body: TrialIntakeRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a 30-day trial intake request from the marketing site.
    Public endpoint - no authentication required.
    """
    payload = body.model_dump()
    try:
        inquiry = InquiryService.create_inquiry(payload, db)
        return TrialIntakeResponse(
            id=inquiry.id,
            message="Thank you for your request. We'll review and get back within 1-2 business days.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit your request. Please try again or email us directly.",
        ) from e
