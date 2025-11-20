"""
YAML processor for validating and fixing YAML content from LLM
"""
import re
import yaml
from typing import List, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlProcessor:
    """Processes and fixes YAML content from LLM"""
    
    def preprocess_yaml_structure(self, ai_yaml: str) -> str:
        """Pre-process YAML to fix structural issues before parsing.
        Handles cases where list items appear in the middle of mappings.
        """
        lines = ai_yaml.splitlines()
        fixed_lines = []
        in_mapping = False
        seen_inputs = False
        seen_steps = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect section headers
            if stripped.endswith(':') and not stripped.startswith('-'):
                section_name = stripped.rstrip(':').strip()
                if section_name in ['inputs', 'steps', 'prechecks', 'postchecks']:
                    in_mapping = False
                    fixed_lines.append(line)
                    if section_name == 'inputs':
                        seen_inputs = True
                    elif section_name == 'steps':
                        seen_steps = True
                    continue
            
            # Detect key-value pairs (mappings)
            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s+", stripped) and not stripped.startswith('-'):
                in_mapping = True
                fixed_lines.append(line)
                continue
            
            # Detect list items
            if stripped.startswith('-'):
                # If we're in a mapping and hit a list item, we need to insert a section header
                if in_mapping:
                    # Determine which section to insert
                    if not seen_inputs and re.match(r"^-\s+name:\s+", stripped):
                        fixed_lines.append("inputs:")
                        seen_inputs = True
                        in_mapping = False
                    elif not seen_steps:
                        fixed_lines.append("steps:")
                        seen_steps = True
                        in_mapping = False
                    else:
                        # Default to steps if we don't know
                        if not seen_steps:
                            fixed_lines.append("steps:")
                            seen_steps = True
                        in_mapping = False
                fixed_lines.append(line)
            else:
                # Regular line
                fixed_lines.append(line)
                # Reset mapping state if we hit a blank line or comment
                if not stripped or stripped.startswith('#'):
                    in_mapping = False
        
        return "\n".join(fixed_lines)
    
    def attempt_yaml_autofix(self, ai_yaml: str) -> str:
        """Heuristically repair common LLM YAML defects:
        - Missing document start marker (---)
        - Missing section headers before list items (e.g., inputs/steps)
        - Ensure top-level lists have a preceding key
        - Remove leading text/comments before YAML
        """
        # Remove leading non-YAML content (text, comments, etc.)
        lines = ai_yaml.splitlines()
        yaml_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip empty lines and comments at the start
            if not stripped or stripped.startswith('#'):
                continue
            # If we find a line that looks like YAML (key: value or list item), start here
            if ':' in stripped or stripped.startswith('-'):
                yaml_start_idx = i
                break
        
        lines = lines[yaml_start_idx:]
        
        # Remove any existing document start marker and empty lines
        while lines and (not lines[0].strip() or lines[0].strip() == '---'):
            lines = lines[1:]
        
        # Ensure YAML starts with document marker directly followed by content (no empty line)
        if not lines:
            return '---\nversion: 1.0.0\n'
        
        fixed_lines: List[str] = ['---']
        
        # Skip any empty lines right after ---, then add all content
        first_content_idx = 0
        for i, ln in enumerate(lines):
            if ln.strip():
                first_content_idx = i
                break
        
        # Add all lines starting from first non-empty line, but skip any additional --- markers
        for ln in lines[first_content_idx:]:
            # Skip any additional document start markers
            if ln.strip() == '---':
                continue
            fixed_lines.append(ln)
        
        # Reset for second pass - but don't add another ---
        lines = fixed_lines[1:]  # Skip the first '---' for processing
        fixed_lines = []
        
        # Second pass: Fix orphaned list items (list items without parent keys)
        fixed_lines_second_pass: List[str] = []
        inserted_inputs = False
        inserted_steps = False
        seen_top_level_keys = set()
        in_section = None
        in_mapping = False
        
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            
            # Detect top-level keys (section headers)
            top_key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_\-]*):\s*$", stripped)
            if top_key_match:
                key_name = top_key_match.group(1)
                seen_top_level_keys.add(key_name)
                in_section = key_name if key_name in ['inputs', 'steps', 'prechecks', 'postchecks'] else None
                in_mapping = False
                fixed_lines_second_pass.append(ln)
                continue
            
            # Detect key-value pairs (mappings)
            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s+", stripped) and not stripped.startswith('-'):
                in_mapping = True
                in_section = None
                fixed_lines_second_pass.append(ln)
                continue
            
            # Detect list items that might be orphaned or misplaced
            if stripped.startswith('-'):
                if in_mapping:
                    if 'inputs' not in seen_top_level_keys and not inserted_inputs:
                        fixed_lines_second_pass.append("inputs:")
                        inserted_inputs = True
                        in_section = 'inputs'
                        in_mapping = False
                    elif 'steps' not in seen_top_level_keys and not inserted_steps:
                        fixed_lines_second_pass.append("steps:")
                        inserted_steps = True
                        in_section = 'steps'
                        in_mapping = False
                    else:
                        if not inserted_steps:
                            fixed_lines_second_pass.append("steps:")
                            inserted_steps = True
                            in_section = 'steps'
                            in_mapping = False
                elif in_section is None:
                    prev_non_empty = ""
                    for j in range(len(fixed_lines_second_pass) - 1, -1, -1):
                        prev_ln = fixed_lines_second_pass[j].strip()
                        if prev_ln and not prev_ln.startswith('#'):
                            prev_non_empty = prev_ln
                            break
                    
                    if not prev_non_empty.endswith(':'):
                        if 'inputs' not in seen_top_level_keys and not inserted_inputs:
                            fixed_lines_second_pass.append("inputs:")
                            inserted_inputs = True
                            in_section = 'inputs'
                        elif 'steps' not in seen_top_level_keys and not inserted_steps:
                            fixed_lines_second_pass.append("steps:")
                            inserted_steps = True
                            in_section = 'steps'
                        else:
                            if not inserted_steps:
                                fixed_lines_second_pass.append("steps:")
                                inserted_steps = True
                                in_section = 'steps'
                
                fixed_lines_second_pass.append(ln)
                in_mapping = False
            else:
                if stripped and not stripped.startswith('-') and not stripped.startswith('#'):
                    if ':' in stripped and not stripped.endswith(':'):
                        in_mapping = True
                    in_section = None
                fixed_lines_second_pass.append(ln)
        
        candidate = "\n".join(fixed_lines_second_pass)
        
        # Final pass: Ensure all top-level lists have headers
        final_lines: List[str] = []
        last_was_key = False
        
        for ln in candidate.splitlines():
            stripped = ln.strip()
            
            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s*$", stripped):
                last_was_key = True
                final_lines.append(ln)
                continue
            
            if stripped.startswith('-') and last_was_key:
                final_lines.append(ln)
                last_was_key = False
                continue
            
            if stripped.startswith('-') and not last_was_key:
                prev_was_key = False
                for j in range(len(final_lines) - 1, -1, -1):
                    prev_ln = final_lines[j].strip()
                    if prev_ln and not prev_ln.startswith('#'):
                        prev_was_key = prev_ln.endswith(':')
                        break
                
                if not prev_was_key:
                    if 'inputs:' not in '\n'.join(final_lines) and re.match(r"^-\s+name:\s+", stripped):
                        final_lines.append("inputs:")
                    elif 'steps:' not in '\n'.join(final_lines):
                        final_lines.append("steps:")
            
            last_was_key = False
            final_lines.append(ln)
        
        result = "\n".join(final_lines)
        
        # Final cleanup: Ensure only one document start marker at the beginning
        result_lines = result.splitlines()
        cleaned_lines = []
        found_first_marker = False
        for ln in result_lines:
            stripped = ln.strip()
            if stripped == '---':
                if not found_first_marker:
                    cleaned_lines.append('---')
                    found_first_marker = True
                continue
            cleaned_lines.append(ln)
        
        if cleaned_lines and cleaned_lines[0] != '---':
            cleaned_lines.insert(0, '---')
        
        return "\n".join(cleaned_lines)
    
    def sanitize_description_field(self, yaml_content: str) -> str:
        """Clean up description fields that LLMs sometimes corrupt."""
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith("description:") and ":" in stripped:
                parts = stripped.split("description:", 1)
                if len(parts) > 1:
                    value = parts[1].strip()
                    # Remove common patterns that LLMs add incorrectly
                    value = re.sub(r'\s*\.?\s*Service:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    value = re.sub(r'\s*\.?\s*Environment:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    value = re.sub(r'\s*\.?\s*Env:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    sanitized_lines.append("description: " + value)
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        
        return "\n".join(sanitized_lines)
    
    def sanitize_command_strings(self, yaml_content: str) -> str:
        """Quote command strings containing special characters that break YAML parsing."""
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        
        for line in lines:
            match = re.match(r"^(\s*)command:\s+(.+)$", line)
            if match:
                indent = match.group(1)
                command_value = match.group(2).strip()
                
                if command_value and not (command_value.startswith('"') or command_value.startswith("'")):
                    special_chars = ['%', '$', '|', '\\', '[', ']', '&', '*', '?', '`']
                    has_special = any(char in command_value for char in special_chars)
                    is_variable_only = bool(re.match(r'^\{\{[a-zA-Z0-9_]+\}\}$', command_value.strip()))
                    
                    if has_special and not is_variable_only:
                        escaped_command = command_value.replace('"', '\\"')
                        sanitized_lines.append(f"{indent}command: \"{escaped_command}\"")
                    else:
                        sanitized_lines.append(line)
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        
        return "\n".join(sanitized_lines)
    
    def fix_yaml_escape_sequences(self, yaml_content: str) -> str:
        """Fix invalid escape sequences in double-quoted YAML strings."""
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        fixed_lines = []
        
        for line in lines:
            match = re.match(r"^(\s*command:\s+)\"(.+)\"$", line)
            if match:
                indent_and_key = match.group(1)
                quoted_content = match.group(2)
                
                if '\\' in quoted_content:
                    escaped_content = quoted_content.replace("'", "''")
                    fixed_lines.append(f"{indent_and_key}'{escaped_content}'")
                else:
                    fixed_lines.append(line)
            else:
                if re.match(r"^(\s*command:\s+)\"", line) and not line.rstrip().endswith('"'):
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
        
        return "\n".join(fixed_lines)




