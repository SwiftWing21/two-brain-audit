"""Lightweight LLM provider clients for audit reviews.

Each provider takes a system prompt + user prompt, returns structured JSON.
No HA fallback or circuit breakers — keep it simple for the standalone tool.
API keys via environment variables.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("two_brain_audit.reviewers")

# ── Pricing (per 1M tokens, USD) ────────────────────────────────────

PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


@dataclass
class ReviewResult:
    """Structured result from an LLM review."""

    grade: str
    score: float
    confidence: float
    findings: list[str]
    recommendations: list[str]
    raw_response: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model, {})
    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
    return round(input_cost + output_cost, 6)


def _parse_review_json(text: str, provider: str, model: str) -> dict[str, Any]:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove first and last ``` lines
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("Failed to parse %s/%s response as JSON", provider, model)
        return {"grade": "C", "confidence": 0.3, "findings": ["Response was not valid JSON"],
                "recommendations": [], "raw": text[:500]}


# ── Review Prompt ────────────────────────────────────────────────────

REVIEW_SYSTEM = """You are an expert code auditor reviewing the "{dimension}" dimension of a software project.

Grade scale: S=1.0, A+=0.95, A=0.90, A-=0.85, B+=0.80, B=0.75, B-=0.70, C+=0.65, C=0.60, D=0.50, F=0.30.

Return ONLY valid JSON:
{{"grade": "A", "confidence": 0.85, "findings": ["..."], "recommendations": ["..."]}}

Be specific. Cite file names and line numbers. Confidence = how thorough your review was (0.0-1.0)."""


def build_review_prompt(dimension: str, context: str, lens: str | None = None) -> tuple[str, str]:
    """Build system + user prompts for a review.

    Args:
        dimension: What to review (e.g., "security", "architecture")
        context: Project context (file listings, code snippets, config)
        lens: Optional specialized perspective (e.g., "security auditor")
    """
    system = REVIEW_SYSTEM.format(dimension=dimension)
    if lens:
        system = f"You are a {lens}.\n\n" + system

    user = f"Review the following project for the '{dimension}' dimension:\n\n{context}"
    return system, user


# ── Provider Implementations ─────────────────────────────────────────

class ClaudeProvider:
    """Anthropic Claude API client."""

    name = "claude"

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def review(self, system: str, user: str) -> ReviewResult:
        if not self.available:
            return ReviewResult(grade="", score=0, confidence=0,
                                findings=["ANTHROPIC_API_KEY not set"], recommendations=[],
                                provider=self.name, model=self.model)

        import httpx

        t0 = time.perf_counter()
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 2048,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60,
        )
        latency = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()

        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        parsed = _parse_review_json(text, self.name, self.model)
        from two_brain_audit.grades import grade_to_score
        grade = parsed.get("grade", "C")
        return ReviewResult(
            grade=grade,
            score=grade_to_score(grade),
            confidence=parsed.get("confidence", 0.5),
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            raw_response=text,
            model=self.model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_calc_cost(self.model, input_tokens, output_tokens),
            latency_ms=latency,
        )


class GeminiProvider:
    """Google Gemini API client."""

    name = "gemini"

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def review(self, system: str, user: str) -> ReviewResult:
        if not self.available:
            return ReviewResult(grade="", score=0, confidence=0,
                                findings=["GOOGLE_API_KEY not set"], recommendations=[],
                                provider=self.name, model=self.model)

        import httpx

        t0 = time.perf_counter()
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            headers={"content-type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": user}]}],
                "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.2},
            },
            timeout=60,
        )
        latency = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        parsed = _parse_review_json(text, self.name, self.model)
        from two_brain_audit.grades import grade_to_score
        grade = parsed.get("grade", "C")
        return ReviewResult(
            grade=grade,
            score=grade_to_score(grade),
            confidence=parsed.get("confidence", 0.5),
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            raw_response=text,
            model=self.model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_calc_cost(self.model, input_tokens, output_tokens),
            latency_ms=latency,
        )


class OpenAIProvider:
    """OpenAI / ChatGPT API client."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def review(self, system: str, user: str) -> ReviewResult:
        if not self.available:
            return ReviewResult(grade="", score=0, confidence=0,
                                findings=["OPENAI_API_KEY not set"], recommendations=[],
                                provider=self.name, model=self.model)

        import httpx

        t0 = time.perf_counter()
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 2048,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60,
        )
        latency = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        parsed = _parse_review_json(text, self.name, self.model)
        from two_brain_audit.grades import grade_to_score
        grade = parsed.get("grade", "C")
        return ReviewResult(
            grade=grade,
            score=grade_to_score(grade),
            confidence=parsed.get("confidence", 0.5),
            findings=parsed.get("findings", []),
            recommendations=parsed.get("recommendations", []),
            raw_response=text,
            model=self.model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_calc_cost(self.model, input_tokens, output_tokens),
            latency_ms=latency,
        )


# ── Provider Registry ────────────────────────────────────────────────

ALL_PROVIDERS = [ClaudeProvider, GeminiProvider, OpenAIProvider]


def get_available_providers() -> list:
    """Return instances of providers with API keys configured."""
    return [P() for P in ALL_PROVIDERS if P().available]
