"""LiteLLM provider for pluggable multi-provider LLM support.

LiteLLM provides a unified, OpenAI-compatible interface that supports
multiple LLM providers including OpenAI, Anthropic, Gemini, Mistral,
Groq, and local models.

See: https://docs.litellm.ai/docs/providers
"""

import json
from typing import Any, List, Dict, Optional

try:
    import litellm
except ImportError:
    litellm = None

# --- UPDATE IMPORTS ---
# We import Tool from our new dedicated module
from framework.llm.provider import LLMProvider, LLMResponse
from framework.tools.base import Tool

class LiteLLMProvider(LLMProvider):
    """
    LiteLLM-based LLM provider for multi-provider support.
    Now supports Tool Calling via the framework.tools system.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
        **kwargs: Any,
    ):
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
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion using LiteLLM.
        Supports native Tool Calling.
        """
        # Prepare messages with system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        # Add JSON mode instruction if requested
        if json_mode:
            json_instruction = "\n\nPlease respond with a valid JSON object."
            if full_messages and full_messages[0]["role"] == "system":
                full_messages[0]["content"] += json_instruction
            else:
                full_messages.insert(0, {"role": "system", "content": json_instruction.strip()})

        # Build kwargs
        call_args: dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            **self.extra_kwargs,
            **kwargs 
        }

        if self.api_key:
            call_args["api_key"] = self.api_key
        if self.api_base:
            call_args["api_base"] = self.api_base

        # --- TOOL SUPPORT ---
        # Convert our Tool objects to OpenAI-compatible schemas
        if tools:
            call_args["tools"] = [t.to_schema() for t in tools]
            call_args["tool_choice"] = "auto"

        # LiteLLM passes this through to the underlying provider
        if response_format:
            call_args["response_format"] = response_format

        try:
            # Make the call
            response = litellm.completion(**call_args)

            # Extract content
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""
            
            # Extract Tool Calls (if any)
            tool_calls = message.tool_calls

            # Get usage info
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            return LLMResponse(
                content=content,
                tool_calls=tool_calls, # <--- Pass raw tool calls back to the agent
                model=response.model or self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                # stop_reason=choice.finish_reason or "", # Optional: Add back if needed
            )
            
        except Exception as e:
            # Graceful error handling
            return LLMResponse(
                content=f"Error generating response: {str(e)}",
                model=self.model,
                input_tokens=0,
                output_tokens=0
            )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        **kwargs
    ) -> LLMResponse:
        """
        Wrapper to easily call complete() with a list of Tool objects.
        """
        return self.complete(messages, system=system, tools=tools, **kwargs)