"""
Repository for ticketing tool connection data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketingConnectionRepository(BaseRepository[TicketingToolConnection]):
    """Repository for TicketingToolConnection CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(TicketingToolConnection, db)

    def list_for_tenant(self, tenant_id: int) -> List[TicketingToolConnection]:
        """List all connections for a tenant ordered by tool name"""
        return self.db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id,
        ).order_by(TicketingToolConnection.tool_name).all()

    def get_by_id_and_tenant(
        self, connection_id: int, tenant_id: int
    ) -> Optional[TicketingToolConnection]:
        """Get connection by id scoped to tenant"""
        return self.db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id,
        ).first()

    def get_by_id(self, connection_id: int) -> Optional[TicketingToolConnection]:
        """Get connection by id without tenant filter (for public OAuth callbacks)"""
        return self.db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
        ).first()
