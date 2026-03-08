"""
POML (Prompt Orchestration Markup Language) parser for runbook prompt templates.

Schema: XML-like structure with root <poml>, optional <system> and <user> elements.
Variable substitution: {var_name} in content is replaced by variables[var_name].
Literal double-braces in output (e.g. {{server_name}} for YAML) can be written
as __SERVER_NAME__ / __DATABASE_NAME__ and are replaced after substitution.

No TOML is used; this module parses POML only (via xml.etree.ElementTree).
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Union, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class POMLParseError(Exception):
    """Raised when POML content cannot be parsed or is invalid."""

    pass


def _get_element_text(element: ET.Element) -> str:
    """Get full text content of an element (including CDATA)."""
    if element is None:
        return ""
    text = element.text or ""
    for child in element:
        text += _get_element_text(child)
        text += child.tail or ""
    return text


def _substitute_variables(text: str, variables: Dict[str, Any]) -> str:
    """Replace {var_name} with variables[var_name]; missing keys become empty string.
    Literal {{ and }} in the source are preserved by first escaping to a sentinel, then restoring.
    """
    if not text:
        return text
    # Temporarily replace literal {{ and }} so format_map doesn't treat them as escaped braces
    _OPEN, _CLOSE = "\x00POML_LBRACE\x00", "\x00POML_RBRACE\x00"
    text = text.replace("{{", _OPEN).replace("}}", _CLOSE)
    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return ""

    safe = SafeDict({k: (v if v is not None else "") for k, v in variables.items()})
    try:
        text = text.format_map(safe)
    except KeyError as e:
        logger.warning("POML variable %s not in variables dict; leaving placeholder", e)
    text = text.replace(_OPEN, "{{").replace(_CLOSE, "}}")
    return text


def _apply_literal_placeholders(text: str) -> str:
    """Replace __SERVER_NAME__ / __DATABASE_NAME__ with {{server_name}} / {{database_name}} for YAML."""
    text = text.replace("__SERVER_NAME__", "{{server_name}}")
    text = text.replace("__DATABASE_NAME__", "{{database_name}}")
    return text


def parse_poml(
    content: Union[str, Path],
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Parse POML content and return rendered system and user prompt strings.

    Args:
        content: Either raw POML string or path to a .poml file.
        variables: Dict for variable substitution (e.g. issue_description, service, env, risk, context, os_type).
                  Keys missing in content are ignored; placeholders missing in variables become "".

    Returns:
        Dict with keys "system" and "user". Either may be empty string if the corresponding element is absent.

    Raises:
        POMLParseError: If XML is invalid or root is not <poml>.
    """
    if variables is None:
        variables = {}

    if isinstance(content, Path):
        content = content.read_text(encoding="utf-8")
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    content = content.strip()
    if not content:
        raise POMLParseError("POML content is empty")

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise POMLParseError(f"Invalid POML XML: {e}") from e

    if root.tag != "poml":
        # Allow case-insensitive or namespaced root
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag.lower() != "poml":
            raise POMLParseError(f"POML root element must be <poml>, got <{root.tag}>")

    system_el = root.find("system")
    user_el = root.find("user")
    # Backward compatibility: some POML may use user_template
    if user_el is None:
        user_el = root.find("user_template")

    system_raw = _get_element_text(system_el).strip() if system_el is not None else ""
    user_raw = _get_element_text(user_el).strip() if user_el is not None else ""

    system = _substitute_variables(system_raw, variables)
    user = _substitute_variables(user_raw, variables)

    system = _apply_literal_placeholders(system)
    user = _apply_literal_placeholders(user)

    return {"system": system, "user": user}


def parse_poml_file(
    file_path: Union[str, Path],
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Load and parse a .poml file from disk.

    Args:
        file_path: Path to the .poml file.
        variables: Dict for variable substitution.

    Returns:
        Dict with keys "system" and "user".
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"POML file not found: {path}")
    content = path.read_text(encoding="utf-8")
    return parse_poml(content, variables)
