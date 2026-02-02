from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field

class Tool(BaseModel):
    """
    Represents a tool that an Agent can use.
    
    Attributes:
        name: The name of the tool (e.g., "calculator").
        description: A natural language description of what the tool does.
        func: The actual Python function to execute.
        schema: (Optional) JSON schema describing the arguments.
    """
    name: str
    description: str
    func: Callable[..., Any]
    parameters_schema: Optional[Dict[str, Any]] = Field(default=None)

    def execute(self, **kwargs) -> Any:
        """Runs the underlying function with the provided arguments."""
        return self.func(**kwargs)

    def to_schema(self) -> Dict[str, Any]:
        """
        Returns the OpenAI-compatible function schema.
        This tells the LLM how to call this tool.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema or {"type": "object", "properties": {}}
            }
        }

    class Config:
        arbitrary_types_allowed = True