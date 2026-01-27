"""
LLM provider abstraction with optional dependencies.

This module provides a unified interface for different LLM providers.
Providers are loaded dynamically to avoid hard dependencies.
"""

__all__ = ["LLMProvider", "LLMResponse", "get_available_providers"]

from typing import Dict, Type, List

# Core provider interface
from framework.llm.provider import LLMProvider, LLMResponse

# Provider implementations (imported on demand)
_available_providers: Dict[str, Type[LLMProvider]] = {}

# Try to import providers (but don't fail if they're not available)
try:
    from framework.llm.anthropic import AnthropicProvider
    _available_providers["anthropic"] = AnthropicProvider
    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from framework.llm.litellm import LiteLLMProvider
    _available_providers["litellm"] = LiteLLMProvider
    __all__.append("LiteLLMProvider")
except ImportError:
    pass

def get_available_providers() -> Dict[str, Type[LLMProvider]]:
    """
    Get a dictionary of available LLM providers.
    
    Returns:
        Dict[str, Type[LLMProvider]]: Mapping of provider names to their classes
    """
    return _available_providers.copy()
