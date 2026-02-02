"""LLM Provider abstraction for pluggable LLM backends."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict, TYPE_CHECKING
from pydantic import BaseModel

# Prevent circular imports
if TYPE_CHECKING:
    from framework.tools.base import Tool

# --- RESTORED CLASSES ---
class ToolUse(BaseModel):
    """A tool call requested by the LLM."""
    id: str
    name: str
    input: Dict[str, Any]

class ToolResult(BaseModel):
    """Result of executing a tool."""
    tool_use_id: str
    content: str
    is_error: bool = False
# ------------------------

class LLMResponse(BaseModel):
    """
    Standardized response from any LLM call.
    """
    content: str
    model: str
    tool_calls: Optional[List[Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_response: Any = None

class LLMProvider(ABC):
    """
    Abstract LLM provider - plug in any LLM backend.
    """

    @abstractmethod
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
        Generate a completion from the LLM.
        """
        pass

    @abstractmethod
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
        pass