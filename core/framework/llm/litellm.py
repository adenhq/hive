"""LiteLLM provider for pluggable multi-provider LLM support.

LiteLLM provides a unified, OpenAI-compatible interface that supports
multiple LLM providers including OpenAI, Anthropic, Gemini, Mistral,
Groq, and local models.

See: https://docs.litellm.ai/docs/providers

Security Features:
- Token budget limits (per-call and per-session)
- Circuit breaker pattern to prevent cascade failures
- Cost tracking for monitoring and alerting
"""

import json
import logging
import time
from typing import Any

import litellm

from framework.llm.provider import LLMProvider, LLMResponse, Tool, ToolUse

logger = logging.getLogger(__name__)


class TokenBudgetExceeded(Exception):
    """Raised when token budget is exceeded."""
    
    def __init__(self, message: str, tokens_used: int, budget: int):
        super().__init__(message)
        self.tokens_used = tokens_used
        self.budget = budget


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open due to consecutive failures."""
    
    def __init__(self, message: str, failure_count: int, cooldown_remaining: float):
        super().__init__(message)
        self.failure_count = failure_count
        self.cooldown_remaining = cooldown_remaining


class LiteLLMProvider(LLMProvider):
    """
    LiteLLM-based LLM provider for multi-provider support.

    Supports any model that LiteLLM supports, including:
    - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    - Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
    - Google: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
    - Mistral: mistral-large, mistral-medium, mistral-small
    - Groq: llama3-70b, mixtral-8x7b
    - Local: ollama/llama3, ollama/mistral
    - And many more...

    Security Features:
    - Token budget limits to prevent runaway costs
    - Circuit breaker to prevent cascade failures
    - Cost tracking for monitoring

    Usage:
        # Basic usage
        provider = LiteLLMProvider(model="gpt-4o-mini")

        # With token limits (recommended for production)
        provider = LiteLLMProvider(
            model="gpt-4o-mini",
            max_session_tokens=100000,  # Max tokens per session
            max_call_tokens=4096,       # Max tokens per call
        )

        # Check usage
        print(f"Tokens used: {provider.session_tokens}")
        print(f"Estimated cost: ${provider.estimated_cost:.4f}")
    """

    # Default token limits
    DEFAULT_MAX_SESSION_TOKENS = 500_000  # 500k tokens per session
    DEFAULT_MAX_CALL_TOKENS = 8192        # 8k tokens per call
    
    # Circuit breaker settings
    CIRCUIT_BREAKER_THRESHOLD = 3         # Consecutive failures before opening
    CIRCUIT_BREAKER_COOLDOWN = 60.0       # Seconds to wait before retrying

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
        max_session_tokens: int | None = None,
        max_call_tokens: int | None = None,
        enable_circuit_breaker: bool = True,
        temperature: float | None = None,
        **kwargs: Any,
    ):
        """
        Initialize the LiteLLM provider.

        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-haiku-20240307")
                   LiteLLM auto-detects the provider from the model name.
            api_key: API key for the provider. If not provided, LiteLLM will
                     look for the appropriate env var (OPENAI_API_KEY,
                     ANTHROPIC_API_KEY, etc.)
            api_base: Custom API base URL (for proxies or local deployments)
            max_session_tokens: Maximum tokens allowed for the entire session.
                               Default: 500,000. Set to None to disable.
            max_call_tokens: Maximum tokens allowed per API call.
                            Default: 8,192. Set to None to disable.
            enable_circuit_breaker: Enable circuit breaker for failure protection.
                                   Default: True.
            temperature: Optional temperature override.
            **kwargs: Additional arguments passed to litellm.completion()
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.extra_kwargs = kwargs
        
        if temperature is not None:
            self.extra_kwargs["temperature"] = temperature
        
        # Token budget tracking
        self.max_session_tokens = max_session_tokens if max_session_tokens is not None else self.DEFAULT_MAX_SESSION_TOKENS
        self.max_call_tokens = max_call_tokens if max_call_tokens is not None else self.DEFAULT_MAX_CALL_TOKENS
        self.session_tokens = 0
        self.session_calls = 0
        
        # Cost tracking (approximate, based on common pricing)
        self.estimated_cost = 0.0
        
        # Circuit breaker state
        self.enable_circuit_breaker = enable_circuit_breaker
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    def _check_budget(self, estimated_tokens: int = 0) -> None:
        """Check if we're within token budget before making a call."""
        if self.max_session_tokens is not None:
            projected_total = self.session_tokens + estimated_tokens
            if projected_total > self.max_session_tokens:
                raise TokenBudgetExceeded(
                    f"Session token limit exceeded. Used: {self.session_tokens}, "
                    f"Budget: {self.max_session_tokens}, Requested: {estimated_tokens}",
                    tokens_used=self.session_tokens,
                    budget=self.max_session_tokens,
                )

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker is open."""
        if not self.enable_circuit_breaker:
            return
            
        if self._circuit_open_until > time.time():
            cooldown_remaining = self._circuit_open_until - time.time()
            raise CircuitBreakerOpen(
                f"Circuit breaker is open due to {self._consecutive_failures} consecutive failures. "
                f"Retry in {cooldown_remaining:.1f} seconds.",
                failure_count=self._consecutive_failures,
                cooldown_remaining=cooldown_remaining,
            )

    def _record_success(self, input_tokens: int, output_tokens: int) -> None:
        """Record a successful API call."""
        total_tokens = input_tokens + output_tokens
        self.session_tokens += total_tokens
        self.session_calls += 1
        
        # Reset circuit breaker on success
        self._consecutive_failures = 0
        
        # Estimate cost (rough approximation, varies by model)
        # Using GPT-4o-mini pricing as baseline: $0.15/1M input, $0.60/1M output
        self.estimated_cost += (input_tokens * 0.00000015) + (output_tokens * 0.0000006)
        
        logger.debug(
            f"LLM call successful. Tokens: {total_tokens}, "
            f"Session total: {self.session_tokens}, "
            f"Estimated cost: ${self.estimated_cost:.4f}"
        )

    def _record_failure(self, error: Exception) -> None:
        """Record a failed API call."""
        self._consecutive_failures += 1
        
        if self.enable_circuit_breaker and self._consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = time.time() + self.CIRCUIT_BREAKER_COOLDOWN
            logger.warning(
                f"Circuit breaker opened after {self._consecutive_failures} failures. "
                f"Cooldown: {self.CIRCUIT_BREAKER_COOLDOWN}s. Error: {error}"
            )

    def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return {
            "session_tokens": self.session_tokens,
            "session_calls": self.session_calls,
            "max_session_tokens": self.max_session_tokens,
            "tokens_remaining": (self.max_session_tokens - self.session_tokens) if self.max_session_tokens else None,
            "estimated_cost_usd": self.estimated_cost,
            "circuit_breaker_failures": self._consecutive_failures,
            "circuit_breaker_open": self._circuit_open_until > time.time(),
        }

    def reset_session(self) -> None:
        """Reset session counters (e.g., for a new user session)."""
        self.session_tokens = 0
        self.session_calls = 0
        self.estimated_cost = 0.0
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion using LiteLLM with budget and circuit breaker protection."""
        # Security checks
        self._check_circuit_breaker()
        self._check_budget(estimated_tokens=max_tokens)
        
        # Enforce per-call token limit
        if self.max_call_tokens is not None:
            max_tokens = min(max_tokens, self.max_call_tokens)
        
        # Prepare messages with system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        # Add JSON mode via prompt engineering (works across all providers)
        if json_mode:
            json_instruction = (
                "\n\nPlease respond with a valid JSON object."
            )
            # Append to system message if present, otherwise add as system message
            if full_messages and full_messages[0]["role"] == "system":
                full_messages[0]["content"] += json_instruction
            else:
                full_messages.insert(0, {"role": "system", "content": json_instruction.strip()})

        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            **self.extra_kwargs,
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        # Add tools if provided
        if tools:
            kwargs["tools"] = [self._tool_to_openai_format(t) for t in tools]

        # Add response_format for structured output
        # LiteLLM passes this through to the underlying provider
        if response_format:
            kwargs["response_format"] = response_format

        # Make the call with error tracking
        try:
            response = litellm.completion(**kwargs)
        except Exception as e:
            self._record_failure(e)
            raise

        # Extract content
        content = response.choices[0].message.content or ""

        # Get usage info
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # Record success and update counters
        self._record_success(input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            model=response.model or self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=response.choices[0].finish_reason or "",
            raw_response=response,
        )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: callable,
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Run a tool-use loop until the LLM produces a final response.
        
        Security: Includes iteration limits, token tracking per iteration,
        and circuit breaker protection.
        """
        # Security checks
        self._check_circuit_breaker()
        self._check_budget()
        
        # Prepare messages with system prompt
        current_messages = []
        if system:
            current_messages.append({"role": "system", "content": system})
        current_messages.extend(messages)

        total_input_tokens = 0
        total_output_tokens = 0
        iteration_failures = 0
        max_iteration_failures = 2  # Fail fast if iterations keep failing

        # Convert tools to OpenAI format
        openai_tools = [self._tool_to_openai_format(t) for t in tools]

        for iteration in range(max_iterations):
            # Check budget before each iteration
            self._check_budget()
            
            # Build kwargs
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": current_messages,
                "max_tokens": min(1024, self.max_call_tokens) if self.max_call_tokens else 1024,
                "tools": openai_tools,
                **self.extra_kwargs,
            }

            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["api_base"] = self.api_base

            try:
                response = litellm.completion(**kwargs)
                iteration_failures = 0  # Reset on success
            except Exception as e:
                self._record_failure(e)
                iteration_failures += 1
                if iteration_failures >= max_iteration_failures:
                    raise RuntimeError(
                        f"Tool loop failed after {iteration_failures} consecutive errors: {e}"
                    ) from e
                continue

            # Track tokens
            usage = response.usage
            if usage:
                iter_input = usage.prompt_tokens
                iter_output = usage.completion_tokens
                total_input_tokens += iter_input
                total_output_tokens += iter_output
                self._record_success(iter_input, iter_output)

            choice = response.choices[0]
            message = choice.message

            # Check if we're done (no tool calls)
            if choice.finish_reason == "stop" or not message.tool_calls:
                return LLMResponse(
                    content=message.content or "",
                    model=response.model or self.model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    stop_reason=choice.finish_reason or "stop",
                    raw_response=response,
                )

            # Process tool calls.
            # Add assistant message with tool calls.
            current_messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Execute tools and add results.
            for tool_call in message.tool_calls:
                # Parse arguments
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                tool_use = ToolUse(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    input=args,
                )

                result = tool_executor(tool_use)

                # Add tool result message
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_use_id,
                    "content": result.content,
                })

        # Max iterations reached
        logger.warning(
            f"Tool loop reached max iterations ({max_iterations}). "
            f"Total tokens used: {total_input_tokens + total_output_tokens}"
        )
        return LLMResponse(
            content="Max tool iterations reached",
            model=self.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            stop_reason="max_iterations",
            raw_response=None,
        )

    def _tool_to_openai_format(self, tool: Tool) -> dict[str, Any]:
        """Convert Tool to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters.get("properties", {}),
                    "required": tool.parameters.get("required", []),
                },
            },
        }

