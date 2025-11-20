"""
Runbook normalization service to inject ticket-specific details into generic runbooks
"""
import re
import yaml
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.services.ci_extraction_service import CIExtractionService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookNormalizer:
    """Normalize generic runbooks with ticket-specific details"""
    
    @staticmethod
    def normalize_runbook_for_ticket(
        runbook: Runbook,
        ticket: Ticket,
        db: Session
    ) -> Dict[str, Any]:
        """
        Normalize a generic runbook with ticket-specific details.
        
        Extracts:
        - Server/CI name from ticket
        - Service name from ticket
        - Environment from ticket
        
        Replaces placeholders in runbook commands with actual values.
        
        Returns normalized runbook structure with substituted commands.
        """
        try:
            # Extract CI/server name from ticket
            ticket_dict = {
                'id': ticket.id,
                'meta_data': ticket.meta_data,
                'description': ticket.description,
                'service': ticket.service,
                'title': ticket.title
            }
            ci_name = CIExtractionService.extract_ci_from_ticket(ticket_dict)
            
            # Extract other details
            service_name = ticket.service or "server"
            environment = ticket.environment or "prod"
            
            # Parse runbook YAML
            from app.services.runbook_parser import RunbookParser
            parser = RunbookParser()
            parsed = parser.parse_runbook(runbook.body_md)
            
            # Normalize commands in all steps
            substitutions = {
                'server_name': ci_name or service_name,
                'ci_name': ci_name or service_name,
                'hostname': ci_name or service_name,
                'service': service_name,
                'environment': environment,
            }
            
            # Remove None values
            substitutions = {k: v for k, v in substitutions.items() if v}
            
            # Normalize prechecks
            normalized_prechecks = []
            for step in parsed.get('prechecks', []):
                normalized_step = RunbookNormalizer._normalize_step(step, substitutions)
                normalized_prechecks.append(normalized_step)
            
            # Normalize main steps
            normalized_main_steps = []
            for step in parsed.get('main_steps', []):
                normalized_step = RunbookNormalizer._normalize_step(step, substitutions)
                normalized_main_steps.append(normalized_step)
            
            # Normalize postchecks
            normalized_postchecks = []
            for step in parsed.get('postchecks', []):
                normalized_step = RunbookNormalizer._normalize_step(step, substitutions)
                normalized_postchecks.append(normalized_step)
            
            return {
                'prechecks': normalized_prechecks,
                'main_steps': normalized_main_steps,
                'postchecks': normalized_postchecks,
                'metadata': {
                    **parsed.get('metadata', {}),
                    'normalized_for_ticket': ticket.id,
                    'server_name': ci_name,
                    'service': service_name,
                    'environment': environment,
                }
            }
            
        except Exception as e:
            logger.error(f"Error normalizing runbook {runbook.id} for ticket {ticket.id}: {e}")
            # Return original parsed structure if normalization fails
            from app.services.runbook_parser import RunbookParser
            parser = RunbookParser()
            return parser.parse_runbook(runbook.body_md)
    
    @staticmethod
    def _normalize_step(step: Dict[str, Any], substitutions: Dict[str, str]) -> Dict[str, Any]:
        """Normalize a single step by replacing placeholders in commands"""
        normalized_step = step.copy()
        
        if 'command' in step and step['command']:
            command = step['command']
            
            # Replace common placeholders
            # Pattern 1: {{variable}} syntax
            for key, value in substitutions.items():
                # Replace {{variable}} and {variable} patterns
                command = re.sub(
                    rf'\{{{{\s*{re.escape(key)}\s*\}}\}}',
                    value,
                    command,
                    flags=re.IGNORECASE
                )
                command = re.sub(
                    rf'\{{\s*{re.escape(key)}\s*\}}',
                    value,
                    command,
                    flags=re.IGNORECASE
                )
            
            # Pattern 2: Generic server/hostname patterns
            # Replace generic patterns like "the server", "target server", etc. with actual server name
            if substitutions.get('server_name'):
                server_name = substitutions['server_name']
                # Replace generic server references
                generic_patterns = [
                    (r'\btarget server\b', server_name, re.IGNORECASE),
                    (r'\bthe server\b', server_name, re.IGNORECASE),
                    (r'\bserver\b', server_name, re.IGNORECASE),
                    (r'\bhostname\b', server_name, re.IGNORECASE),
                ]
                
                # Only replace if it's clearly a placeholder (not part of a command)
                for pattern, replacement, flags in generic_patterns:
                    # Check if it's in a context where it should be replaced
                    # (e.g., not in a command like "server-status" or "server.log")
                    if re.search(rf'\b{pattern}\b', command, flags=flags):
                        # Replace standalone occurrences
                        command = re.sub(
                            rf'(?<![a-zA-Z0-9_-]){pattern}(?![a-zA-Z0-9_-])',
                            replacement,
                            command,
                            flags=flags
                        )
            
            normalized_step['command'] = command
            
            # Also normalize description if it contains placeholders
            if 'description' in step and step['description']:
                description = step['description']
                for key, value in substitutions.items():
                    description = re.sub(
                        rf'\{{{{\s*{re.escape(key)}\s*\}}\}}',
                        value,
                        description,
                        flags=re.IGNORECASE
                    )
                normalized_step['description'] = description
        
        return normalized_step

