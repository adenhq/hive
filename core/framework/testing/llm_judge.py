"""
LLM-based judge for semantic evaluation of test results.

Used by tests that need to evaluate semantic properties like
"no hallucination" or "preserves meaning" that can't be checked
with simple assertions.

Usage in tests:
    from framework.testing.llm_judge import LLMJudge

    judge = LLMJudge()
    result = judge.evaluate(
        constraint="no-hallucination",
        source_document="The original text...",
        summary="The summary to evaluate...",
        criteria="Summary must only contain facts from the source"
    )
    assert result["passes"], result["explanation"]
"""

import json
from typing import Any


from framework.llm.provider import LLMProvider


class LLMJudge:
    """
    LLM-based judge for semantic evaluation of test results.

    Uses Claude to evaluate whether outputs meet semantic constraints
    that can't be verified with simple assertions.
    """

    def __init__(self, provider: LLMProvider | None = None):
        """Initialize the LLM judge."""
        self.provider = provider
        self._client = None  # Legacy support

    def _ensure_provider(self):
        """Ensure we have a provider, defaulting to Anthropic if none provided."""
        if self.provider is not None:
            return

        try:
            from framework.llm.anthropic import AnthropicProvider
            self.provider = AnthropicProvider(model="claude-3-5-haiku-20241022")
        except ImportError:
            try:
                from framework.llm.litellm import LiteLLMProvider
                self.provider = LiteLLMProvider(model="claude-3-5-haiku-20241022")
            except ImportError:
                raise RuntimeError("No LLM provider available for LLM judge. Install anthropic or litellm.")

    def evaluate(
        self,
        constraint: str,
        source_document: str,
        summary: str,
        criteria: str,
    ) -> dict[str, Any]:
        """
        Evaluate whether a summary meets a constraint.

        Args:
            constraint: The constraint being tested (e.g., "no-hallucination")
            source_document: The original document
            summary: The generated summary to evaluate
            criteria: Human-readable criteria for evaluation

        Returns:
            Dict with 'passes' (bool) and 'explanation' (str)
        """
        self._ensure_provider()

        prompt = f"""You are evaluating whether a summary meets a specific constraint.

CONSTRAINT: {constraint}
CRITERIA: {criteria}

SOURCE DOCUMENT:
{source_document}

SUMMARY TO EVALUATE:
{summary}

Evaluate whether the summary meets the constraint. Be strict but fair.

Respond with JSON in this exact format:
{{"passes": true/false, "explanation": "brief explanation of your judgment"}}

Only output the JSON, nothing else."""

        try:
            response = self.provider.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You are a semantic evaluation judge. Output only valid JSON.",
                json_mode=True,
            )

            # Parse the response
            text = response.content.strip()
            # Handle potential markdown code blocks (though json_mode should prevent this)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return {
                "passes": bool(result.get("passes", False)),
                "explanation": result.get("explanation", "No explanation provided"),
            }
        except Exception as e:
            # On error, fail the test with explanation
            return {"passes": False, "explanation": f"LLM judge error: {e}"}
