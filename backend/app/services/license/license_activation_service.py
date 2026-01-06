"""
License activation service for PaaS deployments
Handles license key activation and validation
"""
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.tenant_subscription import TenantSubscription
from app.services.license.server_fingerprint import ServerFingerprint
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class LicenseActivationService:
    """Service for managing license activation in PaaS deployments"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_paas_mode(self) -> bool:
        """Check if running in PaaS mode"""
        return getattr(settings, "DEPLOYMENT_MODE", "saas").lower() == "paas"
    
    def generate_license_key(self) -> str:
        """
        Generate a unique license key
        
        Format: LIC-XXXXXXXX-XXXXXXXX-XXXXXXXX
        Example: LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2
        """
        import secrets
        # Generate 3 groups of 8 alphanumeric characters
        part1 = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:8]
        part2 = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:8]
        part3 = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:8]
        return f"LIC-{part1}-{part2}-{part3}"
    
    def activate_license(
        self,
        license_key: str,
        activation_ip: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Activate a license key on this server instance
        
        Args:
            license_key: License key to activate
            activation_ip: IP address performing activation
            
        Returns:
            (success, error_message, activation_info)
        """
        # Find subscription by license key
        subscription = self.db.query(TenantSubscription).filter(
            TenantSubscription.license_key == license_key
        ).first()
        
        if not subscription:
            return (False, "Invalid license key", None)
        
        # Check if already activated
        if subscription.is_activated:
            # Check if activated on this server
            current_fingerprint = ServerFingerprint.get_fingerprint()
            if subscription.server_fingerprint == current_fingerprint:
                # Already activated on this server - return success
                return (True, None, {
                    "license_key": license_key,
                    "activated_at": subscription.activated_at.isoformat() if subscription.activated_at else None,
                    "server_fingerprint": subscription.server_fingerprint,
                    "max_seats": subscription.max_seats,
                    "max_nodes": subscription.max_nodes,
                })
            else:
                # Activated on different server
                return (False, f"License key already activated on another server. Server fingerprint: {subscription.server_fingerprint[:16]}...", None)
        
        # Generate server fingerprint
        server_fingerprint = ServerFingerprint.get_fingerprint()
        hostname = ServerFingerprint.get_hostname()
        
        # Activate license
        subscription.server_fingerprint = server_fingerprint
        subscription.activated_at = datetime.now(timezone.utc)
        subscription.activation_ip = activation_ip
        
        try:
            self.db.commit()
            logger.info(f"License {license_key} activated on server {hostname} (fingerprint: {server_fingerprint[:16]}...)")
            
            return (True, None, {
                "license_key": license_key,
                "activated_at": subscription.activated_at.isoformat(),
                "server_fingerprint": server_fingerprint,
                "server_hostname": hostname,
                "max_seats": subscription.max_seats,
                "max_nodes": subscription.max_nodes,
            })
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to activate license: {e}", exc_info=True)
            return (False, f"Failed to activate license: {str(e)}", None)
    
    def validate_activation(self) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate that license is activated on this server
        
        Returns:
            (is_valid, error_message, activation_info)
        """
        if not self.is_paas_mode():
            # Not PaaS mode - no activation required
            return (True, None, {"mode": "saas"})
        
        # Find subscription with activation on this server
        current_fingerprint = ServerFingerprint.get_fingerprint()
        subscription = self.db.query(TenantSubscription).filter(
            TenantSubscription.server_fingerprint == current_fingerprint,
            TenantSubscription.license_key.isnot(None),
            TenantSubscription.activated_at.isnot(None)
        ).first()
        
        if not subscription:
            return (False, "License not activated. Please activate your license key.", None)
        
        if not subscription.is_active:
            return (False, f"License subscription is not active (status: {subscription.status})", None)
        
        return (True, None, {
            "license_key": subscription.license_key,
            "activated_at": subscription.activated_at.isoformat() if subscription.activated_at else None,
            "server_fingerprint": subscription.server_fingerprint,
            "max_seats": subscription.max_seats,
            "max_nodes": subscription.max_nodes,
            "current_seats": subscription.current_seats,
            "current_nodes": subscription.current_nodes,
        })
    
    def get_activation_status(self) -> Dict[str, Any]:
        """Get current activation status"""
        is_valid, error, info = self.validate_activation()
        
        return {
            "is_paas_mode": self.is_paas_mode(),
            "is_activated": is_valid,
            "error": error,
            "activation": info,
            "server_info": ServerFingerprint.get_system_info() if self.is_paas_mode() else None,
        }

