from typing import Any
from framework.llm.provider import (
    LLMProvider,
    LLMResponse,
    Tool,
    ToolUse,
    ToolResult,
)
class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing without API keys."""

    def __init__(self, model: str = "mock-model", responses: dict[str, str] = None):
        self.model = model
        self.responses = responses or {}
        self.call_count = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.call_count += 1
        last_msg = messages[-1].get("content", "") if messages else ""
        content = self.responses.get(
            last_msg,
            f"[Mock response #{self.call_count}]"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=len(str(messages)),
            output_tokens=len(content),
            stop_reason="end_turn",
        )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: callable,
        max_iterations: int = 10,
    ) -> LLMResponse:
        self.call_count += 1
        last_msg = messages[-1].get("content", "") if messages else ""
        content = self.responses.get(
            last_msg,
            f"[Mock response with tools #{self.call_count}]"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=len(str(messages)),
            output_tokens=len(content),
            stop_reason="end_turn",
        )
