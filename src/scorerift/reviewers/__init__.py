"""LLM-powered review system — the "right brain on demand."

Three review modes:
- Single provider review (Claude, Gemini, or OpenAI)
- OSS swarm review (4 specialized lenses + cross-validation)
- Multi-provider consensus (same prompt to N providers, compare scores)
"""

from scorerift.reviewers.budget import BudgetGuard
from scorerift.reviewers.consensus import consensus_review
from scorerift.reviewers.oss_review import oss_review, swarm_review
from scorerift.reviewers.providers import ClaudeProvider, GeminiProvider, OpenAIProvider

__all__ = [
    "BudgetGuard",
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "oss_review",
    "swarm_review",
    "consensus_review",
]
