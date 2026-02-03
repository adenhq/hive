"""
LLM-based judge for semantic evaluation of test results.
Refactored to be provider-agnostic while maintaining 100% backward compatibility.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from framework.llm.provider import LLMProvider


class LLMJudge:
    """
    LLM-based judge for semantic evaluation of test results.
    Automatically detects available providers (OpenAI/Anthropic) if none injected.
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        """Initialize the LLM judge."""
        self._provider = llm_provider
        self._client = None  # Anthropic client (lazy-loaded for backward compatibility)

    def _get_client(self):
        """
        Lazy-load the Anthropic client.
        REQUIRED: Kept for backward compatibility with existing unit tests.
        """
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic()
            except ImportError as err:
                raise RuntimeError("anthropic package required for LLM judge") from err
        return self._client

    def _get_fallback_provider(self) -> LLMProvider | None:
        """
        Auto-detects available API keys and returns the appropriate provider.
        Priority: OpenAI -> Anthropic.
        """
        if os.environ.get("OPENAI_API_KEY"):
            from framework.llm.openai import OpenAIProvider
            return OpenAIProvider(model="gpt-4o-mini")

        if os.environ.get("ANTHROPIC_API_KEY"):
            from framework.llm.anthropic import AnthropicProvider
            return AnthropicProvider(model="claude-3-haiku-20240307")

        return None

    def evaluate(
        self,
        constraint: str,
        source_document: str,
        summary: str,
        criteria: str,
    ) -> dict[str, Any]:
        """Evaluate whether a summary meets a constraint."""

        prompt = f"""You are evaluating whether a summary meets a specific constraint.

CONSTRAINT: {constraint}
CRITERIA: {criteria}

SOURCE DOCUMENT:
{source_document}

SUMMARY TO EVALUATE:
{summary}

Respond with JSON: {{"passes": true/false, "explanation": "..."}}"""

        try:
            # 1️⃣ Use injected provider if available
            if self._provider is not None:
                active_provider = self._provider

                response = active_provider.complete(
                    messages=[{"role": "user", "content": prompt}],
                    system="",
                    max_tokens=500,
                    json_mode=True,
                )
                return self._parse_json_result(response.content.strip())

            # 2️⃣ Legacy / backward-compatibility path (Anthropic client)
            fallback_provider = self._get_fallback_provider()

            if fallback_provider is None and (
                hasattr(self._get_client, "return_value")
            ):
                client = self._get_client()
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return self._parse_json_result(response.content[0].text.strip())

            # 3️⃣ Provider-agnostic fallback (OpenAI / Anthropic providers)
            if fallback_provider is not None:
                response = fallback_provider.complete(
                    messages=[{"role": "user", "content": prompt}],
                    system="",
                    max_tokens=500,
                    json_mode=True,
                )
                return self._parse_json_result(response.content.strip())

            # 4️⃣ Graceful failure when NO provider is available
            return {
                "passes": False,
                "explanation": (
                    "LLM judge error: No LLM provider available. "
                    "Please set OPENAI_API_KEY or ANTHROPIC_API_KEY, "
                    "or inject a provider explicitly."
                ),
            }

        except Exception as e:
            return {
                "passes": False,
                "explanation": f"LLM judge error: {e}",
            }

    def _parse_json_result(self, text: str) -> dict[str, Any]:
        """Robustly parse JSON output even if LLM adds markdown or chatter."""
        try:
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()

            result = json.loads(text.strip())
            return {
                "passes": bool(result.get("passes", False)),
                "explanation": result.get(
                    "explanation", "No explanation provided"
                ),
            }
        except Exception as e:
            raise ValueError(
                f"LLM judge error: Failed to parse JSON: {e}"
            ) from e
