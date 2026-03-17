"""
YamlSanitizerMixin — YAML field-level sanitization (commands, escapes, descriptions, variables)
"""
import re
from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlSanitizerMixin:
    """Mixin providing YAML field sanitization methods"""

    def sanitize_description_field(self, yaml_content: str) -> str:
        """Clean up description fields that LLMs sometimes corrupt."""
        if not yaml_content:
            return yaml_content

        lines = yaml_content.split("\n")
        sanitized_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("description:") and ":" in stripped:
                parts = stripped.split("description:", 1)
                if len(parts) > 1:
                    value = parts[1].strip()
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

                incomplete_param_patterns = [
                    (r'(\s-MaxSamples)(\s+(?=-|\s*$|$))', r'\1 1\2'),
                    (r'(\s-MaxSamples)$', r'\1 1'),
                    (r'(\s-SampleInterval)(\s+(?=-|\s*$|$))', r'\1 1\2'),
                    (r'(\s-SampleInterval)$', r'\1 1'),
                    (r'(\s-Timeout)(\s+(?=-|\s*$|$))', r'\1 30\2'),
                    (r'(\s-Timeout)$', r'\1 30'),
                    (r'(\s-Count)(\s+(?=-|\s*$|$))', r'\1 1\2'),
                    (r'(\s-Count)$', r'\1 1'),
                    (r'(\s-Limit)(\s+(?=-|\s*$|$))', r'\1 10\2'),
                    (r'(\s-Limit)$', r'\1 10'),
                ]

                for pattern, replacement in incomplete_param_patterns:
                    param_match = re.search(pattern, command_value)
                    if param_match:
                        remaining = command_value[param_match.end():]
                        if re.match(r'^\s*\d+', remaining):
                            logger.debug(f"Skipping fix for {pattern} - parameter already has a value")
                            continue
                        command_value = re.sub(pattern, replacement, command_value)
                        logger.info(f"Fixed incomplete PowerShell parameter: {pattern} -> {replacement}")

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
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def sanitize_expected_output_field(self, yaml_content: str) -> str:
        """Quote expected_output values that start with > or <, contain %, or end with : to prevent YAML parsing errors."""
        if not yaml_content:
            return yaml_content

        lines = yaml_content.split("\n")
        sanitized_lines = []

        for line in lines:
            match = re.match(r"^(\s*)expected_output:\s+(.+)$", line)
            if match:
                indent = match.group(1)
                value = match.group(2).strip()

                if value.startswith('"') and value.count('"') == 1:
                    fixed_value = value + '"'
                    sanitized_lines.append(f"{indent}expected_output: {fixed_value}")
                    logger.info(f"Auto-fix: closed unterminated expected_output scalar: '{value}' -> '{fixed_value}'")
                    continue

                needs_quoting = False
                if value.startswith('>') or value.startswith('<'):
                    needs_quoting = True
                elif '%' in value and not (value.startswith('"') or value.startswith("'")):
                    if re.match(r'^[<>]=?\s*\d+%', value) or re.match(r'^\d+%', value):
                        needs_quoting = True
                elif value.endswith(':') and not (value.startswith('"') or value.startswith("'")):
                    needs_quoting = True

                if needs_quoting and not (value.startswith('"') or value.startswith("'")):
                    escaped_value = value.replace('"', '\\"')
                    sanitized_lines.append(f"{indent}expected_output: \"{escaped_value}\"")
                    logger.info(f"Auto-fix: Quoted expected_output value: '{value}' -> '\"{escaped_value}\"'")
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    def fix_standalone_variable_names(self, yaml_content: str) -> str:
        """Fix standalone variable names that appear without colons
        (e.g., 'top_cpu_pid' should be 'captures_variable: top_cpu_pid').
        """
        if not yaml_content:
            return yaml_content

        lines = yaml_content.split("\n")
        sanitized_lines = []
        i = 0
        fixes_applied = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                sanitized_lines.append(line)
                i += 1
                continue

            line_for_matching = line.rstrip()

            if ':' in line_for_matching:
                sanitized_lines.append(line)
                i += 1
                continue

            if i > 0 and not line_for_matching.startswith(' ') and not line_for_matching.startswith('-'):
                prev_line = lines[i-1].rstrip()

                if line_for_matching.startswith('captures_variable:'):
                    var_name = line_for_matching.replace('captures_variable:', '').strip()
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    if prev_indent == 0:
                        for j in range(i-1, max(0, i-10), -1):
                            if lines[j].strip().startswith('- name:') or lines[j].strip().startswith('command:'):
                                prev_indent = len(lines[j]) - len(lines[j].lstrip())
                                break
                        if prev_indent == 0:
                            prev_indent = 2
                    fixed_line = f"{' ' * prev_indent}captures_variable: {var_name}"
                    sanitized_lines.append(fixed_line)
                    fixes_applied.append({"line": i+1, "original": line, "fixed": fixed_line, "var_name": var_name, "method": "column-0-indent-fix-existing"})
                    logger.info(f"Fixed column-0 'captures_variable: {var_name}' on line {i+1} to properly indented")
                    i += 1
                    continue

                if prev_line.endswith(':') and lines[i-1].startswith(' '):
                    col0_match = re.match(r'^([a-z][a-z0-9_]+)$', line_for_matching)
                    if col0_match:
                        var_name = col0_match.group(1)
                        prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                        fixed_line = f"{' ' * prev_indent}captures_variable: {var_name}"
                        sanitized_lines.append(fixed_line)
                        fixes_applied.append({"line": i+1, "original": line, "fixed": fixed_line, "var_name": var_name, "method": "column-0-indent-fix"})
                        logger.info(f"Fixed column-0 variable '{var_name}' on line {i+1}")
                        i += 1
                        continue

            variable_pattern = r'^(\s*)([a-z][a-z0-9_]+)$'
            match = re.match(variable_pattern, line_for_matching)
            indent_style = None

            if match and not match.group(1) and i > 0:
                prev_line = lines[i-1].strip() if i > 0 else ""
                if prev_line.endswith(':') and lines[i-1].startswith(' '):
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    var_name = match.group(2)
                    sanitized_lines.append(f"{' ' * prev_indent}captures_variable: {var_name}")
                    fixes_applied.append({"line": i+1, "original": line, "fixed": f"{' ' * prev_indent}captures_variable: {var_name}", "var_name": var_name, "method": "column-0-fix"})
                    logger.info(f"Fixed column-0 variable '{var_name}' on line {i+1}")
                    i += 1
                    continue

                context_lines = lines[max(0, i-5):i]
                has_step_context = any('step' in ln.lower() or 'command:' in ln.lower() or 'name:' in ln.lower() or 'depends_on:' in ln.lower() for ln in context_lines)
                if not has_step_context:
                    match = None

            if not match:
                list_item_pattern = r'^(\s*)(-\s+)([a-z][a-z0-9_]+)$'
                list_match = re.match(list_item_pattern, line_for_matching)
                if list_match:
                    indent_style = 'list'
                    _lm = list_match
                    class ListMatch:
                        def group(self, n):
                            if n == 1:
                                return _lm.group(1) + _lm.group(2)
                            return _lm.group(3)
                    match = ListMatch()

            if not match:
                col0_match = re.match(r'^([a-z][a-z0-9_]+)$', line_for_matching)
                if col0_match:
                    indent_style = 'col0'
                    _cm = col0_match
                    class Col0Match:
                        def group(self, n):
                            if n == 1:
                                return ''
                            return _cm.group(1)
                    match = Col0Match()

            if match:
                indent = match.group(1)
                var_name = match.group(2)
                if indent_style is None:
                    indent_style = 'regular'

                should_fix = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_stripped = lines[j].strip()
                    if not next_stripped:
                        continue
                    if ':' in next_stripped:
                        should_fix = True
                        break

                if should_fix:
                    if indent_style == 'list':
                        space_indent = re.match(r'^(\s*)', indent).group(1) if indent else ''
                        fixed_line = f"{space_indent}- captures_variable: {var_name}"
                    else:
                        fixed_line = f"{indent}captures_variable: {var_name}"
                    sanitized_lines.append(fixed_line)
                    fixes_applied.append({"line": i+1, "original": line, "fixed": fixed_line, "var_name": var_name})
                    logger.info(f"Fixed standalone variable name '{var_name}' on line {i+1}: {repr(line)} -> {repr(fixed_line)}")
                    i += 1
                    continue

                if i > 0:
                    context = ' '.join(lines[max(0, i-10):i]).lower()
                    if any(ind in context for ind in ['name:', 'command:', 'type:', 'step', 'steps:', 'precheck', 'postcheck', '- name:', '- command:']):
                        for j in range(i + 1, min(i + 3, len(lines))):
                            if ':' in lines[j]:
                                if indent_style == 'list':
                                    space_indent = re.match(r'^(\s*)', indent).group(1) if indent else ''
                                    fixed_line = f"{space_indent}- captures_variable: {var_name}"
                                else:
                                    fixed_line = f"{indent}captures_variable: {var_name}"
                                sanitized_lines.append(fixed_line)
                                fixes_applied.append({"line": i+1, "original": line, "fixed": fixed_line, "var_name": var_name, "method": "context-based"})
                                logger.info(f"Fixed standalone variable name '{var_name}' on line {i+1} (context-based)")
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
