"""
Inquiry Service - Business logic for trial intake submissions
"""
import json
from sqlalchemy.orm import Session
from typing import Optional, List, Dict

from app.models.inquiry import Inquiry
from app.core.logging import get_logger

logger = get_logger(__name__)


class InquiryService:
    """Service for trial intake inquiry operations"""

    @staticmethod
    def create_inquiry(payload: Dict, db: Session) -> Inquiry:
        """Create a new inquiry from trial intake form payload"""
        itsm_tools_str = None
        if payload.get("itsm_tools"):
            arr = payload["itsm_tools"]
            if isinstance(arr, list):
                itsm_tools_str = json.dumps(arr)
            else:
                itsm_tools_str = str(arr)

        monitoring_tools_str = None
        if payload.get("monitoring_tools"):
            arr = payload["monitoring_tools"]
            if isinstance(arr, list):
                monitoring_tools_str = json.dumps(arr)
            else:
                monitoring_tools_str = str(arr)

        inquiry = Inquiry(
            name=payload.get("name", "").strip(),
            email=payload.get("email", "").strip(),
            phone=payload.get("phone") or None,
            company=payload.get("company") or None,
            company_size=payload.get("company_size") or None,
            infrastructure_type=payload.get("infrastructure_type") or None,
            itsm_tools=itsm_tools_str,
            monitoring_tools=monitoring_tools_str,
            top_incident_pain=payload.get("top_incident_pain") or None,
            node_count_estimate=payload.get("node_count_estimate") or None,
            status="new",
        )
        db.add(inquiry)
        db.commit()
        db.refresh(inquiry)
        logger.info(f"Created inquiry {inquiry.id} from {inquiry.email}")
        return inquiry

    @staticmethod
    def list_inquiries(
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict:
        """List inquiries with pagination and optional status filter"""
        query = db.query(Inquiry)

        if status:
            query = query.filter(Inquiry.status == status)

        total = query.count()
        inquiries = query.order_by(Inquiry.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "inquiries": inquiries,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @staticmethod
    def update_inquiry_status(inquiry_id: int, status: str, db: Session) -> Optional[Inquiry]:
        """Update inquiry status. Returns None if not found."""
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            return None

        valid_statuses = {"new", "contacted", "approved", "converted", "closed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        inquiry.status = status
        db.commit()
        db.refresh(inquiry)
        logger.info(f"Updated inquiry {inquiry_id} status to {status}")
        return inquiry
