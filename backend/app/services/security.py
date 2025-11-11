"""
Security utilities for sanitizing execution output.
"""
from __future__ import annotations

import re
from typing import Optional

SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|pwd)\s*[:=]\s*[^\s]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key|token)\s*[:=]\s*[^\s]+", re.IGNORECASE),
    re.compile(r"(secret)\s*[:=]\s*[^\s]+", re.IGNORECASE),
]


def redact_sensitive_text(text: Optional[str]) -> Optional[str]:
    """Basic redaction for secrets present in command output."""
    if not text:
        return text
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted



