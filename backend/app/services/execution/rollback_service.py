"""
Rollback service for execution steps
Includes network device configuration backup and rollback (using InfrastructureConnection)
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import json
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.credential import InfrastructureConnection
from app.services.infrastructure import get_connector
from app.services.network.device_executor import NetworkDeviceExecutor
from app.core.logging import get_logger

logger = get_logger(__name__)


class RollbackService:
    """Handles rollback operations for execution steps"""
    
    def __init__(self, connection_service):
        self.connection_service = connection_service
        self.network_executor = NetworkDeviceExecutor()
    
    async def backup_network_device_config(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep,
        connection_config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Backup network device configuration before making changes
        
        Returns:
            Backup config text or None if not a network device or backup fails
        """
        try:
            connector_type = connection_config.get("connector_type", "")
            if connector_type != "network_device":
                return None  # Not a network device
            
            connection_id = connection_config.get("connection_id")
            if not connection_id:
                logger.warning("Connection ID not found in connection config, skipping backup")
                return None
            
            # Get InfrastructureConnection
            connection = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.id == connection_id
            ).first()
            
            if not connection:
                logger.warning(f"InfrastructureConnection {connection_id} not found, skipping backup")
                return None
            
            # Build device dict for executor
            device = {
                'management_ip': connection.target_host,
                'management_port': connection.target_port or 22,
                'connection_protocol': 'ssh',  # Default
                'vendor': None,
                'model': None,
                'name': connection.name
            }
            
            # Extract network device metadata
            if connection.meta_data:
                try:
                    meta = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
                    device['vendor'] = meta.get('vendor')
                    device['model'] = meta.get('model')
                except:
                    pass
            
            # Get credential
            credential_info = None
            if connection.credential_id and connection.credential:
                # Decrypt password using credential service
                from app.services.credential_service import get_credential_service
                credential_service = get_credential_service()
                try:
                    decrypted = credential_service.get_credential(db, connection.credential.id, session.tenant_id)
                    if decrypted:
                        credential_info = {
                            'username': decrypted.get('username') or connection.credential.username,
                            'password': decrypted.get('password'),  # Now properly decrypted
                        }
                    else:
                        logger.warning(f"Failed to decrypt credential {connection.credential.id} for backup")
                except Exception as e:
                    logger.error(f"Error decrypting credential {connection.credential.id} for backup: {e}", exc_info=True)
            
            # Backup config
            backup_config = await self.network_executor.backup_config(device, credential_info)
            
            if backup_config:
                # Store backup in connection meta_data
                meta = {}
                if connection.meta_data:
                    try:
                        meta = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
                    except:
                        pass
                
                if 'config_backups' not in meta:
                    meta['config_backups'] = {}
                
                backup_key = f"backup_{datetime.utcnow().isoformat()}"
                meta['config_backups'][backup_key] = {
                    'config': backup_config,
                    'timestamp': datetime.utcnow().isoformat(),
                    'execution_id': session.id,
                    'session_id': session.id,
                    'size': len(backup_config)
                }
                
                # Keep only last 10 backups
                backups = meta.get('config_backups', {})
                if len(backups) > 10:
                    sorted_keys = sorted(backups.keys())
                    oldest_key = sorted_keys[0]
                    del backups[oldest_key]
                
                connection.meta_data = json.dumps(meta)
                db.commit()
                
                logger.info(f"Backed up config for connection {connection_id} before step {step.step_number}")
                return backup_config
            else:
                logger.warning(f"Failed to backup config for connection {connection_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error backing up network device config: {e}", exc_info=True)
            return None
    
    async def rollback_network_device_config(
        self,
        db: Session,
        session: ExecutionSession,
        connection_id: int
    ) -> bool:
        """
        Rollback network device to previous configuration
        
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            # Get InfrastructureConnection
            connection = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.id == connection_id
            ).first()
            
            if not connection:
                logger.error(f"Connection {connection_id} not found")
                return False
            
            # Get latest backup from meta_data
            meta = {}
            if connection.meta_data:
                try:
                    meta = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
                except:
                    pass
            
            backups = meta.get('config_backups', {})
            if not backups:
                logger.warning(f"No backup found for connection {connection_id}")
                return False
            
            # Get most recent backup
            sorted_keys = sorted(backups.keys(), reverse=True)
            if not sorted_keys:
                logger.warning(f"No backup found for connection {connection_id}")
                return False
            
            latest_key = sorted_keys[0]
            backup = backups[latest_key]
            
            # Build device dict
            device = {
                'management_ip': connection.target_host,
                'management_port': connection.target_port or 22,
                'connection_protocol': 'ssh',  # Default
                'vendor': None,
                'model': None,
                'name': connection.name
            }
            
            # Extract network device metadata
            if meta:
                device['vendor'] = meta.get('vendor')
                device['model'] = meta.get('model')
            
            # Get credential
            credential_info = None
            if connection.credential_id and connection.credential:
                # Decrypt password using credential service
                from app.services.credential_service import get_credential_service
                credential_service = get_credential_service()
                try:
                    decrypted = credential_service.get_credential(db, connection.credential.id, session.tenant_id)
                    if decrypted:
                        credential_info = {
                            'username': decrypted.get('username') or connection.credential.username,
                            'password': decrypted.get('password'),  # Now properly decrypted
                        }
                    else:
                        logger.warning(f"Failed to decrypt credential {connection.credential.id} for rollback")
                except Exception as e:
                    logger.error(f"Error decrypting credential {connection.credential.id} for rollback: {e}", exc_info=True)
            
            # Restore config
            result = await self.network_executor.rollback_config(
                device=device,
                backup_config=backup.get('config'),
                credential=credential_info
            )
            
            if result.get('success'):
                logger.info(f"Successfully rolled back config for connection {connection_id}")
                return True
            else:
                logger.error(f"Failed to rollback config: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error rolling back network device config: {e}", exc_info=True)
            return False
    
    async def rollback_execution(
        self,
        db: Session,
        session: ExecutionSession
    ):
        """
        Rollback all executed steps in reverse order
        
        Executes rollback commands for all completed steps, starting from the last one.
        For network devices, also restores configuration backups.
        """
        try:
            # Get all completed steps, ordered by step_number descending
            completed_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.completed == True,
                ExecutionStep.success == True  # Only rollback successful steps
            ).order_by(ExecutionStep.step_number.desc()).all()
            
            if not completed_steps:
                logger.info(f"No completed steps to rollback for session {session.id}")
                return
            
            logger.info(f"Starting rollback for session {session.id}: {len(completed_steps)} steps to rollback")
            
            # Get connection config (use same config as execution)
            connection_config = await self.connection_service.get_connection_config(db, session, completed_steps[0])
            connector_type = connection_config.get("connector_type", "local")
            connector = get_connector(connector_type)
            
            # Check if this is a network device - if so, restore config backup first
            if connector_type == "network_device":
                connection_id = connection_config.get("connection_id")
                if connection_id:
                    logger.info(f"Rolling back network device config for connection {connection_id}")
                    await self.rollback_network_device_config(db, session, connection_id)
            
            rollback_failed = False
            
            # Execute rollback commands in reverse order
            for step in completed_steps:
                if not step.rollback_command:
                    logger.warning(f"Step {step.step_number} has no rollback command, skipping")
                    continue
                
                try:
                    logger.info(f"Rolling back step {step.step_number}: {step.rollback_command[:50]}...")
                    
                    # Execute rollback command
                    result = await connector.execute_command(
                        command=step.rollback_command,
                        connection_config=connection_config,
                        timeout=30
                    )
                    
                    if not result["success"]:
                        logger.error(
                            f"Rollback failed for step {step.step_number}: {result.get('error', 'Unknown error')}"
                        )
                        rollback_failed = True
                        # Continue with other rollbacks even if one fails
                    else:
                        logger.info(f"Successfully rolled back step {step.step_number}")
                        
                except Exception as e:
                    logger.error(f"Exception during rollback of step {step.step_number}: {e}")
                    rollback_failed = True
                    # Continue with other rollbacks
            
            if rollback_failed:
                logger.warning(f"Some rollback commands failed for session {session.id}")
            else:
                logger.info(f"Successfully rolled back all steps for session {session.id}")
                
        except Exception as e:
            logger.error(f"Error during rollback execution: {e}")
            # Don't raise - rollback failure shouldn't prevent error reporting




