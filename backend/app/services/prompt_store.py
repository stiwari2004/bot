import os
from functools import lru_cache
from typing import Dict, Any

try:
    import tomllib  # Python 3.11+
    HAS_TOMLLIB = True
except ImportError:
    tomllib = None
    HAS_TOMLLIB = False

try:
    import toml
    HAS_TOML = True
except ImportError:
    toml = None  # type: ignore
    HAS_TOML = False


PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


class PromptNotFound(Exception):
    pass


@lru_cache(maxsize=64)
def _read_toml(path: str) -> Dict[str, Any]:
    if HAS_TOMLLIB:
        with open(path, "rb") as f:
            return tomllib.load(f)
    elif HAS_TOML:
        with open(path, "r") as f:
            return toml.load(f)
    else:
        raise RuntimeError("No TOML library available. Install 'toml' package: pip install toml")


def _prompt_path(prompt_id: str, extension: str = "poml") -> str:
    """Get path to prompt file. Supports both .poml and .toml for backward compatibility."""
    filename = f"{prompt_id}.{extension}"
    path = os.path.join(PROMPTS_DIR, filename)
    # Fallback to .toml if .poml doesn't exist (for backward compatibility)
    if extension == "poml" and not os.path.exists(path):
        toml_path = os.path.join(PROMPTS_DIR, f"{prompt_id}.toml")
        if os.path.exists(toml_path):
            return toml_path
    return path


@lru_cache(maxsize=1)
def _load_common_instructions() -> str:
    """Load common instructions that apply to all runbook generation."""
    common_path = os.path.join(PROMPTS_DIR, "common_instructions.toml")
    if os.path.exists(common_path):
        data = _read_toml(common_path)
        return data.get("common_system", "")
    return ""


def load_prompt(prompt_id: str) -> Dict[str, Any]:
    path = _prompt_path(prompt_id)
    if not os.path.exists(path):
        raise PromptNotFound(f"Prompt '{prompt_id}' not found at {path}")
    data = _read_toml(path)
    return data


def render_prompt(prompt_id: str, variables: Dict[str, Any]) -> Dict[str, str]:
    """Render a prompt template with provided variables.
    
    Combines common instructions with service-specific instructions.
    Expects TOML/POML with keys: system, user_template (optional).
    Performs Python format() substitution: {var} -> variables[var].
    Returns dict with keys: system, user.
    """
    # Load common instructions (cached)
    common_instructions = _load_common_instructions()
    
    # Load service-specific prompt
    data = load_prompt(prompt_id)
    service_system = (data.get("system") or "").format(**variables)
    user_template = data.get("user_template") or ""
    user = user_template.format(**variables)
    
    # Combine common + service-specific system instructions
    if common_instructions:
        system = f"{common_instructions}\n\n{service_system}"
    else:
        system = service_system
    
    # Replace placeholders with double-brace syntax for YAML variables
    user = user.replace("__SERVER_NAME__", "{{server_name}}")
    user = user.replace("__DATABASE_NAME__", "{{database_name}}")
    
    return {"system": system, "user": user}


