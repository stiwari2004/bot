"""
Rollback Manager for Network Device Configurations
Stores config backups and manages rollback operations
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.logging import get_logger

logger = get_logger(__name__)


class NetworkRollbackManager:
    """Manage configuration backups and rollbacks for network devices"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def store_backup(
        self,
        device_id: int,
        config_text: str,
        execution_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> int:
        """
        Store a configuration backup
        
        Args:
            device_id: Network device ID
            config_text: Configuration text
            execution_id: Optional execution ID that triggered this backup
            session_id: Optional session ID
        
        Returns:
            Backup record ID
        """
        try:
            # Store in network_device_config_backups table (to be created)
            # For now, we'll store in device meta_data as a workaround
            from app.models.network_device import NetworkDevice
            
            device = self.db.query(NetworkDevice).filter(NetworkDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")
            
            # Update last_config_backup timestamp
            device.last_config_backup = datetime.utcnow()
            
            # Store backup in meta_data
            if not device.meta_data:
                device.meta_data = {}
            
            backup_key = f"backup_{datetime.utcnow().isoformat()}"
            if 'config_backups' not in device.meta_data:
                device.meta_data['config_backups'] = {}
            
            device.meta_data['config_backups'][backup_key] = {
                'config': config_text,
                'timestamp': datetime.utcnow().isoformat(),
                'execution_id': execution_id,
                'session_id': session_id,
                'size': len(config_text)
            }
            
            # Keep only last 10 backups
            backups = device.meta_data.get('config_backups', {})
            if len(backups) > 10:
                # Remove oldest backup
                sorted_keys = sorted(backups.keys())
                oldest_key = sorted_keys[0]
                del backups[oldest_key]
            
            self.db.commit()
            
            logger.info(f"Stored config backup for device {device_id} (backup_key={backup_key})")
            return device_id  # Return device_id as backup_id for now
            
        except Exception as e:
            logger.error(f"Error storing config backup: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def get_latest_backup(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent configuration backup for a device"""
        try:
            from app.models.network_device import NetworkDevice
            
            device = self.db.query(NetworkDevice).filter(NetworkDevice.id == device_id).first()
            if not device or not device.meta_data:
                return None
            
            backups = device.meta_data.get('config_backups', {})
            if not backups:
                return None
            
            # Get most recent backup
            sorted_keys = sorted(backups.keys(), reverse=True)
            if sorted_keys:
                latest_key = sorted_keys[0]
                backup_data = backups[latest_key].copy()
                backup_data['backup_key'] = latest_key
                return backup_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving config backup: {e}", exc_info=True)
            return None
    
    def list_backups(self, device_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """List all configuration backups for a device"""
        try:
            from app.models.network_device import NetworkDevice
            
            device = self.db.query(NetworkDevice).filter(NetworkDevice.id == device_id).first()
            if not device or not device.meta_data:
                return []
            
            backups = device.meta_data.get('config_backups', {})
            if not backups:
                return []
            
            # Sort by timestamp (newest first)
            sorted_items = sorted(
                backups.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            
            result = []
            for backup_key, backup_data in sorted_items[:limit]:
                result.append({
                    'backup_key': backup_key,
                    **backup_data
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing config backups: {e}", exc_info=True)
            return []









