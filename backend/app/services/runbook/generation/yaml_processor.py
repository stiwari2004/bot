"""
YAML processor for validating and fixing YAML content from LLM
"""
import re
import yaml
from typing import List, Dict, Any
from app.core.logging import get_logger
from app.config import runbook_structure, runbook_processing

logger = get_logger(__name__)


class YamlProcessor:
    """Processes and fixes YAML content from LLM"""
    
    def preprocess_yaml_structure(self, ai_yaml: str) -> str:
        """Pre-process YAML to fix structural issues before parsing.
        Handles cases where list items appear in the middle of mappings.
        Fixes misindented fields that appear after list items (e.g., description at column 0).
        """
        lines = ai_yaml.splitlines()
        fixed_lines = []
        in_mapping = False
        seen_inputs = False
        seen_steps = False
        current_section = None
        last_list_item_indent = None
        in_list_item = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                fixed_lines.append(line)
                in_list_item = False
                i += 1
                continue
            
            # Detect section headers
            if stripped.endswith(':') and not stripped.startswith('-'):
                section_name = stripped.rstrip(':').strip()
                if section_name in [runbook_structure.SECTION_INPUTS, runbook_structure.SECTION_STEPS, 
                                     runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_POSTCHECKS]:
                    in_mapping = False
                    current_section = section_name
                    fixed_lines.append(line)
                    if section_name == 'inputs':
                        seen_inputs = True
                    elif section_name == 'steps':
                        seen_steps = True
                    last_list_item_indent = None
                    in_list_item = False
                    i += 1
                    continue
            
            # Detect key-value pairs (mappings) at top level
            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s+", stripped) and not stripped.startswith('-'):
                # Check if this is a misindented field that should be part of the previous list item
                if in_list_item and last_list_item_indent is not None:
                    # This field is misindented - it should be part of the list item
                    # Fix it by adding proper indentation
                    indent = ' ' * (last_list_item_indent + 2)  # List items are typically indented 2 spaces
                    fixed_lines.append(indent + stripped)
                    logger.info(f"Fixed misindented field on line {i+1}: '{stripped}' -> '{indent + stripped}' (was at column 0, should be indented {last_list_item_indent + 2} spaces)")
                    i += 1
                    continue
                
                in_mapping = True
                fixed_lines.append(line)
                last_list_item_indent = None
                in_list_item = False
                i += 1
                continue
            
            # Detect list items
            if stripped.startswith('-'):
                # Calculate indentation of this list item
                indent_level = len(line) - len(line.lstrip())
                last_list_item_indent = indent_level
                in_list_item = True
                
                # If we're in a mapping and hit a list item, we need to insert a section header
                if in_mapping:
                    # Determine which section to insert based on content
                    if not seen_inputs and (re.match(r"^-\s+name:\s+", stripped) or 'type:' in lines[i+1] if i+1 < len(lines) else False):
                        fixed_lines.append("inputs:")
                        seen_inputs = True
                        current_section = 'inputs'
                        in_mapping = False
                    elif not seen_steps:
                        fixed_lines.append("steps:")
                        seen_steps = True
                        current_section = 'steps'
                        in_mapping = False
                    else:
                        # Default to steps if we don't know
                        if not seen_steps:
                            fixed_lines.append("steps:")
                            seen_steps = True
                            current_section = 'steps'
                        in_mapping = False
                
                # Check if this list item in 'steps' section looks like an input (has type, required fields)
                if current_section == 'steps' and i+1 < len(lines):
                    # Look ahead to see if this has input-like structure
                    next_few_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                    if 'type:' in next_few_lines and 'required:' in next_few_lines:
                        # This is an input, not a step - move it to inputs section
                        if not seen_inputs:
                            fixed_lines.append("inputs:")
                            seen_inputs = True
                        current_section = 'inputs'
                        logger.info(f"Detected input-like item in steps section on line {i+1}, moving to inputs")
                
                fixed_lines.append(line)
                i += 1
            else:
                # Regular line - check if it's a misindented field that should be part of previous list item
                if in_list_item and last_list_item_indent is not None:
                    # Check if this line looks like a field (has colon) but is not properly indented
                    if ':' in stripped:
                        # Check if it's at column 0 (definitely misindented) or has wrong indentation
                        line_indent = len(line) - len(line.lstrip())
                        expected_indent = last_list_item_indent + 2
                        
                        if line_indent == 0 or (line_indent < expected_indent and line_indent <= last_list_item_indent):
                            # Field is misindented - fix it
                            indent = ' ' * expected_indent
                            fixed_lines.append(indent + stripped)
                            logger.info(f"Fixed misindented field on line {i+1}: '{stripped}' -> '{indent + stripped}' (was indented {line_indent}, should be {expected_indent})")
                            i += 1
                            continue
                
                fixed_lines.append(line)
                # Reset mapping state if we hit a blank line or comment
                if not stripped or stripped.startswith('#'):
                    in_mapping = False
                    last_list_item_indent = None
                    in_list_item = False
                i += 1
        
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
                in_section = key_name if key_name in [
                    runbook_structure.SECTION_INPUTS, runbook_structure.SECTION_STEPS,
                    runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_POSTCHECKS
                ] else None
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
        """Quote command strings containing special characters that break YAML parsing.
        Also fixes incomplete PowerShell parameters (e.g., -MaxSamples without value).
        """
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        
        for line in lines:
            match = re.match(r"^(\s*)command:\s+(.+)$", line)
            if match:
                indent = match.group(1)
                command_value = match.group(2).strip()
                
                # Fix incomplete PowerShell parameters
                # Common parameters that require values: -MaxSamples, -SampleInterval, -Timeout, -Count, etc.
                # CRITICAL: Only add value if parameter doesn't already have one (avoid duplicates like "-MaxSamples 1 1")
                incomplete_param_patterns = [
                    # Match -MaxSamples followed by whitespace and another parameter or end of string (no value)
                    (r'(\s-MaxSamples)(\s+(?=-|\s*$|$))', r'\1 1\2'),  # -MaxSamples -> -MaxSamples 1 (only if no value)
                    (r'(\s-MaxSamples)$', r'\1 1'),  # -MaxSamples at end -> -MaxSamples 1
                    # Match -SampleInterval followed by whitespace and another parameter or end of string (no value)
                    (r'(\s-SampleInterval)(\s+(?=-|\s*$|$))', r'\1 1\2'),  # -SampleInterval -> -SampleInterval 1 (only if no value)
                    (r'(\s-SampleInterval)$', r'\1 1'),  # -SampleInterval at end -> -SampleInterval 1
                    (r'(\s-Timeout)(\s+(?=-|\s*$|$))', r'\1 30\2'),  # -Timeout -> -Timeout 30 (only if no value)
                    (r'(\s-Timeout)$', r'\1 30'),  # -Timeout at end -> -Timeout 30
                    (r'(\s-Count)(\s+(?=-|\s*$|$))', r'\1 1\2'),  # -Count -> -Count 1 (only if no value)
                    (r'(\s-Count)$', r'\1 1'),  # -Count at end -> -Count 1
                    (r'(\s-Limit)(\s+(?=-|\s*$|$))', r'\1 10\2'),  # -Limit -> -Limit 10 (only if no value)
                    (r'(\s-Limit)$', r'\1 10'),  # -Limit at end -> -Limit 10
                ]
                
                for pattern, replacement in incomplete_param_patterns:
                    # Check if pattern matches AND parameter doesn't already have a numeric value after it
                    match = re.search(pattern, command_value)
                    if match:
                        # Check if there's already a value (number) after this parameter
                        param_end = match.end()
                        # Look ahead to see if there's already a number
                        remaining = command_value[param_end:]
                        # If there's already a number immediately after, skip (don't add duplicate)
                        if re.match(r'^\s*\d+', remaining):
                            logger.debug(f"Skipping fix for {pattern} - parameter already has a value")
                            continue
                        command_value = re.sub(pattern, replacement, command_value)
                        logger.info(f"Fixed incomplete PowerShell parameter in command: {pattern} -> {replacement}")
                
                if command_value and not (command_value.startswith('"') or command_value.startswith("'")):
                    special_chars = ['%', '$', '|', '\\', '[', ']', '&', '*', '?', '`']
                    has_special = any(char in command_value for char in special_chars)
                    is_variable_only = bool(re.match(r'^\{\{[a-zA-Z0-9_]+\}\}$', command_value.strip()))
                    
                    if has_special and not is_variable_only:
                        escaped_command = command_value.replace('"', '\\"')
                        sanitized_lines.append(f"{indent}command: \"{escaped_command}\"")
                    else:
                        sanitized_lines.append(f"{indent}command: {command_value}")
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
    
    def sanitize_expected_output_field(self, yaml_content: str) -> str:
        """Quote expected_output values that start with > or <, contain %, or end with : to prevent YAML parsing errors."""
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        
        for line in lines:
            # Match expected_output field (with any indentation)
            match = re.match(r"^(\s*)expected_output:\s+(.+)$", line)
            if match:
                indent = match.group(1)
                value = match.group(2).strip()
                
                # Check if value needs quoting
                needs_quoting = False
                
                # Values starting with > or < can be interpreted as YAML block scalars
                if value.startswith('>') or value.startswith('<'):
                    needs_quoting = True
                # Values containing % often need quoting (e.g., ">50%", "<20%")
                elif '%' in value and not (value.startswith('"') or value.startswith("'")):
                    # Check if it's a comparison like ">50%" or "<20%"
                    if re.match(r'^[<>]=?\s*\d+%', value) or re.match(r'^\d+%', value):
                        needs_quoting = True
                # Values ending with : can be interpreted as YAML mapping separator (e.g., "Address:")
                elif value.endswith(':') and not (value.startswith('"') or value.startswith("'")):
                    needs_quoting = True
                
                if needs_quoting and not (value.startswith('"') or value.startswith("'")):
                    # Escape any existing quotes
                    escaped_value = value.replace('"', '\\"')
                    sanitized_lines.append(f"{indent}expected_output: \"{escaped_value}\"")
                    logger.info(f"Auto-fix: Quoted expected_output value ending with colon: '{value}' -> '\"{escaped_value}\"'")
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        
        return "\n".join(sanitized_lines)
    
    def fix_standalone_variable_names(self, yaml_content: str) -> str:
        """Fix standalone variable names that appear without colons (e.g., 'top_cpu_pid' should be 'captures_variable: top_cpu_pid')."""
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        i = 0
        fixes_applied = []
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                sanitized_lines.append(line)
                i += 1
                continue
            
            # Check if this line looks like a standalone variable name
            # Pattern: starts with lowercase letter, contains only lowercase letters, numbers, underscores
            # Can be at any indentation level (including column 0, though that's unusual)
            # Can be a list item (starting with "- ") or a regular field
            # Must not already have a colon
            # First, strip trailing whitespace for matching
            line_for_matching = line.rstrip()
            
            # Skip if line already has a colon (it's already a proper field)
            if ':' in line_for_matching:
                sanitized_lines.append(line)
                i += 1
                continue
            
            # SPECIAL CASE: Check if this is a mis-indented field at column 0
            # that should be indented to match previous line's indentation
            # OR if it's already been converted to "captures_variable: ..." but still at column 0
            if i > 0 and not line_for_matching.startswith(' ') and not line_for_matching.startswith('-'):
                # This line starts at column 0 (no indentation)
                prev_line = lines[i-1].rstrip()
                
                # Check if this is already "captures_variable: ..." at column 0 (from a previous fix)
                if line_for_matching.startswith('captures_variable:'):
                    # It's already been converted but needs indentation
                    var_name = line_for_matching.replace('captures_variable:', '').strip()
                    # Get previous line's indentation (or look back further for step context)
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    if prev_indent == 0:
                        # Look back further for step context
                        for j in range(i-1, max(0, i-10), -1):
                            if lines[j].strip().startswith('- name:') or lines[j].strip().startswith('command:'):
                                prev_indent = len(lines[j]) - len(lines[j].lstrip())
                                break
                        if prev_indent == 0:
                            prev_indent = 2  # Default to 2 spaces
                    # Fix it by adding proper indentation
                    fixed_line = f"{' ' * prev_indent}captures_variable: {var_name}"
                    sanitized_lines.append(fixed_line)
                    fixes_applied.append({
                        "line": i + 1,
                        "original": line,
                        "fixed": fixed_line,
                        "var_name": var_name,
                        "method": "column-0-indent-fix-existing"
                    })
                    logger.info(f"Fixed column-0 'captures_variable: {var_name}' on line {i+1} to properly indented")
                    i += 1
                    continue
                
                # If previous line ends with ':' and is indented, this should be indented too
                if prev_line.endswith(':') and lines[i-1].startswith(' '):
                    # Check if this looks like a variable name
                    var_pattern_col0 = r'^([a-z][a-z0-9_]+)$'
                    col0_match = re.match(var_pattern_col0, line_for_matching)
                    if col0_match:
                        var_name = col0_match.group(1)
                        # Get previous line's indentation
                        prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                        # Fix it by adding proper indentation
                        fixed_line = f"{' ' * prev_indent}captures_variable: {var_name}"
                        sanitized_lines.append(fixed_line)
                        fixes_applied.append({
                            "line": i + 1,
                            "original": line,
                            "fixed": fixed_line,
                            "var_name": var_name,
                            "method": "column-0-indent-fix"
                        })
                        logger.info(f"Fixed column-0 variable '{var_name}' on line {i+1} (after '{prev_line}') to properly indented 'captures_variable: {var_name}'")
                        i += 1
                        continue
            
            # Pattern 1: Regular field (indented with spaces, no list marker)
            # IMPORTANT: Use \s* (zero or more) not \s+ (one or more) to catch all cases
            variable_pattern = r'^(\s*)([a-z][a-z0-9_]+)$'
            match = re.match(variable_pattern, line_for_matching)
            indent_style = None
            
            # SPECIAL CASE: If it's at column 0 (no indentation) but previous line ends with ':'
            # This is likely a mis-indented field that should be indented
            if match and not match.group(1) and i > 0:
                prev_line = lines[i-1].strip() if i > 0 else ""
                # If previous line ends with ':' and is indented, this should be indented too
                if prev_line.endswith(':') and lines[i-1].startswith(' '):
                    # This is a mis-indented field - it should match the previous line's indentation
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    var_name = match.group(2)
                    # Fix it by adding proper indentation
                    sanitized_lines.append(f"{' ' * prev_indent}captures_variable: {var_name}")
                    fixes_applied.append({
                        "line": i + 1,
                        "original": line,
                        "fixed": f"{' ' * prev_indent}captures_variable: {var_name}",
                        "var_name": var_name,
                        "method": "column-0-fix"
                    })
                    logger.info(f"Fixed column-0 variable '{var_name}' on line {i+1} to properly indented 'captures_variable: {var_name}'")
                    i += 1
                    continue
                
                # Otherwise, check if previous context suggests this is a step field
                context_lines = lines[max(0, i-5):i]
                has_step_context = any('step' in line.lower() or 'command:' in line.lower() or 'name:' in line.lower() or 'depends_on:' in line.lower() for line in context_lines)
                if not has_step_context:
                    # Probably a top-level key, not a variable - skip
                    match = None
            
            # Pattern 2: List item (starts with "- ")
            if not match:
                list_item_pattern = r'^(\s*)(-\s+)([a-z][a-z0-9_]+)$'
                list_match = re.match(list_item_pattern, line_for_matching)
                if list_match:
                    indent_style = 'list'
                    # Create a match-like object
                    class ListMatch:
                        def group(self, n):
                            if n == 1:
                                return list_match.group(1) + list_match.group(2)  # indent + "- "
                            return list_match.group(3)  # var_name
                    match = ListMatch()
            
            # Pattern 3: At column 0 (unusual but possible)
            if not match:
                col0_pattern = r'^([a-z][a-z0-9_]+)$'
                col0_match = re.match(col0_pattern, line_for_matching)
                if col0_match:
                    indent_style = 'col0'
                    class Col0Match:
                        def group(self, n):
                            if n == 1:
                                return ''
                            return col0_match.group(1)
                    match = Col0Match()
            
            if match:
                indent = match.group(1)
                var_name = match.group(2)
                if indent_style is None:
                    indent_style = 'regular'
                
                # AGGRESSIVE FIX: If next non-empty line has a colon, this is definitely a missing field
                # This catches the "mapping values are not allowed here" error
                should_fix = False
                
                # Check next line(s) for fields - be very aggressive
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    
                    # Skip empty lines
                    if not next_stripped:
                        continue
                    
                    # If next non-empty line has a colon, this variable name MUST be a field
                    # This is the most common case causing "mapping values are not allowed here"
                    if ':' in next_stripped:
                        should_fix = True
                        logger.debug(f"Line {i+1} '{var_name}' followed by line with colon '{next_stripped[:50]}' - will fix")
                        break
                
                # If we found a colon in next lines, fix it immediately
                if should_fix:
                    # Convert to captures_variable field
                    # Preserve original indentation style (list item vs regular field)
                    if indent_style == 'list':
                        # It was a list item, convert to list item with field
                        # indent already includes "- ", so we need to extract just the spaces
                        space_indent = re.match(r'^(\s*)', indent).group(1) if indent else ''
                        fixed_line = f"{space_indent}- captures_variable: {var_name}"
                    else:
                        # Regular field or col0
                        fixed_line = f"{indent}captures_variable: {var_name}"
                    
                    sanitized_lines.append(fixed_line)
                    fixes_applied.append({
                        "line": i + 1,
                        "original": line,
                        "fixed": fixed_line,
                        "var_name": var_name
                    })
                    logger.info(f"Fixed standalone variable name '{var_name}' on line {i+1}: {repr(line)} -> {repr(fixed_line)}")
                    i += 1
                    continue
                
                # Also check context from previous lines
                if i > 0:
                    # Look at previous 10 lines for YAML structure indicators
                    context = ' '.join(lines[max(0, i-10):i]).lower()
                    # If we see step-related fields, we're likely in a step
                    if any(indicator in context for indicator in ['name:', 'command:', 'type:', 'step', 'steps:', 'precheck', 'postcheck', '- name:', '- command:']):
                        # If ANY next line has a colon, fix it (very aggressive)
                        for j in range(i + 1, min(i + 3, len(lines))):
                            if ':' in lines[j]:
                                # Preserve original indentation style
                                if indent_style == 'list':
                                    space_indent = re.match(r'^(\s*)', indent).group(1) if indent else ''
                                    fixed_line = f"{space_indent}- captures_variable: {var_name}"
                                else:
                                    fixed_line = f"{indent}captures_variable: {var_name}"
                                
                                sanitized_lines.append(fixed_line)
                                fixes_applied.append({
                                    "line": i + 1,
                                    "original": line,
                                    "fixed": fixed_line,
                                    "var_name": var_name,
                                    "method": "context-based"
                                })
                                logger.info(f"Fixed standalone variable name '{var_name}' on line {i+1} (context-based): {repr(line)} -> {repr(fixed_line)}")
                                i += 1
                                should_fix = True
                                break
                        if should_fix:
                            continue
            
            sanitized_lines.append(line)
            i += 1
        
        if fixes_applied:
            logger.info(f"Applied {len(fixes_applied)} fixes for standalone variable names:")
            for fix in fixes_applied:
                logger.info(f"  Line {fix['line']}: '{fix['original'].strip()}' -> '{fix['fixed'].strip()}'")
        else:
            logger.debug("No standalone variable names found to fix")
        
        return "\n".join(sanitized_lines)




