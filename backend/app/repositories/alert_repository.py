"""
Repository for alert data access
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.alert import Alert
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertRepository(BaseRepository[Alert]):
    """Repository for alert CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(Alert, db)
    
    def get_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get all alerts for a tenant, optionally filtered by status and source"""
        try:
            query = self.db.query(Alert).filter(Alert.tenant_id == tenant_id)
            
            if status:
                query = query.filter(Alert.status == status)
            
            if source:
                query = query.filter(Alert.source == source)
            
            return query.order_by(Alert.received_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting alerts by tenant: {e}", exc_info=True)
            return []
    
    def get_by_id_and_tenant(
        self,
        alert_id: int,
        tenant_id: int
    ) -> Optional[Alert]:
        """Get alert by ID and tenant"""
        return self.db.query(Alert).filter(
            and_(
                Alert.id == alert_id,
                Alert.tenant_id == tenant_id
            )
        ).first()
    
    def create_alert(
        self,
        tenant_id: int,
        source: str,
        external_id: Optional[str],
        title: str,
        description: Optional[str],
        severity: str,
        environment: str,
        service: Optional[str],
        status: str,
        raw_payload: Optional[Dict[str, Any]],
        meta_data: Optional[Dict[str, Any]],
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
        received_at: Optional[datetime] = None
    ) -> Alert:
        """Create a new alert with all fields"""
        alert = Alert(
            tenant_id=tenant_id,
            source=source,
            external_id=external_id,
            title=title,
            description=description,
            severity=severity,
            environment=environment,
            service=service,
            status=status,
            raw_payload=raw_payload,
            meta_data=meta_data,
            starts_at=starts_at,
            ends_at=ends_at,
            received_at=received_at or datetime.now(timezone.utc)
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def update_alert(
        self,
        alert_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[Alert]:
        """Update alert fields"""
        alert = self.get_by_id_and_tenant(alert_id, tenant_id)
        if alert:
            for key, value in kwargs.items():
                setattr(alert, key, value)
            self.db.commit()
            self.db.refresh(alert)
        return alert
    
    def update_alert_metadata(
        self,
        alert_id: int,
        tenant_id: int,
        meta_data: Dict[str, Any]
    ) -> Optional[Alert]:
        """Update alert metadata"""
        alert = self.get_by_id_and_tenant(alert_id, tenant_id)
        if alert:
            if not alert.meta_data:
                alert.meta_data = {}
            alert.meta_data.update(meta_data)
            self.db.commit()
            self.db.refresh(alert)
        return alert

