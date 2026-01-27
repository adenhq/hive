"""LLM provider abstraction with lazy loading for heavy dependencies.

Providers are loaded lazily to avoid 1.5s+ import overhead from LiteLLM.
Use get_provider() functions or import directly when needed.
"""

from framework.llm.provider import LLMProvider, LLMResponse

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "AnthropicProvider",
    "LiteLLMProvider",
    "MockLLMProvider",
]

# Lazy loading - providers imported on first access
_providers_cache = {}


def __getattr__(name: str):
    """Lazy load providers on first access."""
    if name == "AnthropicProvider":
        if "AnthropicProvider" not in _providers_cache:
            try:
                from framework.llm.anthropic import AnthropicProvider
                _providers_cache["AnthropicProvider"] = AnthropicProvider
            except ImportError:
                raise ImportError("AnthropicProvider not available")
        return _providers_cache["AnthropicProvider"]

    elif name == "LiteLLMProvider":
        if "LiteLLMProvider" not in _providers_cache:
            try:
                from framework.llm.litellm import LiteLLMProvider
                _providers_cache["LiteLLMProvider"] = LiteLLMProvider
            except ImportError:
                raise ImportError("LiteLLMProvider not available - install litellm")
        return _providers_cache["LiteLLMProvider"]

    elif name == "MockLLMProvider":
        if "MockLLMProvider" not in _providers_cache:
            try:
                from framework.llm.mock import MockLLMProvider
                _providers_cache["MockLLMProvider"] = MockLLMProvider
            except ImportError:
                raise ImportError("MockLLMProvider not available")
        return _providers_cache["MockLLMProvider"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
