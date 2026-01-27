"""LLM Provider abstraction for pluggable LLM backends."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Type, TypeVar, Generic, ClassVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T', bound='LLMProvider')

class LLMResponse(BaseModel):
    """Response from an LLM call."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_response: Any = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Tool(BaseModel):
    """A tool the LLM can use."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


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


class LLMProvider(BaseModel, ABC):
    """
    Abstract base class for LLM providers.
    
    This class is a Pydantic model to support JSON schema generation.
    Subclasses should implement the abstract methods and can add provider-specific fields.
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "description": "Base class for LLM providers"
        }
    )
    
    # Provider metadata
    provider_name: ClassVar[str] = "base"
    supports_tools: ClassVar[bool] = False
    
    # Instance configuration
    model: str = Field(..., description="The model to use for this provider")
    
    def __init__(self, **data):
        # Ensure model is set from class default if not provided
        if 'model' not in data and hasattr(self, 'model'):
            data['model'] = self.model
        super().__init__(**data)
    """
    Abstract LLM provider - plug in any LLM backend.

    Implementations should handle:
    - API authentication
    - Request/response formatting
    - Token counting
    - Error handling
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        tools: Optional[List[Tool]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text from a prompt.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            tools: List of tools the model can use
            **kwargs: Provider-specific arguments

        Returns:
            LLMResponse containing the generated text and metadata
        """
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Tool],
        system_prompt: str = "",
        **kwargs: Any,
    ) -> tuple[LLMResponse, Optional[List[ToolUse]]]:
        """Generate text with tool use capabilities.

        Args:
            prompt: User prompt/message
            tools: List of tools the model can use
            system_prompt: Optional system prompt
            **kwargs: Provider-specific arguments

        Returns:
            Tuple of (LLMResponse, list of ToolUse if any tools were used)
        """
        pass

    @classmethod
    def create(cls: Type[T], *args, **kwargs) -> T:
        """Create a new instance of the provider.
        
        This is a convenience method that allows creating providers with a consistent interface.
        """
        return cls(*args, **kwargs)

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: callable,
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
