"""Audit output sanitizer — strips sensitive data before public export."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("scorerift")

# Keys that are stripped by default (case-insensitive substring match)
DEFAULT_STRIP_KEYS: frozenset[str] = frozenset({
    "password", "secret", "key", "token", "api_key",
    "endpoint", "hostname", "username", "credentials",
})

# Regex patterns for absolute paths
_UNIX_PATH_RE = re.compile(
    r"(/(?:home|usr|opt|var|tmp|etc|root|Users)/)[^\s\"',;:}\]]*",
)
_WIN_PATH_RE = re.compile(
    r"([A-Za-z]:\\(?:Users|home|Program Files|Windows)[^\s\"',;:}\]]*)",
)

PATH_PLACEHOLDER = "./"


@dataclass
class SanitizeConfig:
    """Configuration for the sanitizer.

    Attributes:
        strip_keys: Extra key names to strip (added to defaults).
        keep_keys: Key names to keep even if they match a default strip pattern.
        path_roots: Additional path prefixes to replace with ``./``.
    """

    strip_keys: set[str] = field(default_factory=set)
    keep_keys: set[str] = field(default_factory=set)
    path_roots: list[str] = field(default_factory=list)


def load_config(project_root: str | Path = ".") -> SanitizeConfig | None:
    """Load ``.tba-sanitize.json`` from *project_root* if it exists."""
    config_path = Path(project_root).resolve() / ".tba-sanitize.json"
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return SanitizeConfig(
            strip_keys=set(raw.get("strip_keys", [])),
            keep_keys=set(raw.get("keep_keys", [])),
            path_roots=list(raw.get("path_roots", [])),
        )
    except Exception:
        log.warning("Failed to parse %s, using defaults", config_path)
        return None


def _should_strip(key: str, config: SanitizeConfig | None) -> bool:
    """Return True if *key* should be redacted."""
    lower = key.lower()
    keep = config.keep_keys if config else set()
    if lower in keep or key in keep:
        return False
    all_strip = DEFAULT_STRIP_KEYS | (config.strip_keys if config else set())
    return any(s in lower for s in all_strip)


def _sanitize_path(value: str, config: SanitizeConfig | None) -> str:
    """Replace absolute paths with ``./`` placeholder."""
    result = _UNIX_PATH_RE.sub(PATH_PLACEHOLDER, value)
    result = _WIN_PATH_RE.sub(PATH_PLACEHOLDER, result)
    if config:
        for root in config.path_roots:
            if root:
                result = result.replace(root, PATH_PLACEHOLDER)
    return result


def _walk(obj: Any, config: SanitizeConfig | None) -> Any:
    """Recursively sanitize dicts and lists."""
    if isinstance(obj, dict):
        return {
            k: _walk(v, config)
            for k, v in obj.items()
            if not _should_strip(k, config)
        }
    if isinstance(obj, list):
        return [_walk(item, config) for item in obj]
    if isinstance(obj, str):
        return _sanitize_path(obj, config)
    return obj


def sanitize(data: dict[str, Any], config: SanitizeConfig | None = None) -> dict[str, Any]:
    """Deep-walk *data* and strip sensitive keys / absolute paths.

    Args:
        data: Audit output dict (e.g. from ``export_json``).
        config: Optional override config. If ``None``, only defaults apply.

    Returns:
        A new dict with sensitive material removed.
    """
    return _walk(data, config)


def sanitize_text(text: str, config: SanitizeConfig | None = None) -> str:
    """Apply path sanitization to plain text (CSV / Markdown output).

    Key stripping does not apply — only path replacement.
    """
    result = _UNIX_PATH_RE.sub(PATH_PLACEHOLDER, text)
    result = _WIN_PATH_RE.sub(PATH_PLACEHOLDER, result)
    if config:
        for root in config.path_roots:
            if root:
                result = result.replace(root, PATH_PLACEHOLDER)
    return result
