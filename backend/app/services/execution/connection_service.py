"""
Connection configuration service - CLEAN REWRITE
Execution only runs on nodes that are in the connected nodes list (infrastructure_connections).
Billing is node-based: we never execute against a node that is not in the list.
"""
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.credential import Credential
from app.services.ci_extraction_service import CIExtractionService
from app.core.logging import get_logger
import json

logger = get_logger(__name__)

DEFAULT_SSH_PORT = 22


def _text_candidates(text: str) -> List[str]:
    """Extract server name / IP candidates from ticket or issue text."""
    if not text or not text.strip():
        return []
    candidates: List[str] = []
    for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        candidates.append(m.group(0))
    for prefix in ("host", "server", "node", "ci", "machine", "target"):
        for m in re.finditer(rf"\b{prefix}\s*[:\-=]\s*([a-zA-Z0-9_.-]+)\b", text, re.IGNORECASE):
            candidates.append(m.group(1).strip())
    for m in re.finditer(r"\b([a-z0-9][a-z0-9_.-]{2,})\b", text, re.IGNORECASE):
        candidates.append(m.group(1))
    return candidates


def resolve_target_connection_for_assignment(
    db: Session,
    tenant_id: int,
    ticket_id: Optional[int],
    request_metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Get the affected node (name or IP) from the ticket, then validate it is in the nodes list.
    - If the node is in the list → return connection (allow execution).
    - If the node is not in the list → raise (ask to add the node; billing is node-based).
    No guessing: we only execute when the ticket's affected node is explicitly in the list.
    """
    request_metadata = request_metadata or {}
    server_name: Optional[str] = None
    host_ip: Optional[str] = None
    search_text_parts: List[str] = []

    # 1) Request metadata (server_name / host_ip / issue_description)
    conn_in = request_metadata.get("connection") or {}
    if conn_in.get("host"):
        server_name = conn_in.get("host")
    server_name = server_name or request_metadata.get("server_name")
    host_ip = host_ip or request_metadata.get("host_ip")
    if request_metadata.get("issue_description"):
        search_text_parts.append(request_metadata["issue_description"])

    # 2) From ticket: extracted_inputs (from runbook input extraction) and title/description
    ticket: Optional[Ticket] = None
    if ticket_id:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            search_text_parts.extend([ticket.title or "", ticket.description or ""])
            if getattr(ticket, "meta_data", None) and isinstance(ticket.meta_data, dict):
                extracted = ticket.meta_data.get("extracted_inputs") or {}
                if not server_name:
                    server_name = extracted.get("server_name")
                if not host_ip:
                    host_ip = extracted.get("host_ip")
                for v in (ticket.meta_data or {}).values():
                    if isinstance(v, str):
                        search_text_parts.append(v)

    # 3) From ticket description/title via CI extraction
    if ticket and not server_name and not host_ip:
        ticket_dict = {
            "id": ticket.id,
            "meta_data": ticket.meta_data,
            "description": ticket.description,
            "service": ticket.service,
            "title": ticket.title,
        }
        ci = CIExtractionService.extract_ci_from_ticket(ticket_dict)
        if ci:
            server_name = server_name or ci

    search_text = " ".join(search_text_parts).strip()

    # 4) Extract from ticket/issue text when we still have no name or IP
    if not server_name and not host_ip and search_text:
        for c in _text_candidates(search_text):
            if not c or len(c) < 2:
                continue
            if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", c):
                host_ip = c
                break
        for c in _text_candidates(search_text):
            if not c or len(c) < 2 or re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", c):
                continue
            server_name = c
            break
        if not host_ip and server_name and re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", str(server_name)):
            host_ip, server_name = server_name, None

    # 5) Validate: affected node must be in the nodes list (no execution otherwise)
    node = None
    affected = server_name or host_ip
    if not affected or not str(affected).strip():
        raise ValueError(
            "Could not determine the affected node from the ticket. "
            "The ticket (or issue description) should mention the server name or IP. "
            "Execution is only allowed for nodes that are in your connected nodes list (Settings → Nodes)."
        )
    node = CIExtractionService.find_infrastructure_connection(db, str(affected).strip(), tenant_id)
    if not node:
        raise ValueError(
            f"The affected node '{affected}' is not in your connected nodes list. "
            "Add this node in Settings → Infrastructure Connections (Nodes) to run execution. "
            "Billing is node-based; execution is only allowed for nodes in your list."
        )
    logger.info("Affected node from ticket validated in nodes list: %s -> %s (%s)", affected, node.name, node.target_host)

    if not node.is_active:
        raise ValueError(
            f"Node '{node.name}' is inactive. Activate it in Settings → Infrastructure Connections."
        )

    # Build connection block for worker (must include host so worker gets target_host)
    port = node.target_port if node.target_port is not None else (DEFAULT_SSH_PORT if (node.connection_type or "").lower() in ("ssh", "") else None)
    connection = {
        "host": node.target_host,
        "port": port,
        "type": node.connection_type or "ssh",
        "connector_type": (node.connection_type or "ssh").lower(),
        "target_host": node.target_host,
        "server_name": node.name,
        "environment": node.environment,
    }
    if node.credential_id:
        credential = db.query(Credential).filter(Credential.id == node.credential_id).first()
        if credential and credential.name:
            connection["credential_source"] = f"alias:{credential.name}"
    return connection


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
