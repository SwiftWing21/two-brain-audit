"""Ollama integration — local model availability and health.

Binary check: /api/tags responds AND >= 1 model loaded = 1.0, else 0.0.
Feeds into: performance dimension.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("scorerift.integrations.ollama")


class OllamaIntegration:
    """Check local Ollama instance health."""

    name = "ollama"

    def __init__(self) -> None:
        self.host: str = "http://localhost:11434"
        self.timeout: int = 5

    def configure(self, host: str = "http://localhost:11434", timeout: int = 5, **kwargs: Any) -> None:
        self.host = host.rstrip("/")
        self.timeout = timeout

    def checks(self) -> dict[str, Any]:
        return {"ollama_health": self.check_health}

    def check_health(self) -> tuple[float, dict[str, Any]]:
        """Binary: Ollama responds and has >= 1 model loaded."""
        import json
        import urllib.request

        try:
            req = urllib.request.Request(f"{self.host}/api/tags")  # noqa: S310
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                data = json.loads(resp.read())
            models = data.get("models", [])
            if models:
                names = [m.get("name", "?") for m in models[:5]]
                return 1.0, {"models": len(models), "sample": names}
            return 0.0, {"note": "Ollama running but no models loaded"}
        except Exception as e:
            return 0.0, {"error": str(e), "note": "Ollama not reachable"}
