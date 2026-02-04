"""LLM Provider abstraction for pluggable LLM backends."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


from framework.llm.resilience import ResilienceConfig, CircuitBreaker, RetryHandler

@dataclass
class LLMResponse:
    """Response from an LLM call."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_response: Any = None


@dataclass
class Tool:
    """A tool the LLM can use."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolUse:
    """A tool call requested by the LLM."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool."""

    tool_use_id: str
    content: str
    is_error: bool = False


class LLMProvider(ABC):
    """
    Abstract LLM provider - plug in any LLM backend.

    Implementations should handle:
    - API authentication
    - Request/response formatting
    - Token counting
    - Error handling
    """

    def __init__(self, resilience_config: ResilienceConfig | None = None):
        self.resilience_config = resilience_config or ResilienceConfig()
        self._circuit_breaker = CircuitBreaker(self.resilience_config)
        self._retry_handler = RetryHandler(self.resilience_config)

    async def _execute_with_resilience(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Helper to run a provider method with both retry and circuit breaker.
        """
        # Inner function that the circuit breaker will call, which in turn calls retry
        async def _call_with_retry():
            return await self._retry_handler.execute_with_retry(func, *args, **kwargs)
            
        return await self._circuit_breaker.call(_call_with_retry)

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: Conversation history [{role: "user"|"assistant", content: str}]
            system: System prompt
            tools: Available tools for the LLM to use
            max_tokens: Maximum tokens to generate
            response_format: Optional structured output format. Use:
                - {"type": "json_object"} for basic JSON mode
                - {"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}
                  for strict JSON schema enforcement
            json_mode: If True, request structured JSON output from the LLM

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[["ToolUse"], "ToolResult"],
        max_iterations: int = 10,
    ) -> LLMResponse:
        """
        Run a tool-use loop until the LLM produces a final response.

        Args:
            messages: Initial conversation
            system: System prompt
            tools: Available tools
            tool_executor: Function to execute tools: (ToolUse) -> ToolResult
            max_iterations: Max tool calls before stopping

        Returns:
            Final LLMResponse after tool use completes
        """
        pass
