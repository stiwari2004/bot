"""
YAML parsing with error handling and recovery
"""
import yaml
from typing import Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlParser:
    """Parses YAML with comprehensive error handling and recovery"""
    
    def parse_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """
        Parse YAML content with error handling and recovery strategies.
        
        Args:
            yaml_content: YAML string to parse
            
        Returns:
            Parsed YAML as dictionary
            
        Raises:
            ValueError: If YAML cannot be parsed or is invalid
        """
        if not yaml_content or not yaml_content.strip():
            raise ValueError("YAML content is empty")
        
        spec = None
        try:
            spec = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error: {type(e).__name__}: {e}")
            # Try recovery with document marker
            logger.debug(f"First parse attempt failed: {e}, trying with document marker")
            if not yaml_content.strip().startswith('---'):
                yaml_with_marker = '---\n' + yaml_content.lstrip()
            else:
                yaml_with_marker = yaml_content
            try:
                spec = yaml.safe_load(yaml_with_marker)
            except yaml.YAMLError as e2:
                logger.error(f"YAML parse error even with document marker: {e2}")
                self._log_parse_error_details(e2, yaml_content)
                raise ValueError(f"YAML parsing failed: {e2}") from e2
        
        # Handle None or empty results
        if spec is None:
            logger.error(f"YAML parsed to None. YAML content (first 2000 chars): {yaml_content[:2000]}")
            raise ValueError("YAML parsed to None - check YAML syntax")
        
        # Handle non-dict results
        if not isinstance(spec, dict):
            spec = self._recover_from_non_dict(spec, yaml_content)
        
        # Validate that steps exist
        if "steps" not in spec:
            spec = self._recover_missing_steps(spec, yaml_content)
        
        return spec
    
    def _recover_from_non_dict(self, spec: Any, yaml_content: str) -> Dict[str, Any]:
        """Recover from YAML that parsed to non-dict"""
        logger.error(f"YAML did not parse to dict: type={type(spec)}, value={str(spec)[:500]}")
        logger.error(f"YAML content that failed to parse (first 2000 chars): {yaml_content[:2000]}")
        
        # Strategy 1: If it's a list, try to extract the first dict element
        if isinstance(spec, list) and len(spec) > 0 and isinstance(spec[0], dict):
            logger.warning("YAML parsed to list, using first element as dict")
            return spec[0]
        
        # Strategy 2: If it's a string, try to find YAML in it
        if isinstance(spec, str):
            logger.warning("YAML parsed to string, attempting to extract YAML dict from string")
            if "runbook_id:" in spec:
                yaml_start = spec.find("runbook_id:")
                yaml_chunk = spec[yaml_start:yaml_start+5000]
                try:
                    parsed = yaml.safe_load(yaml_chunk)
                    if isinstance(parsed, dict):
                        logger.info("Successfully extracted dict from string")
                        return parsed
                except Exception as e:
                    logger.error(f"Failed to extract YAML from string: {e}")
            raise ValueError(f"YAML parsed to string instead of dict. Content: {spec[:200]}")
        
        # Strategy 3: Try loading all documents if it's a multi-document YAML
        if isinstance(spec, list) and len(spec) == 0:
            logger.warning("YAML parsed to empty list, trying to load all documents")
            try:
                all_docs = list(yaml.safe_load_all(yaml_content))
                if all_docs and len(all_docs) > 0 and isinstance(all_docs[0], dict):
                    logger.info("Successfully extracted dict from multi-document YAML")
                    return all_docs[0]
            except Exception as e:
                logger.error(f"Failed to load multi-document YAML: {e}")
        
        raise ValueError(f"invalid spec shape - not a dict (got {type(spec).__name__})")
    
    def _recover_missing_steps(self, spec: Dict[str, Any], yaml_content: str) -> Dict[str, Any]:
        """Recover from YAML missing steps section"""
        logger.error(f"[MISSING STEPS] YAML dict missing 'steps' key")
        logger.error(f"[MISSING STEPS] Keys found in spec: {list(spec.keys())}")
        logger.error(f"[MISSING STEPS] Raw YAML that failed (first 2000 chars): {repr(yaml_content[:2000])}")
        
        # Check if "steps" appears in the raw YAML but wasn't parsed
        if "steps:" in yaml_content or "steps" in yaml_content.lower():
            logger.error(f"[MISSING STEPS] 'steps' keyword found in raw YAML but not in parsed spec!")
            steps_idx = yaml_content.lower().find("steps:")
            if steps_idx >= 0:
                logger.error(f"[MISSING STEPS] Found 'steps:' at position {steps_idx} in raw YAML")
                logger.error(f"[MISSING STEPS] Context around steps: {repr(yaml_content[max(0, steps_idx-100):steps_idx+500])}")
        
        # Try to recover - check if steps might be in inputs
        steps_from_inputs = []
        if "inputs" in spec and isinstance(spec["inputs"], list):
            for inp in spec["inputs"]:
                if isinstance(inp, dict) and (inp.get("type") == "command" or "command" in inp):
                    logger.warning(f"[MISSING STEPS] Found command in inputs, converting to step: {inp.get('name', 'unknown')}")
                    step = {
                        "name": inp.get("name", "Unknown step"),
                        "type": "command",
                        "command": inp.get("command", ""),
                        "expected_output": inp.get("expected_output", "Command executed successfully"),
                        "skip_in_auto_mode": False,
                        "severity": inp.get("severity", "safe")
                    }
                    steps_from_inputs.append(step)
        
        # Try to recover - check if steps is named differently
        possible_step_keys = [k for k in spec.keys() if 'step' in k.lower() or 'action' in k.lower() or 'command' in k.lower()]
        if possible_step_keys:
            logger.warning(f"[MISSING STEPS] Found possible step keys: {possible_step_keys}, attempting to rename")
            spec['steps'] = spec[possible_step_keys[0]]
        elif steps_from_inputs:
            logger.warning(f"[MISSING STEPS] Recovered {len(steps_from_inputs)} steps from inputs section")
            spec['steps'] = steps_from_inputs
            # Clean up inputs to remove the commands
            spec['inputs'] = [inp for inp in spec.get('inputs', []) 
                             if isinstance(inp, dict) and inp.get("type") != "command" and "command" not in inp]
        else:
            # If no steps at all, this is a critical error
            logger.error("[MISSING STEPS] No steps found in YAML - LLM generated incomplete runbook")
            logger.error(f"[MISSING STEPS] Available keys: {list(spec.keys())}")
            logger.error(f"[MISSING STEPS] Full spec dump: {yaml.safe_dump(spec, default_flow_style=False)}")
            raise ValueError("invalid spec shape - missing steps. LLM generated incomplete YAML without steps section. Check backend logs for details.")
        
        return spec
    
    def _log_parse_error_details(self, error: Exception, yaml_content: str) -> None:
        """Log detailed information about YAML parse errors"""
        error_str = str(error)
        
        # Try to extract line and column numbers
        import re
        line_match = re.search(r'line (\d+)', error_str)
        col_match = re.search(r'column (\d+)', error_str)
        
        if line_match and col_match:
            line_num = int(line_match.group(1))
            col_num = int(col_match.group(1))
            lines_list = yaml_content.split('\n')
            if line_num <= len(lines_list):
                problem_line = lines_list[line_num - 1]
                logger.error(f"PROBLEMATIC LINE {line_num}: {repr(problem_line)}")
                logger.error(f"Character at column {col_num}: {repr(problem_line[col_num-1:col_num+5] if col_num <= len(problem_line) else 'N/A')}")
                if line_num == 1:
                    logger.error(f"First line full content (first 200 chars): {repr(problem_line[:200])}")
        
        logger.error(f"YAML content causing error (first 1000 chars): {repr(yaml_content[:1000])}")








