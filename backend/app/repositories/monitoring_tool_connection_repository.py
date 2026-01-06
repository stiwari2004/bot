"""
Repository for monitoring tool connection data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class MonitoringToolConnectionRepository(BaseRepository[MonitoringToolConnection]):
    """Repository for monitoring tool connection CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(MonitoringToolConnection, db)
    
    def get_by_tenant_and_tool(
        self,
        tenant_id: int,
        tool_name: str,
        active_only: bool = True
    ) -> Optional[MonitoringToolConnection]:
        """
        Get monitoring tool connection by tenant and tool name
        
        Args:
            tenant_id: Tenant ID
            tool_name: Monitoring tool name (e.g., 'datadog', 'prometheus', 'solarwinds')
            active_only: Only return active connections
            
        Returns:
            MonitoringToolConnection or None
        """
        query = self.db.query(MonitoringToolConnection).filter(
            MonitoringToolConnection.tenant_id == tenant_id,
            MonitoringToolConnection.tool_name == tool_name
        )
        
        if active_only:
            query = query.filter(MonitoringToolConnection.is_active == True)
        
        return query.first()
    
    def get_all_by_tenant(
        self,
        tenant_id: int,
        active_only: bool = True
    ) -> List[MonitoringToolConnection]:
        """
        Get all monitoring tool connections for a tenant
        
        Args:
            tenant_id: Tenant ID
            active_only: Only return active connections
            
        Returns:
            List of MonitoringToolConnection
        """
        query = self.db.query(MonitoringToolConnection).filter(
            MonitoringToolConnection.tenant_id == tenant_id
        )
        
        if active_only:
            query = query.filter(MonitoringToolConnection.is_active == True)
        
        return query.all()
    
    def get_by_id_and_tenant(
        self,
        connection_id: int,
        tenant_id: int
    ) -> Optional[MonitoringToolConnection]:
        """Get monitoring tool connection by ID and tenant"""
        return self.db.query(MonitoringToolConnection).filter(
            MonitoringToolConnection.id == connection_id,
            MonitoringToolConnection.tenant_id == tenant_id
        ).first()
    
    def create_connection(
        self,
        tenant_id: int,
        tool_name: str,
        connection_type: str,
        webhook_url: Optional[str] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_username: Optional[str] = None,
        api_password: Optional[str] = None,
        application_key: Optional[str] = None,
        meta_data: Optional[str] = None,
        is_active: bool = True
    ) -> MonitoringToolConnection:
        """Create a new monitoring tool connection"""
        connection = MonitoringToolConnection(
            tenant_id=tenant_id,
            tool_name=tool_name,
            connection_type=connection_type,
            webhook_url=webhook_url,
            api_base_url=api_base_url,
            api_key=api_key,
            api_username=api_username,
            api_password=api_password,
            application_key=application_key,
            meta_data=meta_data,
            is_active=is_active
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection
    
    def update_connection(
        self,
        connection_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[MonitoringToolConnection]:
        """Update monitoring tool connection fields"""
        connection = self.get_by_id_and_tenant(connection_id, tenant_id)
        if connection:
            for key, value in kwargs.items():
                setattr(connection, key, value)
            self.db.commit()
            self.db.refresh(connection)
        return connection
    
    def update_sync_status(
        self,
        connection_id: int,
        tenant_id: int,
        status: str,
        error: Optional[str] = None
    ) -> Optional[MonitoringToolConnection]:
        """
        Update last sync status and error for a connection
        
        Args:
            connection_id: Connection ID
            tenant_id: Tenant ID
            status: Sync status ('success', 'failed', 'pending')
            error: Optional error message
        """
        from datetime import datetime, timezone
        
        connection = self.get_by_id_and_tenant(connection_id, tenant_id)
        if connection:
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = status
            if error:
                connection.last_error = error
            self.db.commit()
            self.db.refresh(connection)
        return connection

