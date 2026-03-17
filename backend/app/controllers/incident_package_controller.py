"""
IncidentPackageController
Handles HTTP requests for incident package operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.incident_package_repository import IncidentPackageRepository
from app.services.incident.incident_package_service import IncidentPackageService
from app.core.logging import get_logger

logger = get_logger(__name__)


class IncidentPackageController(BaseController):
    """Controller for incident package operations"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.package_repo = IncidentPackageRepository(db)
        self.package_service = IncidentPackageService()

    def generate_package(
        self,
        ticket_id: int,
        session_id: Optional[int],
        generated_by: int,
    ) -> Dict[str, Any]:
        """Generate incident package"""
        try:
            package = self.package_service.generate_package(
                db=self.db,
                ticket_id=ticket_id,
                session_id=session_id,
                generated_by=generated_by,
                tenant_id=self.tenant_id,
            )
            return {
                "package_id": package.id,
                "ticket_id": ticket_id,
                "session_id": session_id,
                "generated_at": package.generated_at.isoformat() if package.generated_at else None,
                "message": "Incident package generated successfully",
            }

        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error generating incident package for ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to generate incident package")

    def get_package(self, ticket_id: int) -> Dict[str, Any]:
        """Get incident package for a ticket"""
        try:
            package = self.package_repo.get_latest_for_ticket(ticket_id, self.tenant_id)
            if not package:
                raise self.not_found("Incident package", ticket_id)

            return {
                "id": package.id,
                "ticket_id": package.ticket_id,
                "session_id": package.session_id,
                "incident_start_time": package.incident_start_time.isoformat() if package.incident_start_time else None,
                "incident_end_time": package.incident_end_time.isoformat() if package.incident_end_time else None,
                "resolution_time_minutes": package.resolution_time_minutes,
                "root_cause_analysis": package.root_cause_analysis,
                "timeline": package.timeline,
                "actions_taken": package.actions_taken,
                "lessons_learned": package.lessons_learned,
                "recommendations": package.recommendations,
                "compliance_data": package.compliance_data,
                "generated_at": package.generated_at.isoformat() if package.generated_at else None,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting incident package for ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to get incident package")

    def list_packages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all incident packages"""
        try:
            packages = self.package_repo.list_for_tenant(self.tenant_id, limit=limit)
            return [
                {
                    "id": p.id,
                    "ticket_id": p.ticket_id,
                    "session_id": p.session_id,
                    "generated_at": p.generated_at.isoformat() if p.generated_at else None,
                    "resolution_time_minutes": p.resolution_time_minutes,
                }
                for p in packages
            ]

        except Exception as e:
            logger.error(f"Error listing incident packages: {e}")
            raise self.handle_error(e, "Failed to list incident packages")
