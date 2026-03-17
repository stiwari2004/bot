"""
YAML processor for validating and fixing YAML content from LLM
"""
from app.services.runbook.generation.yaml_structure_mixin import YamlStructureMixin
from app.services.runbook.generation.yaml_sanitizer_mixin import YamlSanitizerMixin


class YamlProcessor(YamlStructureMixin, YamlSanitizerMixin):
    """Processes and fixes YAML content from LLM.

    Structural repairs: YamlStructureMixin (preprocess_yaml_structure, attempt_yaml_autofix)
    Field sanitization: YamlSanitizerMixin (sanitize_description_field, sanitize_command_strings,
                                            fix_yaml_escape_sequences, sanitize_expected_output_field,
                                            fix_standalone_variable_names)
    """
