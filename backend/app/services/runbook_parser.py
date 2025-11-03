"""
Runbook parser to extract structured steps from markdown/YAML format
"""
import yaml
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RunbookParser:
    """Parse runbook body_md into structured format for execution"""
    
    def parse_runbook(self, body_md: str) -> Dict[str, Any]:
        """
        Parse runbook body into structured format
        
        Args:
            body_md: Markdown body containing YAML code fence
            
        Returns:
            {
                "prechecks": [{"command": "...", "description": "..."}],
                "main_steps": [{"command": "...", "description": "...", "severity": "..."}],
                "postchecks": [{"command": "...", "description": "..."}],
                "metadata": {...}
            }
        """
        try:
            # Try to extract YAML from code fence
            yaml_match = re.search(r'```yaml\n(.*?)```', body_md, re.DOTALL)
            if yaml_match:
                yaml_content = yaml_match.group(1).strip()
                spec = yaml.safe_load(yaml_content)
                
                if spec and isinstance(spec, dict):
                    return self._parse_yaml_spec(spec)
            
            # Fallback: Try to parse as raw markdown without YAML
            logger.warning("No YAML code fence found, attempting markdown parsing")
            return self._parse_markdown_fallback(body_md)
            
        except Exception as e:
            logger.error(f"Error parsing runbook: {e}")
            return self._parse_markdown_fallback(body_md)
    
    def _parse_yaml_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Parse validated YAML spec structure"""
        prechecks = []
        main_steps = []
        postchecks = []
        
        # Parse prechecks
        if "prechecks" in spec and isinstance(spec["prechecks"], list):
            for item in spec["prechecks"]:
                prechecks.append({
                    "command": item.get("command", ""),
                    "description": item.get("description", ""),
                    "expected_output": item.get("expected_output", "")
                })
        
        # Parse main steps
        if "steps" in spec and isinstance(spec["steps"], list):
            for step in spec["steps"]:
                main_steps.append({
                    "command": step.get("command", ""),
                    "description": step.get("description", ""),
                    "name": step.get("name", ""),
                    "type": step.get("type", "command"),
                    "severity": step.get("severity", "safe"),
                    "expected_output": step.get("expected_output", ""),
                    "timeout": step.get("timeout")
                })
        
        # Parse postchecks
        if "postchecks" in spec and isinstance(spec["postchecks"], list):
            for item in spec["postchecks"]:
                postchecks.append({
                    "command": item.get("command", ""),
                    "description": item.get("description", ""),
                    "expected_output": item.get("expected_output", "")
                })
        
        metadata = {
            "title": spec.get("title", ""),
            "service": spec.get("service", ""),
            "env": spec.get("env", ""),
            "risk": spec.get("risk", ""),
            "version": spec.get("version", "")
        }
        
        return {
            "prechecks": prechecks,
            "main_steps": main_steps,
            "postchecks": postchecks,
            "metadata": metadata
        }
    
    def _parse_markdown_fallback(self, body_md: str) -> Dict[str, Any]:
        """
        Fallback parser for old markdown-only format
        Extracts commands from code blocks and bullet points
        """
        prechecks = []
        main_steps = []
        postchecks = []
        
        # Try to find bash code blocks
        bash_matches = re.findall(r'```bash\n(.*?)```', body_md, re.DOTALL)
        for match in bash_matches:
            commands = [line.strip() for line in match.strip().split('\n') if line.strip()]
            for cmd in commands:
                if cmd:
                    # Default to main steps for old format
                    main_steps.append({
                        "command": cmd,
                        "description": f"Execute: {cmd}",
                        "name": "Command",
                        "type": "command",
                        "severity": "moderate",
                        "expected_output": ""
                    })
        
        # Try to parse step sections
        # Look for "### Step X:" or "## Troubleshooting Steps"
        step_pattern = r'###\s*Step\s+\d+:(.*?)(?=###|$)'
        steps_text = re.findall(step_pattern, body_md, re.DOTALL)
        
        if not main_steps and steps_text:
            # If we have step sections, try to extract from them
            for idx, step_text in enumerate(steps_text, 1):
                # Look for commands in this step
                cmd_match = re.search(r'```bash\n(.*?)```', step_text, re.DOTALL)
                if cmd_match:
                    commands = [line.strip() for line in cmd_match.group(1).strip().split('\n') if line.strip()]
                    for cmd in commands:
                        if cmd:
                            main_steps.append({
                                "command": cmd,
                                "description": f"Step {idx}: {self._extract_description(step_text)}",
                                "name": f"Step {idx}",
                                "type": "command",
                                "severity": "moderate",
                                "expected_output": ""
                            })
        
        # Default fallback: create at least one step if nothing found
        if not main_steps:
            logger.warning("Could not parse any steps from runbook, creating placeholder")
            main_steps.append({
                "command": "echo 'No commands found in runbook'",
                "description": "Placeholder: Unable to parse runbook structure",
                "name": "Unknown",
                "type": "manual",
                "severity": "safe",
                "expected_output": ""
            })
        
        return {
            "prechecks": prechecks,
            "main_steps": main_steps,
            "postchecks": postchecks,
            "metadata": {
                "title": "Unknown",
                "service": "unknown",
                "env": "",
                "risk": ""
            }
        }
    
    def _extract_description(self, text: str) -> str:
        """Extract a brief description from step text"""
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Get first sentence
        sentences = text.strip().split('.')
        if sentences:
            return sentences[0].strip()
        return ""


# Singleton instance
_parser_instance = None

def get_parser() -> RunbookParser:
    """Get singleton runbook parser instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = RunbookParser()
    return _parser_instance

