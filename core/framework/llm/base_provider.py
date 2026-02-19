"""Base LLM provider wrapper for delegating to LiteLLMProvider.

This module provides common functionality for provider-specific wrappers
(Anthropic, OpenAI, etc.) that delegate to LiteLLMProvider internally.
"""

import os
from typing import Any

from framework.llm.litellm import LiteLLMProvider
from framework.llm.provider import LLMProvider, LLMResponse, Tool, ToolResult, ToolUse
from collections.abc import Callable


def get_api_key_from_credential_store(
    provider_name: str, env_var_name: str
) -> str | None:
    """Get API key from CredentialStoreAdapter or environment.

    Priority:
    1. CredentialStoreAdapter (supports encrypted storage + env vars)
    2. os.environ fallback

    Args:
        provider_name: Name of the provider for CredentialStoreAdapter (e.g., "anthropic", "openai")
        env_var_name: Environment variable name to check (e.g., "ANTHROPIC_API_KEY")

    Returns:
        API key string or None if not found
    """
    try:
        from aden_tools.credentials import CredentialStoreAdapter

        creds = CredentialStoreAdapter.default()
        if creds.is_available(provider_name):
            return creds.get(provider_name)
    except ImportError:
        pass
    return os.environ.get(env_var_name)


class BaseLiteLLMProviderWrapper(LLMProvider):
    """Base class for LLM providers that delegate to LiteLLMProvider.

    This is a backward-compatible wrapper pattern that internally uses LiteLLMProvider.
    Subclasses should implement __init__ to set up api_key and model, then call _init_provider().

    Example:
        class MyProvider(BaseLiteLLMProviderWrapper):
            def __init__(self, api_key=None, model="my-model"):
                self.api_key = api_key or get_api_key_from_credential_store("my_provider", "MY_API_KEY")
                if not self.api_key:
                    raise ValueError("API key required")
                self.model = model
                self._init_provider()
    """

    def _init_provider(self) -> None:
        """Initialize the internal LiteLLMProvider. Call this from subclass __init__."""
        self._provider = LiteLLMProvider(
            model=self.model,
            api_key=self.api_key,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Generate a completion via LiteLLM."""
        return self._provider.complete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[[ToolUse], ToolResult],
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Run a tool-use loop via LiteLLM."""
        return self._provider.complete_with_tools(
            messages=messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Async completion via LiteLLM."""
        return await self._provider.acomplete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )

    async def acomplete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[[ToolUse], ToolResult],
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Async tool-use loop via LiteLLM."""
        return await self._provider.acomplete_with_tools(
            messages=messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )
