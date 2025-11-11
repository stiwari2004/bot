"""
CI/Server extraction service
Extracts CI/server names from tickets for infrastructure connection matching
"""
import re
from typing import Optional, Dict, Any, List
from app.core.logging import get_logger

logger = get_logger(__name__)


class CIExtractionService:
    """Extract CI/server names from ticket metadata and description"""
    
    # Common patterns for CI/server names
    SERVER_PATTERNS = [
        r'\b([a-z0-9-]+\.(?:example\.com|local|internal|corp))\b',  # FQDN
        r'\b(server[_-]?[0-9]+)\b',  # server-01, server_01
        r'\b(host[_-]?[0-9]+)\b',  # host-01, host_01
        r'\b([a-z]+[0-9]+)\b',  # db01, web01
        r'\b([A-Z]+-[0-9]+)\b',  # PROD-DB-01
        r'\b(ci[_-]?[0-9]+)\b',  # ci-123, ci_123
        r'\b([a-z]+-[a-z]+-[0-9]+)\b',  # prod-db-01
    ]
    
    # Common CI identifiers
    CI_KEYWORDS = [
        'ci_id', 'ci_name', 'ci_name', 'configuration_item',
        'server_name', 'hostname', 'host_name', 'server',
        'instance', 'node', 'machine', 'host'
    ]
    
    @staticmethod
    def extract_ci_from_ticket(ticket: Dict[str, Any]) -> Optional[str]:
        """
        Extract CI/server name from ticket
        
        Priority:
        1. ticket.meta_data.ci_association
        2. ticket.meta_data (search for CI keywords)
        3. ticket.description (pattern matching)
        4. ticket.service field
        """
        try:
            # 1. Check meta_data.ci_association
            meta_data = ticket.get('meta_data') or {}
            if isinstance(meta_data, str):
                try:
                    import json
                    meta_data = json.loads(meta_data)
                except:
                    meta_data = {}
            
            ci_association = meta_data.get('ci_association') or meta_data.get('ci_id') or meta_data.get('ci_name')
            if ci_association:
                logger.info(f"Found CI from ci_association: {ci_association}")
                return str(ci_association).strip()
            
            # 2. Search meta_data for CI keywords
            for key in CIExtractionService.CI_KEYWORDS:
                if key in meta_data:
                    value = meta_data[key]
                    if value and isinstance(value, str) and len(value.strip()) > 0:
                        logger.info(f"Found CI from meta_data.{key}: {value}")
                        return value.strip()
            
            # 3. Extract from description using patterns
            description = ticket.get('description') or ticket.get('title') or ''
            if description:
                extracted = CIExtractionService._extract_from_text(description)
                if extracted:
                    logger.info(f"Found CI from description: {extracted}")
                    return extracted
            
            # 4. Use service field if it looks like a server name
            service = ticket.get('service')
            if service and CIExtractionService._looks_like_server_name(service):
                logger.info(f"Using service field as CI: {service}")
                return service.strip()
            
            logger.debug(f"No CI found for ticket {ticket.get('id')}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting CI from ticket: {e}")
            return None
    
    @staticmethod
    def _extract_from_text(text: str) -> Optional[str]:
        """Extract server/CI name from text using patterns"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Try each pattern
        for pattern in CIExtractionService.SERVER_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Return the first match that looks like a server name
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else None
                    if match and CIExtractionService._looks_like_server_name(match):
                        return match
        
        return None
    
    @staticmethod
    def _looks_like_server_name(name: str) -> bool:
        """Check if a string looks like a server/CI name"""
        if not name or len(name.strip()) < 3:
            return False
        
        # Exclude common words that aren't server names
        excluded = ['server', 'database', 'service', 'application', 'system', 'error', 'failed']
        if name.lower() in excluded:
            return False
        
        # Should contain alphanumeric characters
        if not re.search(r'[a-z0-9]', name.lower()):
            return False
        
        return True
    
    @staticmethod
    def find_infrastructure_connection(
        db,
        ci_name: str,
        tenant_id: int,
        connection_type: Optional[str] = None
    ) -> Optional[Any]:
        """
        Find infrastructure connection matching CI/server name
        
        Returns InfrastructureConnection or None
        """
        try:
            from app.models.credential import InfrastructureConnection
            
            # Search by name (exact match first)
            query = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.tenant_id == tenant_id
            )
            
            if connection_type:
                query = query.filter(InfrastructureConnection.connection_type == connection_type)
            
            # Try exact match
            connection = query.filter(
                InfrastructureConnection.name.ilike(f"%{ci_name}%")
            ).first()
            
            if connection:
                logger.info(f"Found infrastructure connection by name match: {connection.name}")
                return connection
            
            # Try matching target_host
            connection = query.filter(
                InfrastructureConnection.target_host.ilike(f"%{ci_name}%")
            ).first()
            
            if connection:
                logger.info(f"Found infrastructure connection by host match: {connection.target_host}")
                return connection
            
            logger.debug(f"No infrastructure connection found for CI: {ci_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding infrastructure connection: {e}")
            return None



