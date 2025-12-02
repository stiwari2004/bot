"""
YAML extraction and cleaning from LLM output
"""
import re
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlExtractor:
    """Extracts and cleans YAML from LLM output"""
    
    def extract_yaml(self, ai_output: str) -> str:
        """
        Extract YAML from LLM output, removing markdown, code fences, and explanatory text.
        
        Args:
            ai_output: Raw output from LLM
            
        Returns:
            Cleaned YAML string
        """
        if not ai_output:
            return ""
        
        ai_yaml = ai_output
        logger.debug(f"LLM returned YAML length={len(ai_yaml)}, first 500 chars: {ai_yaml[:500]}")
        
        # Strip code fences if present
        if ai_yaml.strip().startswith("```"):
            lines = ai_yaml.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            ai_yaml = "\n".join(lines)
            logger.debug(f"After stripping fences: length={len(ai_yaml)}, first 200: {ai_yaml[:200]}")
        
        # Extract YAML starting from "runbook_id:"
        if ai_yaml and "runbook_id:" in ai_yaml:
            runbook_id_idx = ai_yaml.find("runbook_id:")
            if runbook_id_idx > 0:
                logger.warning(f"[YAML EXTRACTION] Found 'runbook_id:' at position {runbook_id_idx}, extracting YAML from there")
                logger.warning(f"[YAML EXTRACTION] Content before runbook_id: {repr(ai_yaml[:min(runbook_id_idx, 200)])}")
                start_idx = runbook_id_idx
                while start_idx > 0 and ai_yaml[start_idx - 1] not in ['\n', '\r']:
                    start_idx -= 1
                if start_idx > 0 and ai_yaml[start_idx - 1] in ['\n', '\r']:
                    start_idx = start_idx - 1
                ai_yaml = ai_yaml[start_idx:].lstrip()
                logger.info(f"[YAML EXTRACTION] Extracted YAML starting from position {start_idx}, length={len(ai_yaml)}")
        
        # Clean markdown and non-YAML content
        ai_yaml = self._remove_markdown(ai_yaml)
        
        # Verify runbook_id exists
        if ai_yaml and "runbook_id:" not in ai_yaml:
            logger.error(f"[YAML EXTRACTION] ERROR: 'runbook_id:' not found in LLM output after extraction!")
            logger.error(f"[YAML EXTRACTION] First 500 chars: {repr(ai_yaml[:500]) if ai_yaml else 'None'}")
        
        # Remove non-YAML lines at the start
        ai_yaml = self._remove_leading_non_yaml(ai_yaml)
        
        return ai_yaml
    
    def _remove_markdown(self, ai_yaml: str) -> str:
        """Remove markdown formatting from YAML"""
        lines = ai_yaml.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip markdown headers
            if stripped.startswith('#'):
                continue
            # Skip markdown list items
            if stripped.startswith('* '):
                continue
            # Skip lines with tabs that contain markdown syntax
            if '\t' in line and (stripped.startswith('*') or stripped.startswith('- Use:') or 'Use:' in stripped):
                continue
            # Skip lines with common markdown/explanatory patterns
            stripped_lower = stripped.lower()
            if any(pattern in stripped_lower for pattern in [
                'use: get-process',
                'use: get-counter',
                'never use:',
                'examples allowed:',
                'examples:'
            ]):
                continue
            # Skip lines that are just plain text without YAML structure
            if stripped and ':' not in stripped and not stripped.startswith('-') and not re.match(r'^\s*-\s+[a-z_][a-z0-9_]*:', line):
                if not re.match(r'^[a-z_][a-z0-9_]*:', stripped):
                    continue
            
            cleaned_lines.append(line)
        
        ai_yaml = '\n'.join(cleaned_lines)
        
        # Remove markdown code blocks: `code`
        ai_yaml = re.sub(r'`([^`]+)`', r'\1', ai_yaml)
        
        # Remove markdown list markers
        lines = ai_yaml.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('* ') and ':' not in line[:20]:
                cleaned_lines.append(line.replace('* ', '', 1).lstrip())
            elif stripped.startswith('- ') and not re.match(r'^\s*-\s+[a-z_][a-z0-9_]*:', line):
                if ':' not in line or not re.search(r'[a-z_][a-z0-9_]*:\s', line):
                    cleaned_lines.append(line.replace('- ', '', 1).lstrip())
                else:
                    cleaned_lines.append(line)
            elif re.match(r'^\s*\d+\.\s+', stripped):
                cleaned_lines.append(re.sub(r'^\s*\d+\.\s+', '', line))
            elif stripped.startswith('#'):
                continue
            else:
                cleaned_lines.append(line)
        
        ai_yaml = '\n'.join(cleaned_lines)
        
        # Remove markdown bold/italic
        ai_yaml = re.sub(r'\*\*([^*]+)\*\*', r'\1', ai_yaml)
        ai_yaml = re.sub(r'(?<![a-z0-9_])\*([^*\n:]+)\*(?![*a-z0-9_])', r'\1', ai_yaml)
        
        return ai_yaml
    
    def _remove_leading_non_yaml(self, ai_yaml: str) -> str:
        """Remove non-YAML lines at the start"""
        lines = ai_yaml.split('\n')
        yaml_start_idx = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if ':' in stripped and re.match(r'^[a-z_][a-z0-9_]*:', stripped.split(':')[0]):
                yaml_start_idx = i
                break
        
        if yaml_start_idx > 0:
            logger.warning(f"Removing {yaml_start_idx} non-YAML lines from start")
            ai_yaml = '\n'.join(lines[yaml_start_idx:])
        
        return ai_yaml
    
    def fix_newlines_in_yaml(self, ai_yaml: str) -> str:
        """
        Fix newlines in YAML values that break parsing.
        
        Args:
            ai_yaml: YAML string with potential newline issues
            
        Returns:
            Fixed YAML string
        """
        lines = ai_yaml.split('\n')
        fixed_lines = []
        
        for line in lines:
            match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*):\s+(.+)$', line)
            if match:
                indent = match.group(1)
                key = match.group(2)
                value = match.group(3)
                
                # Check if value contains literal newline
                if '\n' in value or '\r' in value:
                    value_clean = value.replace('\r', '').replace('\n', ' ').strip()
                    if len(value_clean) > 100:
                        # Long value - use block scalar
                        value_parts = value.replace('\r', '').split('\n')
                        fixed_lines.append(f"{indent}{key}: |")
                        for part in value_parts:
                            if part.strip():
                                fixed_lines.append(f"{indent}  {part.strip()}")
                    else:
                        # Short value - quote with escaped newline
                        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                        fixed_lines.append(f"{indent}{key}: \"{escaped}\"")
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

