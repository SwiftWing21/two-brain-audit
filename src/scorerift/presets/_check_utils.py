"""Shared utilities for preset check functions."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def run_tool(
    cmd: list[str],
    timeout: int = 60,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with platform-safe flags.

    - CREATE_NO_WINDOW on Windows (no console flash)
    - capture_output + text mode
    - Explicit timeout
    """
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if cwd:
        kwargs["cwd"] = cwd
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kwargs)  # noqa: S603 S607


def tool_available(name: str) -> bool:
    """Check if a CLI tool is available on PATH."""
    import shutil
    return shutil.which(name) is not None
