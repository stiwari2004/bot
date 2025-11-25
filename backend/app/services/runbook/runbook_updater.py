"""
Runbook updater service for updating runbook YAML when commands are corrected.
"""
import yaml
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.runbook import Runbook
from app.core.logging import get_logger
from app.services.runbook_parser import RunbookParser

logger = get_logger(__name__)


class RunbookUpdater:
    """Updates runbook YAML in database when commands are corrected"""
    
    def __init__(self):
        self.parser = RunbookParser()
    
    async def update_runbook_step(
        self,
        runbook_id: int,
        step_number: int,
        corrected_command: str,
        db: Session
    ) -> bool:
        """
        Update a specific step's command in the runbook YAML.
        
        Args:
            runbook_id: ID of the runbook to update
            step_number: Step number (1-indexed, includes prechecks, main steps, postchecks)
            corrected_command: Corrected command to use
            db: Database session
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Fetch runbook from database
            runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if not runbook:
                logger.error(f"Runbook {runbook_id} not found")
                return False
            
            if not runbook.body_md:
                logger.error(f"Runbook {runbook_id} has no body_md")
                return False
            
            # Extract original YAML to preserve runbook_id and other fields
            import re as regex_module
            yaml_match = regex_module.search(r'```yaml\n(.*?)```', runbook.body_md, regex_module.DOTALL)
            original_yaml_content = None
            original_spec = None
            if yaml_match:
                original_yaml_content = yaml_match.group(1).strip()
                try:
                    original_spec = yaml.safe_load(original_yaml_content)
                except Exception as e:
                    logger.warning(f"Could not parse original YAML: {e}")
            
            # Parse current runbook structure
            parsed = self.parser.parse_runbook(runbook.body_md)
            
            # Determine which step list and index based on step_number
            # step_number is 1-indexed and includes: prechecks, then main_steps, then postchecks
            precheck_count = len(parsed.get("prechecks", []))
            main_step_count = len(parsed.get("main_steps", []))
            
            step_list = None
            step_index = None
            
            if step_number <= precheck_count:
                # Step is in prechecks
                step_list = parsed.get("prechecks", [])
                step_index = step_number - 1
            elif step_number <= precheck_count + main_step_count:
                # Step is in main_steps
                step_list = parsed.get("main_steps", [])
                step_index = step_number - precheck_count - 1
            else:
                # Step is in postchecks
                step_list = parsed.get("postchecks", [])
                step_index = step_number - precheck_count - main_step_count - 1
            
            if not step_list or step_index < 0 or step_index >= len(step_list):
                logger.error(
                    f"Step {step_number} not found in runbook {runbook_id}. "
                    f"Prechecks: {precheck_count}, Main: {main_step_count}, "
                    f"Postchecks: {len(parsed.get('postchecks', []))}"
                )
                return False
            
            # Update the command
            old_command = step_list[step_index].get("command", "")
            step_list[step_index]["command"] = corrected_command
            
            logger.info(
                f"Updating runbook {runbook_id} step {step_number}: "
                f"{old_command[:100]} → {corrected_command[:100]}"
            )
            
            # Reconstruct YAML from parsed structure, preserving original spec if available
            updated_yaml = self._reconstruct_yaml(parsed, original_spec)
            
            # Update body_md with new YAML wrapped in code fence
            updated_body_md = f"```yaml\n{updated_yaml}\n```"
            
            # Update runbook in database
            runbook.body_md = updated_body_md
            # updated_at will be set automatically by SQLAlchemy
            
            db.commit()
            logger.info(f"Successfully updated runbook {runbook_id} step {step_number}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating runbook {runbook_id} step {step_number}: {e}", exc_info=True)
            db.rollback()
            return False
    
    def _reconstruct_yaml(self, parsed: Dict[str, Any], original_spec: Optional[Dict[str, Any]] = None) -> str:
        """
        Reconstruct YAML from parsed runbook structure, preserving original fields.
        
        Args:
            parsed: Parsed runbook structure from RunbookParser
            original_spec: Original YAML spec to preserve fields like runbook_id
            
        Returns:
            YAML string
        """
        metadata = parsed.get("metadata", {})
        
        # Build YAML structure, preserving original runbook_id if available
        yaml_dict = {
            "runbook_id": original_spec.get("runbook_id", metadata.get("title", "rb-unknown")) if original_spec else metadata.get("title", "rb-unknown"),
            "version": original_spec.get("version", metadata.get("version", "1.0")) if original_spec else metadata.get("version", "1.0"),
            "title": metadata.get("title", "Unknown"),
            "service": metadata.get("service", "unknown"),
            "env": metadata.get("env", "prod"),
            "risk": metadata.get("risk", "low"),
        }
        
        # Preserve other original fields if available
        if original_spec:
            for key in ["description", "owner", "last_tested", "review_required", "inputs"]:
                if key in original_spec:
                    yaml_dict[key] = original_spec[key]
        
        # Add description if available
        if metadata.get("description"):
            yaml_dict["description"] = metadata["description"]
        
        # Add prechecks
        prechecks = parsed.get("prechecks", [])
        if prechecks:
            yaml_dict["prechecks"] = [
                {
                    "command": item.get("command", ""),
                    "description": item.get("description", ""),
                    "expected_output": item.get("expected_output", ""),
                }
                for item in prechecks
            ]
        
        # Add main steps
        main_steps = parsed.get("main_steps", [])
        if main_steps:
            yaml_dict["steps"] = [
                {
                    "name": step.get("name", f"Step {i+1}"),
                    "command": step.get("command", ""),
                    "description": step.get("description", ""),
                    "type": step.get("type", "command"),
                    "severity": step.get("severity", "safe"),
                    "expected_output": step.get("expected_output", ""),
                }
                for i, step in enumerate(main_steps)
            ]
            
            # Add rollback_command if present
            for i, step in enumerate(main_steps):
                if step.get("rollback_command"):
                    yaml_dict["steps"][i]["rollback_command"] = step["rollback_command"]
        
        # Add postchecks
        postchecks = parsed.get("postchecks", [])
        if postchecks:
            yaml_dict["postchecks"] = [
                {
                    "command": item.get("command", ""),
                    "description": item.get("description", ""),
                    "expected_output": item.get("expected_output", ""),
                }
                for item in postchecks
            ]
        
        # Convert to YAML string
        try:
            yaml_str = yaml.dump(yaml_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return yaml_str
        except Exception as e:
            logger.error(f"Error converting to YAML: {e}", exc_info=True)
            raise

