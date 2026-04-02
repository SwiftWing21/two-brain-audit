"""Pluggable integration modules for external data sources."""

from __future__ import annotations

from typing import Any, Protocol

from two_brain_audit.integrations.github import GitHubIntegration
from two_brain_audit.integrations.ollama import OllamaIntegration
from two_brain_audit.integrations.pypi import PyPIIntegration
from two_brain_audit.integrations.semgrep import SemgrepIntegration


class Integration(Protocol):
    """Protocol that all integrations must satisfy.

    An integration provides one or more check functions that can be
    wired to dimensions. It also declares what configuration it needs.
    """

    name: str

    def configure(self, **kwargs: Any) -> None:
        """Accept configuration (API keys, URLs, thresholds)."""
        ...

    def checks(self) -> dict[str, Any]:
        """Return a dict of {check_name: check_callable}.

        Each callable should return (score: float, detail: dict).
        """
        ...


__all__ = ["Integration", "GitHubIntegration", "OllamaIntegration", "PyPIIntegration", "SemgrepIntegration"]
