"""LLM provider abstraction."""

from framework.llm.provider import LLMProvider, LLMResponse
from framework.llm.stream_events import (
    FinishEvent,
    ReasoningDeltaEvent,
    ReasoningStartEvent,
    StreamErrorEvent,
    StreamEvent,
    TextDeltaEvent,
    TextEndEvent,
    ToolCallEvent,
    ToolResultEvent,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "StreamEvent",
    "TextDeltaEvent",
    "TextEndEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ReasoningStartEvent",
    "ReasoningDeltaEvent",
    "FinishEvent",
    "StreamErrorEvent",
]

try:
    if os.environ.get("ANTHROPIC_API_KEY"):
        from framework.llm.anthropic import AnthropicProvider  # noqa: F401

        __all__.append("AnthropicProvider")
    elif os.environ.get("OPENAI_API_KEY"):
        from framework.llm.openai import OpenAIProvider  # noqa: F401

        __all__.append("OpenAIProvider")
except ImportError:
    pass

try:
    from framework.llm.litellm import LiteLLMProvider  # noqa: F401

    __all__.append("LiteLLMProvider")
except ImportError:
    pass

try:
    from framework.llm.mock import MockLLMProvider  # noqa: F401

    __all__.append("MockLLMProvider")
except ImportError:
    pass
