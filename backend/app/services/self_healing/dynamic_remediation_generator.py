"""
Dynamic Remediation Generator
Generates remediation step definitions from post-execution analysis
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.runbook import Runbook
from app.models.ticket import Ticket
import json

logger = get_logger(__name__)


class DynamicRemediationGenerator:
    """Service for generating remediation steps from analysis"""
    
    async def generate_remediation_steps(
        self,
        db: Session,
        analysis_result: Dict[str, Any],
        ticket: Ticket,
        original_runbook_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate remediation step definitions from analysis
        
        Args:
            db: Database session
            analysis_result: Result from post-execution analysis
            ticket: Associated ticket
            original_runbook_id: Original runbook ID that failed
            
        Returns:
            {
                "steps": List[Dict] - Step definitions,
                "runbook_name": str,
                "runbook_description": str,
                "validation_errors": List[str]
            }
        """
        try:
            recommended_actions = analysis_result.get('recommended_actions', [])
            root_cause = analysis_result.get('root_cause', 'Unknown')
            analysis = analysis_result.get('analysis', '')
            
            if not recommended_actions:
                return {
                    "steps": [],
                    "runbook_name": f"Remediation for Ticket {ticket.id}",
                    "runbook_description": "No remediation steps available",
                    "validation_errors": ["No recommended actions from analysis"]
                }
            
            # Generate step definitions from recommended actions
            steps = []
            for idx, action in enumerate(recommended_actions, start=1):
                step = self._action_to_step_definition(action, idx, ticket)
                if step:
                    steps.append(step)
            
            # Validate steps
            validation_errors = self._validate_steps(steps)
            
            # Generate runbook metadata
            runbook_name = f"Remediation: {ticket.title[:50]}"
            runbook_description = (
                f"Auto-generated remediation runbook for ticket {ticket.id}.\n"
                f"Root Cause: {root_cause}\n"
                f"Analysis: {analysis[:200]}"
            )
            
            logger.info(
                f"Generated {len(steps)} remediation steps for ticket {ticket.id}"
            )
            
            return {
                "steps": steps,
                "runbook_name": runbook_name,
                "runbook_description": runbook_description,
                "validation_errors": validation_errors
            }
            
        except Exception as e:
            logger.error(f"Error generating remediation steps: {e}", exc_info=True)
            return {
                "steps": [],
                "runbook_name": f"Remediation for Ticket {ticket.id}",
                "runbook_description": f"Error generating steps: {str(e)}",
                "validation_errors": [str(e)]
            }
    
    def _action_to_step_definition(
        self,
        action: str,
        step_number: int,
        ticket: Ticket
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a recommended action to a step definition
        
        Args:
            action: Recommended action text
            step_number: Step number
            ticket: Associated ticket
            
        Returns:
            Step definition dictionary or None if invalid
        """
        try:
            # Parse action to extract command
            # Actions might be in various formats:
            # - "Restart service X"
            # - "Run command: systemctl restart X"
            # - "Check Y and if Z, then do W"
            
            # Simple heuristic: look for command patterns
            action_lower = action.lower()
            
            # Extract command if present
            command = None
            if "command:" in action_lower or "run:" in action_lower:
                # Extract command after colon
                parts = action.split(":", 1)
                if len(parts) > 1:
                    command = parts[1].strip()
            elif "systemctl" in action_lower:
                # Extract systemctl command
                import re
                match = re.search(r'systemctl\s+\w+\s+\w+', action)
                if match:
                    command = match.group(0)
            elif "restart" in action_lower or "start" in action_lower or "stop" in action_lower:
                # Try to construct command from action
                if "service" in action_lower:
                    # Extract service name
                    import re
                    service_match = re.search(r'service\s+(\w+)', action_lower)
                    if service_match:
                        service_name = service_match.group(1)
                        if "restart" in action_lower:
                            command = f"systemctl restart {service_name}"
                        elif "start" in action_lower:
                            command = f"systemctl start {service_name}"
                        elif "stop" in action_lower:
                            command = f"systemctl stop {service_name}"
            
            # If no command extracted, use action as description and create a generic step
            if not command:
                # Try to infer command from common patterns
                if "check" in action_lower or "verify" in action_lower:
                    # This is likely a verification step
                    command = None  # Will be handled as verification step
                else:
                    # Use action as-is (might need manual review)
                    command = action
            
            # Determine step type
            step_type = "command"
            if "check" in action_lower or "verify" in action_lower or "validate" in action_lower:
                step_type = "verification"
            elif "restart" in action_lower or "start" in action_lower or "stop" in action_lower:
                step_type = "remediation"
            
            # Build step definition
            step = {
                "step_number": step_number,
                "step_name": f"Remediation Step {step_number}",
                "step_type": step_type,
                "command": command,
                "description": action,
                "expected_output": None,
                "timeout_seconds": 300,  # 5 minutes default
                "retry_count": 1,
                "on_success": "continue",
                "on_failure": "continue" if step_number < 5 else "stop"  # Stop after 5 steps
            }
            
            return step
            
        except Exception as e:
            logger.warning(f"Error converting action to step: {action} - {e}")
            return None
    
    def _validate_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """
        Validate step definitions
        
        Args:
            steps: List of step definitions
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not steps:
            errors.append("No steps defined")
            return errors
        
        if len(steps) > 10:
            errors.append(f"Too many steps: {len(steps)} (maximum 10)")
        
        for idx, step in enumerate(steps, start=1):
            if not step.get('step_name'):
                errors.append(f"Step {idx}: Missing step_name")
            
            if step.get('step_type') == 'command' and not step.get('command'):
                errors.append(f"Step {idx}: Command step missing command")
            
            if step.get('timeout_seconds', 0) <= 0:
                errors.append(f"Step {idx}: Invalid timeout_seconds")
        
        return errors


# Global instance
_dynamic_remediation_generator: Optional[DynamicRemediationGenerator] = None


def get_dynamic_remediation_generator() -> DynamicRemediationGenerator:
    """Get or create dynamic remediation generator instance"""
    global _dynamic_remediation_generator
    if _dynamic_remediation_generator is None:
        _dynamic_remediation_generator = DynamicRemediationGenerator()
    return _dynamic_remediation_generator

