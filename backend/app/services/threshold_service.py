"""
Threshold Service - Manage environment-specific thresholds for metrics
"""
from typing import Dict, Optional, Any
from app.core.logging import get_logger
from app.models.runbook import Runbook

logger = get_logger(__name__)


class ThresholdService:
    """Service for managing and retrieving thresholds for metric analysis"""
    
    def get_thresholds(
        self,
        metric: str,
        environment: str,
        service: Optional[str] = None,
        tenant_id: Optional[int] = None,
        runbook: Optional[Runbook] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Get thresholds for a metric, checking database first, then runbook, then defaults
        
        Args:
            metric: Metric name (e.g., "cpu", "memory", "disk")
            environment: Environment (prod, staging, dev)
            service: Optional service name
            tenant_id: Optional tenant ID (defaults to 1)
            runbook: Optional runbook object to extract thresholds from
            db: Optional database session for loading from database
            
        Returns:
            {
                "warning": float,
                "critical": float,
                "source": "runbook" | "database" | "default"
            }
        """
        tenant_id = tenant_id or 1
        
        # Try to load from database first (if db session provided)
        if db:
            thresholds = self.load_thresholds_from_database_with_db(
                db, metric, environment, tenant_id
            )
            if thresholds:
                return {
                    **thresholds,
                    "source": "database"
                }
        
        # Try to load from runbook
        if runbook:
            thresholds = self.load_thresholds_from_runbook(runbook, metric, environment)
            if thresholds:
                return {
                    **thresholds,
                    "source": "runbook"
                }
        
        # Return defaults
        return self._get_default_thresholds(metric, environment)
    
    def load_thresholds_from_database_with_db(
        self,
        db: Any,
        metric: str,
        environment: str,
        tenant_id: int
    ) -> Optional[Dict[str, float]]:
        """
        Load thresholds from database using provided db session
        
        Args:
            db: Database session
            metric: Metric name (cpu, memory, disk, network)
            environment: Environment name (prod, staging, dev)
            tenant_id: Tenant ID
            
        Returns:
            {"warning": float, "critical": float} or None
        """
        try:
            from app.models.system_config import SystemConfig
            
            # Load warning threshold
            warning_key = f"infra_threshold_{metric}_{environment}_warning"
            warning_config = db.query(SystemConfig).filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.config_key == warning_key
            ).first()
            
            # Load critical threshold
            critical_key = f"infra_threshold_{metric}_{environment}_critical"
            critical_config = db.query(SystemConfig).filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.config_key == critical_key
            ).first()
            
            if warning_config and critical_config:
                try:
                    warning = float(warning_config.config_value)
                    critical = float(critical_config.config_value)
                    return {
                        "warning": warning,
                        "critical": critical
                    }
                except (ValueError, TypeError):
                    logger.warning(f"Invalid threshold values for {metric}/{environment}: warning={warning_config.config_value}, critical={critical_config.config_value}")
                    return None
            
            return None
        except Exception as e:
            logger.warning(f"Error loading thresholds from database: {e}")
            return None
    
    def load_thresholds_from_runbook(
        self,
        runbook: Runbook,
        metric: str,
        environment: str
    ) -> Optional[Dict[str, float]]:
        """
        Load thresholds from runbook YAML structure
        
        Args:
            runbook: Runbook object
            metric: Metric name
            environment: Environment name
            
        Returns:
            {"warning": float, "critical": float} or None
        """
        try:
            from app.services.runbook_parser import get_parser
            parser = get_parser()
            parsed = parser.parse_runbook(runbook.body_md)
            
            # Look for thresholds in prechecks
            prechecks = parsed.get("prechecks", [])
            for precheck in prechecks:
                thresholds = precheck.get("thresholds", {})
                if isinstance(thresholds, dict):
                    env_thresholds = thresholds.get(environment, {})
                    if isinstance(env_thresholds, dict):
                        # Check if this precheck is for the requested metric
                        # We can infer from command or description
                        command = precheck.get("command", "").lower()
                        description = precheck.get("description", "").lower()
                        
                        # Simple metric matching
                        metric_keywords = {
                            "cpu": ["cpu", "processor", "processor time"],
                            "memory": ["memory", "ram", "mem"],
                            "disk": ["disk", "storage", "space", "usage"],
                            "network": ["network", "bandwidth", "traffic"]
                        }
                        
                        metric_matches = metric_keywords.get(metric.lower(), [])
                        if any(keyword in command or keyword in description for keyword in metric_matches):
                            warning = env_thresholds.get("warning")
                            critical = env_thresholds.get("critical")
                            if warning is not None and critical is not None:
                                return {
                                    "warning": float(warning),
                                    "critical": float(critical)
                                }
            
            return None
        except Exception as e:
            logger.warning(f"Error loading thresholds from runbook: {e}")
            return None
    
    def load_thresholds_from_database(
        self,
        metric: str,
        environment: str,
        service: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> Optional[Dict[str, float]]:
        """
        Load thresholds from database (SystemConfig table)
        
        Args:
            metric: Metric name (cpu, memory, disk, network)
            environment: Environment name (prod, staging, dev)
            service: Optional service name (not used currently)
            tenant_id: Optional tenant ID (defaults to 1 if not provided)
            
        Returns:
            {"warning": float, "critical": float} or None
        """
        try:
            from app.models.system_config import SystemConfig
            from sqlalchemy.orm import Session
            
            # For now, we need db session passed in, but this method doesn't have it
            # We'll need to refactor get_thresholds to accept db session
            # For now, return None and let it fall back to defaults
            # This will be called from PrecheckAnalysisService which has db access
            
            return None
        except Exception as e:
            logger.warning(f"Error loading thresholds from database: {e}")
            return None
    
    def _get_default_thresholds(self, metric: str, environment: str) -> Dict[str, Any]:
        """
        Get default thresholds based on metric and environment
        
        Args:
            metric: Metric name
            environment: Environment name
            
        Returns:
            {"warning": float, "critical": float, "source": "default"}
        """
        # Default thresholds by metric and environment
        defaults = {
            "cpu": {
                "prod": {"warning": 70.0, "critical": 90.0},
                "staging": {"warning": 80.0, "critical": 95.0},
                "dev": {"warning": 90.0, "critical": 98.0}
            },
            "memory": {
                "prod": {"warning": 75.0, "critical": 90.0},
                "staging": {"warning": 85.0, "critical": 95.0},
                "dev": {"warning": 90.0, "critical": 98.0}
            },
            "disk": {
                "prod": {"warning": 80.0, "critical": 90.0},
                "staging": {"warning": 85.0, "critical": 95.0},
                "dev": {"warning": 90.0, "critical": 98.0}
            },
            "network": {
                "prod": {"warning": 70.0, "critical": 85.0},
                "staging": {"warning": 80.0, "critical": 90.0},
                "dev": {"warning": 90.0, "critical": 95.0}
            }
        }
        
        metric_lower = metric.lower()
        env_lower = environment.lower()
        
        if metric_lower in defaults and env_lower in defaults[metric_lower]:
            return {
                **defaults[metric_lower][env_lower],
                "source": "default"
            }
        
        # Generic defaults if metric/environment not found
        return {
            "warning": 80.0,
            "critical": 90.0,
            "source": "default"
        }


# Global instance
_threshold_service: Optional[ThresholdService] = None


def get_threshold_service() -> ThresholdService:
    """Get or create threshold service instance"""
    global _threshold_service
    if _threshold_service is None:
        _threshold_service = ThresholdService()
    return _threshold_service

