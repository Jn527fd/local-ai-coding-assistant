from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

REDACTED = "[redacted]"

SECRET_KEY_FRAGMENTS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "csrf",
    "password",
    "secret",
    "session",
    "token",
}

CONTENT_KEY_FRAGMENTS = {
    "chat",
    "content",
    "documenttext",
    "extractedtext",
    "message",
    "ocr",
    "passage",
    "prompt",
    "query",
    "snippet",
    "text",
    "transcript",
}

PATH_KEY_FRAGMENTS = {
    "file",
    "filename",
    "filepath",
    "path",
    "repository",
    "storedfilename",
}

SAFE_DECLARATION_KEYS = {
    "contentincluded",
    "privatepathsincluded",
    "secretsincluded",
}


def redact_diagnostics(value: Any) -> Any:
    """Recursively redact secrets, content, and private paths."""

    return _redact(value, parent_key="")


def _redact(value: Any, parent_key: str) -> Any:
    normalized_key = _normalize(parent_key)
    if normalized_key in SAFE_DECLARATION_KEYS and isinstance(value, bool):
        return value
    if _is_sensitive_key(normalized_key):
        return REDACTED
    if isinstance(value, Path):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(key): _redact(item, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, parent_key) for item in value]
    if isinstance(value, tuple):
        return [_redact(item, parent_key) for item in value]
    if isinstance(value, str) and _looks_like_private_path(value):
        return REDACTED
    return value


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(fragment in normalized_key for fragment in SECRET_KEY_FRAGMENTS) or any(
        fragment in normalized_key for fragment in CONTENT_KEY_FRAGMENTS
    ) or any(fragment in normalized_key for fragment in PATH_KEY_FRAGMENTS)


def _normalize(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum() or char == "_")


def _looks_like_private_path(value: str) -> bool:
    if "\\" in value or value.startswith(("/", "~")):
        return True
    return len(value) > 2 and value[1:3] == ":\\"
