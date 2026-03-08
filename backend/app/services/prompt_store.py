import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any

from app.services.poml_parser import parse_poml_file, POMLParseError


PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


class PromptNotFound(Exception):
    pass


def _prompt_path(prompt_id: str) -> Path:
    """Resolve path to .poml file."""
    return Path(PROMPTS_DIR) / f"{prompt_id}.poml"


@lru_cache(maxsize=1)
def _load_common_instructions() -> str:
    """Load common instructions from common_instructions.poml (POML format)."""
    common_path = Path(PROMPTS_DIR) / "common_instructions.poml"
    if not common_path.exists():
        return ""
    try:
        result = parse_poml_file(common_path, {})
        return (result.get("system") or "").strip()
    except POMLParseError:
        return ""


def load_prompt(prompt_id: str) -> Dict[str, Any]:
    """Load a POML prompt file and return raw parsed structure (system/user strings without variable substitution)."""
    path = _prompt_path(prompt_id)
    if not path.exists():
        raise PromptNotFound(f"POML prompt '{prompt_id}' not found at {path}")
    return parse_poml_file(path, {})


def render_prompt(prompt_id: str, variables: Dict[str, Any]) -> Dict[str, str]:
    """Render a POML prompt template with provided variables.
    Merges common_instructions.poml into system when present.
    Returns dict with keys: system, user.
    """
    common = _load_common_instructions()
    result = parse_poml_file(_prompt_path(prompt_id), variables)
    system = (result.get("system") or "").strip()
    user = (result.get("user") or "").strip()
    if common:
        system = f"{common}\n\n{system}"
    return {"system": system, "user": user}
