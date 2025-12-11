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
                        # Verify connection is active
                        if not connection.is_active:
                            raise ValueError(
                                f"Infrastructure connection for '{ci_name}' is inactive. "
                                "Please activate the connection in Settings → Infrastructure Connections."
                            )
                        
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
                    
                    # Node not found in InfrastructureConnection - require it to be added first
                    raise ValueError(
                        f"Node '{ci_name}' is not configured in Infrastructure Connections. "
                        "Please add this node to your infrastructure connections first before executing runbooks. "
                        "You can discover and add nodes from Settings → Infrastructure Connections → Discover Resources."
                    )
                
                # Fallback: Check ticket meta_data for connection_config
                ticket_meta = ticket.meta_data or {}
                if isinstance(ticket_meta, str):
                    try:
                        ticket_meta = json.loads(ticket_meta)
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse ticket meta_data as JSON: {e}")
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
