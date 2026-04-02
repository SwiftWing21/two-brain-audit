"""LLM-powered review system — the "right brain on demand."

Three review modes:
- Single provider review (Claude, Gemini, or OpenAI)
- OSS swarm review (4 specialized lenses + cross-validation)
- Multi-provider consensus (same prompt to N providers, compare scores)
"""

from two_brain_audit.reviewers.consensus import consensus_review
from two_brain_audit.reviewers.oss_review import oss_review, swarm_review
from two_brain_audit.reviewers.providers import ClaudeProvider, GeminiProvider, OpenAIProvider

__all__ = [
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "oss_review",
    "swarm_review",
    "consensus_review",
]
