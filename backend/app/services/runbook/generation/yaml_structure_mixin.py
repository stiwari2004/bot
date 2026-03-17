"""
YamlStructureMixin — YAML structural fixes (missing section headers, document markers, list orphans)
"""
import re
from typing import List
from app.core.logging import get_logger
from app.config import runbook_structure

logger = get_logger(__name__)


class YamlStructureMixin:
    """Mixin providing YAML structural repair methods"""

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

            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s+", stripped) and not stripped.startswith('-'):
                if in_list_item and last_list_item_indent is not None:
                    indent = ' ' * (last_list_item_indent + 2)
                    fixed_lines.append(indent + stripped)
                    logger.info(f"Fixed misindented field on line {i+1}: '{stripped}' -> '{indent + stripped}'")
                    i += 1
                    continue
                in_mapping = True
                fixed_lines.append(line)
                last_list_item_indent = None
                in_list_item = False
                i += 1
                continue

            if stripped.startswith('-'):
                indent_level = len(line) - len(line.lstrip())
                last_list_item_indent = indent_level
                in_list_item = True

                if in_mapping:
                    if not seen_inputs and (re.match(r"^-\s+name:\s+", stripped) or ('type:' in lines[i+1] if i+1 < len(lines) else False)):
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
                        if not seen_steps:
                            fixed_lines.append("steps:")
                            seen_steps = True
                            current_section = 'steps'
                        in_mapping = False

                if current_section == 'steps' and i+1 < len(lines):
                    next_few_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                    if 'type:' in next_few_lines and 'required:' in next_few_lines:
                        if not seen_inputs:
                            fixed_lines.append("inputs:")
                            seen_inputs = True
                        current_section = 'inputs'
                        logger.info(f"Detected input-like item in steps section on line {i+1}, moving to inputs")

                fixed_lines.append(line)
                i += 1
            else:
                if in_list_item and last_list_item_indent is not None:
                    if ':' in stripped:
                        line_indent = len(line) - len(line.lstrip())
                        expected_indent = last_list_item_indent + 2
                        if line_indent == 0 or (line_indent < expected_indent and line_indent <= last_list_item_indent):
                            indent = ' ' * expected_indent
                            fixed_lines.append(indent + stripped)
                            logger.info(
                                f"Fixed misindented field on line {i+1}: '{stripped}' -> '{indent + stripped}' "
                                f"(was indented {line_indent}, should be {expected_indent})"
                            )
                            i += 1
                            continue

                fixed_lines.append(line)
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
        lines = ai_yaml.splitlines()
        yaml_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if ':' in stripped or stripped.startswith('-'):
                yaml_start_idx = i
                break

        lines = lines[yaml_start_idx:]

        while lines and (not lines[0].strip() or lines[0].strip() == '---'):
            lines = lines[1:]

        if not lines:
            return '---\nversion: 1.0.0\n'

        fixed_lines: List[str] = ['---']

        first_content_idx = 0
        for i, ln in enumerate(lines):
            if ln.strip():
                first_content_idx = i
                break

        for ln in lines[first_content_idx:]:
            if ln.strip() == '---':
                continue
            fixed_lines.append(ln)

        lines = fixed_lines[1:]
        fixed_lines = []

        fixed_lines_second_pass: List[str] = []
        inserted_inputs = False
        inserted_steps = False
        seen_top_level_keys = set()
        in_section = None
        in_mapping = False

        for i, ln in enumerate(lines):
            stripped = ln.strip()

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

            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*:\s+", stripped) and not stripped.startswith('-'):
                in_mapping = True
                in_section = None
                fixed_lines_second_pass.append(ln)
                continue

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
