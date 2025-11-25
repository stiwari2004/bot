"""
Connection configuration service - CLEAN REWRITE
Simple service for getting connection config for execution steps
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.credential import Credential
from app.services.ci_extraction_service import CIExtractionService
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class ConnectionService:
    """Manages connection configuration for execution steps"""
    
    async def get_connection_config(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ) -> Dict[str, Any]:
        """Get connection configuration for executing a step"""
        # Priority:
        # 1. Extract CI/server from ticket and match to infrastructure connection
        # 2. Use connection config from ticket metadata
        # 3. Use connection config from runbook metadata
        # 4. Default to local execution
        
        # Try to extract CI and match to infrastructure connection
        if session.ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                # Extract CI/server name from ticket
                ticket_dict = {
                    'id': ticket.id,
                    'meta_data': ticket.meta_data,
                    'description': ticket.description,
                    'service': ticket.service,
                    'title': ticket.title
                }
                ci_name = CIExtractionService.extract_ci_from_ticket(ticket_dict)
                
                if ci_name:
                    # Try to find matching infrastructure connection
                    connection = CIExtractionService.find_infrastructure_connection(
                        db, ci_name, session.tenant_id
                    )
                    
                    if connection:
                        # Get credential
                        credential = None
                        if connection.credential_id:
                            credential = db.query(Credential).filter(
                                Credential.id == connection.credential_id
                            ).first()
                        
                        # Build connection config
                        config = {
                            "connector_type": connection.connection_type,
                            "host": connection.target_host,
                            "port": connection.target_port,
                            "ci_name": ci_name,
                            "connection_id": connection.id,
                            "credential_id": credential.id if credential else None,
                        }
                        
                        # Add credential info if available
                        if credential:
                            from app.services.credential_service import get_credential_service
                            credential_service = get_credential_service()
                            decrypted = credential_service.get_credential(db, credential.id, session.tenant_id)
                            if decrypted:
                                config.update({
                                    "username": decrypted.get("username"),
                                    "password": decrypted.get("password"),
                                    "api_key": decrypted.get("api_key"),
                                    "database_name": decrypted.get("database_name")
                                })
                        
                        logger.info(f"Using infrastructure connection for CI: {ci_name}")
                        return config
                    
                    # Try cloud discovery (Azure, GCP, AWS)
                    from app.services.cloud_discovery import CloudDiscoveryService
                    vm_info = await CloudDiscoveryService.discover_azure_vm(
                        db=db,
                        vm_name=ci_name,
                        tenant_id=session.tenant_id
                    )
                    
                    if vm_info:
                        azure_creds = vm_info.get('azure_credentials') or {}
                        config = {
                            "connector_type": "azure_bastion",
                            "resource_id": vm_info['resource_id'],
                            "subscription_id": vm_info['subscription_id'],
                            "ci_name": ci_name,
                            "connection_id": vm_info.get('connection_id'),
                            "credential_id": vm_info.get('credential_id'),
                            "azure_credentials": azure_creds,
                            "tenant_id": azure_creds.get('tenant_id'),
                            "client_id": azure_creds.get('client_id'),
                            "client_secret": azure_creds.get('client_secret'),
                            "os_type": vm_info.get('os_type'),
                        }
                        logger.info(f"Discovered Azure VM: {ci_name}")
                        return config
                
                # Fallback: Check ticket meta_data for connection_config
                ticket_meta = ticket.meta_data or {}
                if isinstance(ticket_meta, str):
                    try:
                        ticket_meta = json.loads(ticket_meta)
                    except:
                        ticket_meta = {}
                
                if ticket_meta.get("connection_config"):
                    config = ticket_meta["connection_config"]
                    if isinstance(config, dict) and "credential_id" not in config:
                        config["credential_id"] = ticket_meta.get("credential_id")
                    return config
        
        # Try runbook metadata
        runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        if runbook and runbook.metadata:
            runbook_meta = runbook.metadata
            if isinstance(runbook_meta, dict) and runbook_meta.get("connection_config"):
                config = runbook_meta["connection_config"]
                if isinstance(config, dict) and "credential_id" not in config:
                    config["credential_id"] = runbook_meta.get("credential_id")
                return config
        
        # Default to local execution
        logger.info("Using default local connector")
        return {
            "connector_type": "local",
            "credential_id": None,
        }
