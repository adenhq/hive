"""LiteLLM provider for pluggable multi-provider LLM support.

LiteLLM provides a unified, OpenAI-compatible interface that supports
multiple LLM providers including OpenAI, Anthropic, Gemini, Mistral,
Groq, and local models.

See: https://docs.litellm.ai/docs/providers
"""

import json
import os
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

import litellm
from pydantic import ConfigDict, Field

from framework.llm.provider import (
    LLMProvider, 
    LLMResponse, 
    Tool, 
    ToolUse,
    ToolResult
)


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

    Usage:
        # OpenAI
        provider = LiteLLMProvider(model="gpt-4o-mini")

        # Anthropic
        provider = LiteLLMProvider(model="claude-3-haiku-20240307")

        # Google Gemini
        provider = LiteLLMProvider(model="gemini/gemini-1.5-flash")

        # Local Ollama
        provider = LiteLLMProvider(model="ollama/llama3")

        # With custom API base
        provider = LiteLLMProvider(
            model="gpt-4o-mini",
            api_base="https://my-proxy.com/v1"
        )
    """
    # Provider metadata
    provider_name: ClassVar[str] = "litellm"
    supports_tools: ClassVar[bool] = True
    
    # Configuration
    model_config = ConfigDict(extra='allow')  # Allow extra fields in the model
    
    # Instance configuration
    model: str = Field(default="gpt-3.5-turbo", description="The model to use for completions")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)")
    max_tokens: int = Field(default=1024, ge=1, description="Maximum number of tokens to generate")
    
    # API configuration
    api_key: Optional[str] = Field(default=None, description="API key for the provider")
    api_base: Optional[str] = Field(default=None, description="Base URL for the API")
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        """
        Initialize the LiteLLM provider.

        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-haiku-20240307").
                  If not provided, will use LITELLM_MODEL environment variable or default to "gpt-3.5-turbo".
            api_key: API key for the provider. If not provided, LiteLLM will
                     look for the appropriate env var (OPENAI_API_KEY,
                     ANTHROPIC_API_KEY, etc.)
            api_base: Custom API base URL (for proxies or local deployments)
            temperature: Sampling temperature to use (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments passed to litellm.completion()
        """
        # Get model from environment if not provided
        if model is None:
            model = os.environ.get("LITELLM_MODEL", "gpt-3.5-turbo")

        # Initialize the base class with model config
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Set instance attributes
        self.api_key = api_key
        self.api_base = api_base
        self.extra_kwargs = kwargs
        
        # Configure LiteLLM
        if self.api_base:
            litellm.api_base = self.api_base
        if self.api_key:
            litellm.api_key = self.api_key
            
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        tools: Optional[List[Tool]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            prompt: The user's input prompt
            system_prompt: Optional system prompt to guide the model's behavior
            tools: Optional list of tools the model can use
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            LLMResponse containing the generated text and metadata
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Convert tools to LiteLLM format if provided
        litellm_tools = None
        if tools:
            litellm_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            } for tool in tools]
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                tools=litellm_tools,
                **self._get_completion_kwargs(**kwargs)
            )
            
            choice = response.choices[0]
            message = choice.message
            
            return LLMResponse(
                content=message.content or "",
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                stop_reason=choice.finish_reason,
                raw_response=response
            )
            
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise RuntimeError("Rate limit exceeded. Please try again later.") from e
            raise
            
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Tool],
        system_prompt: str = "",
        **kwargs: Any,
    ) -> Tuple[LLMResponse, Optional[List[ToolUse]]]:
        """Generate a response with tool usage capabilities.
        
        Args:
            prompt: The user's input prompt
            tools: List of tools the model can use
            system_prompt: Optional system prompt
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Tuple of (LLMResponse, list of ToolUse if any tools were used)
        """
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools,
            **kwargs
        )
        
        # Check for tool calls in the response
        tool_uses = None
        if hasattr(response.raw_response.choices[0].message, 'tool_calls'):
            tool_calls = response.raw_response.choices[0].message.tool_calls or []
            tool_uses = [
                ToolUse(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    input=json.loads(tool_call.function.arguments)
                )
                for tool_call in tool_calls
            ]
            
        return response, tool_uses

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

        # Make the call
        response = litellm.completion(**kwargs)

        # Extract content
        content = response.choices[0].message.content or ""

        # Get usage info
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            content=content,
            model=response.model or self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=response.choices[0].finish_reason or "",
            raw_response=response,
        )

    async def complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: List[Tool],
        tool_executor: callable,
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Run a tool-use loop until the LLM produces a final response."""
        # Prepare messages with system prompt
        current_messages = []
        if system:
            current_messages.append({"role": "system", "content": system})
        current_messages.extend(messages)

        total_input_tokens = 0
        total_output_tokens = 0

        # Convert tools to OpenAI format
        openai_tools = [self._tool_to_openai_format(t) for t in tools]

        for _ in range(max_iterations):
            try:
                # Build kwargs
                kwargs: Dict[str, Any] = {
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

                response = await litellm.acompletion(**kwargs)

                # Track tokens
                usage = response.usage
                if usage:
                    total_input_tokens += usage.prompt_tokens
                    total_output_tokens += usage.completion_tokens

                choice = response.choices[0]
                message = choice.message

                return LLMResponse(
                    content=message.content or "",
                    model=response.model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    stop_reason=choice.finish_reason or "stop",
                    raw_response=response,
                )

            except Exception as e:
                # Handle rate limits and retries
                if "rate limit" in str(e).lower():
                    raise RuntimeError("Rate limit exceeded. Please try again later.") from e
                raise

    def _get_completion_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        """Get the default completion arguments.

        Args:
            **kwargs: Additional arguments to override defaults

        Returns:
            Dictionary of completion arguments
        """
        defaults = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        defaults.update(kwargs)
        return defaults
