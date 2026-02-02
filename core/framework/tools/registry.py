from typing import Dict, List, Any, Optional
from .base import Tool

class ToolRegistry:
    """
    A central repository for managing available tools.
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Adds a tool to the registry."""
        if tool.name in self._tools:
            print(f"⚠️ Warning: Overwriting existing tool '{tool.name}'")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """Returns a list of all registered tool objects."""
        return list(self._tools.values())

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Exports all registered tools in the OpenAI API format.
        Used when sending the tool definitions to the LLM.
        """
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool by name with the given arguments.
        """
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry.")
        
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"