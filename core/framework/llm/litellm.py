"""LiteLLM provider for pluggable multi-provider LLM support.

LiteLLM provides a unified, OpenAI-compatible interface that supports
multiple LLM providers including OpenAI, Anthropic, Gemini, Mistral,
Groq, and local models.

Observability:
    This provider integrates with OpenTelemetry for distributed tracing.
    All LLM calls create spans with token counts, latency, and model info.
    Enable via HIVE_TRACING_ENABLED=true environment variable.

See: https://docs.litellm.ai/docs/providers
"""

import json
from collections.abc import Callable
from typing import Any

try:
    import litellm
except ImportError:
    litellm = None

from framework.llm.provider import LLMProvider, LLMResponse, Tool, ToolResult, ToolUse
from framework.observability import get_tracer


class LiteLLMProvider(LLMProvider):
    """
    LiteLLM-based LLM provider for multi-provider support.

    Supports any model that LiteLLM supports, including:
    - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    - Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
    - Google: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
    - DeepSeek: deepseek-chat, deepseek-coder, deepseek-reasoner
    - Mistral: mistral-large, mistral-medium, mistral-small
    - Groq: llama3-70b, mixtral-8x7b
    - Local: ollama/llama3, ollama/mistral
    - And many more...

    Usage:
        # OpenAI
        provider = LiteLLMProvider(model="gpt-4o-mini")

        # Anthropic
        provider = LiteLLMProvider(model="claude-3-haiku-20240307")

        # Google Gemini
        provider = LiteLLMProvider(model="gemini/gemini-1.5-flash")

        # DeepSeek
        provider = LiteLLMProvider(model="deepseek/deepseek-chat")

        # Local Ollama
        provider = LiteLLMProvider(model="ollama/llama3")

        # With custom API base
        provider = LiteLLMProvider(
            model="gpt-4o-mini",
            api_base="https://my-proxy.com/v1"
        )
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
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
            **kwargs: Additional arguments passed to litellm.completion()
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.extra_kwargs = kwargs

        if litellm is None:
            raise ImportError(
                "LiteLLM is not installed. Please install it with: pip install litellm"
            )

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion using LiteLLM."""
        tracer = get_tracer()

        # Prepare messages with system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        # Add JSON mode via prompt engineering (works across all providers)
        if json_mode:
            json_instruction = "\n\nPlease respond with a valid JSON object."
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

        # Make the call with tracing
        with tracer.trace_llm_call(
            model=self.model,
            operation="complete",
            system_prompt_length=len(system) if system else None,
            message_count=len(messages),
            tools_count=len(tools) if tools else None,
        ) as llm_span:
            response = litellm.completion(**kwargs)

            # Extract content
            content = response.choices[0].message.content or ""

            # Get usage info
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            # Record LLM metrics on span
            tracer.record_llm_result(
                span=llm_span,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=response.model,
                stop_reason=response.choices[0].finish_reason,
            )

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
        tool_executor: Callable[[ToolUse], ToolResult],
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Run a tool-use loop until the LLM produces a final response."""
        tracer = get_tracer()

        # Prepare messages with system prompt
        current_messages = []
        if system:
            current_messages.append({"role": "system", "content": system})
        current_messages.extend(messages)

        total_input_tokens = 0
        total_output_tokens = 0
        tool_calls_count = 0

        # Convert tools to OpenAI format
        openai_tools = [self._tool_to_openai_format(t) for t in tools]

        # Create parent span for the entire tool-use loop
        with tracer.trace_llm_call(
            model=self.model,
            operation="complete_with_tools",
            system_prompt_length=len(system) if system else None,
            message_count=len(messages),
            tools_count=len(tools),
        ) as loop_span:
            for iteration in range(max_iterations):
                # Build kwargs
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": current_messages,
                    "max_tokens": 1024,
                    "tools": openai_tools,
                    **self.extra_kwargs,
                }

                if self.api_key:
                    kwargs["api_key"] = self.api_key
                if self.api_base:
                    kwargs["api_base"] = self.api_base

                response = litellm.completion(**kwargs)

                # Track tokens
                usage = response.usage
                if usage:
                    total_input_tokens += usage.prompt_tokens
                    total_output_tokens += usage.completion_tokens

                choice = response.choices[0]
                message = choice.message

                # Check if we're done (no tool calls)
                if choice.finish_reason == "stop" or not message.tool_calls:
                    # Record final metrics
                    tracer.record_llm_result(
                        span=loop_span,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        model=response.model,
                        stop_reason=choice.finish_reason,
                    )
                    if loop_span is not None:
                        loop_span.set_attribute("hive.llm.iterations", iteration + 1)
                        loop_span.set_attribute("hive.llm.tool_calls", tool_calls_count)

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
                current_messages.append(
                    {
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
                    }
                )

                # Execute tools and add results.
                for tool_call in message.tool_calls:
                    tool_calls_count += 1

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

                    # Trace individual tool calls
                    with tracer.trace_tool_call(
                        tool_name=tool_call.function.name,
                        tool_input=args,
                    ) as tool_span:
                        result = tool_executor(tool_use)

                        # Record tool result
                        if tool_span is not None:
                            tool_span.set_attribute("hive.tool.success", not result.is_error)
                            if result.is_error:
                                tool_span.set_attribute("hive.tool.error", result.content[:500])

                    # Add tool result message
                    current_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": result.tool_use_id,
                            "content": result.content,
                        }
                    )

            # Max iterations reached
            tracer.record_llm_result(
                span=loop_span,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                model=self.model,
                stop_reason="max_iterations",
            )
            if loop_span is not None:
                loop_span.set_attribute("hive.llm.iterations", max_iterations)
                loop_span.set_attribute("hive.llm.tool_calls", tool_calls_count)
                loop_span.set_attribute("hive.llm.max_iterations_reached", True)

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
