"""
Configuration service for managing system settings
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.system_config import SystemConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConfigService:
    """Manage system configuration with tenant-specific overrides"""
    
    @staticmethod
    def get_config(db: Session, tenant_id: int, key: str, default: str = None) -> str:
        """Get configuration value for tenant"""
        try:
            config = db.query(SystemConfig).filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.config_key == key
            ).first()
            
            if config:
                return config.config_value
            elif default is not None:
                return default
            else:
                logger.warning(f"Config key '{key}' not found for tenant {tenant_id} and no default provided")
                return None
        except Exception as e:
            logger.error(f"Error getting config {key} for tenant {tenant_id}: {e}")
            return default
        
    @staticmethod
    def set_config(db: Session, tenant_id: int, key: str, value: str, description: str = None) -> None:
        """Update or create configuration value"""
        try:
            config = db.query(SystemConfig).filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.config_key == key
            ).first()
            
            if config:
                config.config_value = value
                if description:
                    config.description = description
            else:
                config = SystemConfig(
                    tenant_id=tenant_id,
                    config_key=key,
                    config_value=value,
                    description=description
                )
                db.add(config)
            
            db.commit()
            logger.info(f"Config {key} updated to {value} for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Error setting config {key} for tenant {tenant_id}: {e}")
            db.rollback()
            raise
        
    @staticmethod
    def get_confidence_threshold(db: Session, tenant_id: int) -> float:
        """Get threshold for suggesting existing runbook"""
        threshold_str = ConfigService.get_config(
            db, 
            tenant_id, 
            'confidence_threshold_existing', 
            default='0.75'
        )
        try:
            return float(threshold_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid confidence_threshold_existing value: {threshold_str}, using default 0.75")
            return 0.75
        
    @staticmethod
    def get_duplicate_threshold(db: Session, tenant_id: int) -> float:
        """Get threshold for duplicate detection"""
        threshold_str = ConfigService.get_config(
            db, 
            tenant_id, 
            'confidence_threshold_duplicate', 
            default='0.80'
        )
        try:
            return float(threshold_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid confidence_threshold_duplicate value: {threshold_str}, using default 0.80")
            return 0.80
    
    @staticmethod
    def get_min_success_rate(db: Session, tenant_id: int) -> float:
        """Get minimum success rate threshold"""
        threshold_str = ConfigService.get_config(
            db, 
            tenant_id, 
            'min_runbook_success_rate', 
            default='0.70'
        )
        try:
            return float(threshold_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid min_runbook_success_rate value: {threshold_str}, using default 0.70")
            return 0.70
    
    @staticmethod
    def get_all_configs(db: Session, tenant_id: int) -> dict:
        """Get all configurations for tenant as dictionary"""
        configs = db.query(SystemConfig).filter(SystemConfig.tenant_id == tenant_id).all()
        return {config.config_key: config.config_value for config in configs}
    
    @staticmethod
    def get_execution_mode(db: Session, tenant_id: int) -> str:
        """Get execution mode: 'hil' (always require approval) or 'auto' (use threshold)"""
        mode = ConfigService.get_config(
            db,
            tenant_id,
            'execution_mode',
            default='auto'  # Default to auto mode for backward compatibility
        )
        return mode.lower() if mode else 'auto'
    
    @staticmethod
    def set_execution_mode(db: Session, tenant_id: int, mode: str) -> None:
        """Set execution mode: 'hil' or 'auto'"""
        if mode.lower() not in ['hil', 'auto']:
            raise ValueError("Execution mode must be 'hil' or 'auto'")
        ConfigService.set_config(
            db,
            tenant_id,
            'execution_mode',
            mode.lower(),
            description='Execution mode: hil (always require approval) or auto (use threshold)'
        )

