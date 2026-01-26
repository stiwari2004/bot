"""
Connector Health Service
Tracks health status of monitoring, ticketing, and infrastructure connectors
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.logging import get_logger
from app.models.credential import InfrastructureConnection
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession

logger = get_logger(__name__)


class ConnectorHealthService:
    """Service for tracking connector health and status"""
    
    def __init__(self, db: Session, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id
    
    def get_connector_health_summary(self) -> Dict[str, Any]:
        """
        Get overall connector health summary
        
        Returns:
            Dict with health metrics for all connector types
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # Get infrastructure connections
        query = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.is_active == True
        )
        if self.tenant_id:
            query = query.filter(InfrastructureConnection.tenant_id == self.tenant_id)
        
        connections = query.all()
        
        # Calculate health metrics
        total_connections = len(connections)
        healthy_connections = 0
        degraded_connections = 0
        failed_connections = 0
        
        connection_details = []
        
        for conn in connections:
            # Check last usage (proxy for health)
            # In production, this would check actual connectivity/API status
            health_status = self._assess_connection_health(conn, one_hour_ago, twenty_four_hours_ago)
            
            if health_status["status"] == "healthy":
                healthy_connections += 1
            elif health_status["status"] == "degraded":
                degraded_connections += 1
            else:
                failed_connections += 1
            
            connection_details.append({
                "id": conn.id,
                "name": conn.name,
                "type": conn.connection_type,
                "status": health_status["status"],
                "last_success": health_status.get("last_success"),
                "error_rate_1h": health_status.get("error_rate_1h", 0),
                "error_rate_24h": health_status.get("error_rate_24h", 0),
            })
        
        return {
            "total_connections": total_connections,
            "healthy": healthy_connections,
            "degraded": degraded_connections,
            "failed": failed_connections,
            "health_percentage": round((healthy_connections / total_connections * 100) if total_connections > 0 else 0, 1),
            "connections": connection_details,
            "timestamp": now.isoformat()
        }
    
    def _assess_connection_health(
        self,
        connection: InfrastructureConnection,
        one_hour_ago: datetime,
        twenty_four_hours_ago: datetime
    ) -> Dict[str, Any]:
        """
        Assess health of a single connection
        
        Returns:
            Dict with status, last_success, error rates
        """
        # Check recent ticket creation (indicates connector is working)
        recent_tickets = self.db.query(Ticket).filter(
            Ticket.tenant_id == connection.tenant_id,
            Ticket.created_at >= one_hour_ago
        ).count()
        
        # Check recent executions using this connection
        recent_executions = self.db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == connection.tenant_id,
            ExecutionSession.created_at >= one_hour_ago
        ).count()
        
        # Simple heuristic: if we have recent activity, connector is healthy
        # In production, this would check actual API connectivity, token expiry, etc.
        has_recent_activity = recent_tickets > 0 or recent_executions > 0
        
        # Check last_used_at if available
        last_used = connection.credential.last_used_at if connection.credential else None
        
        if has_recent_activity or (last_used and last_used >= one_hour_ago):
            return {
                "status": "healthy",
                "last_success": last_used.isoformat() if last_used else datetime.now(timezone.utc).isoformat(),
                "error_rate_1h": 0.0,
                "error_rate_24h": 0.0,
            }
        elif last_used and last_used >= twenty_four_hours_ago:
            return {
                "status": "degraded",
                "last_success": last_used.isoformat(),
                "error_rate_1h": 0.0,
                "error_rate_24h": 5.0,  # Estimated
            }
        else:
            return {
                "status": "failed",
                "last_success": last_used.isoformat() if last_used else None,
                "error_rate_1h": 100.0,
                "error_rate_24h": 100.0,
            }
    
    def get_monitoring_connector_health(self) -> Dict[str, Any]:
        """Get health status for monitoring connectors specifically"""
        # This would check actual monitoring API connectivity
        # For now, return placeholder
        return {
            "datadog": {"status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "solarwinds": {"status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
        }
    
    def get_ticketing_connector_health(self) -> Dict[str, Any]:
        """Get health status for ticketing connectors specifically"""
        # This would check actual ticketing API connectivity
        # For now, return placeholder
        return {
            "servicenow": {"status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "zendesk": {"status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
        }
