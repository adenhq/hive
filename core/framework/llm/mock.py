"""Mock LLM Provider for testing and structural validation without real LLM calls."""

import json
import re
from collections.abc import Callable
from typing import Any

from framework.llm.provider import LLMProvider, LLMResponse, Tool, ToolResult, ToolUse


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing agents without making real API calls.

    This provider generates placeholder responses based on the expected output structure,
    allowing structural validation and graph execution testing without incurring costs
    or requiring API keys.

    Example:
        llm = MockLLMProvider()
        response = llm.complete(
            messages=[{"role": "user", "content": "test"}],
            system="Generate JSON with keys: name, age",
            json_mode=True
        )
        # Returns: {"name": "mock_value", "age": "mock_value"}
    """

    def __init__(self, model: str = "mock-model"):
        """
        Initialize the mock LLM provider.

        Args:
            model: Model name to report in responses (default: "mock-model")
        """
        self.model = model

    def _extract_output_keys(self, system: str) -> list[str]:
        """
        Extract expected output keys from the system prompt with improved patterns.
        """
        keys = []

        # Pattern 1: output_keys: [key1, key2]
        match = re.search(r"output_keys:\s*\[(.*?)\]", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            keys = [k.strip().strip("\"'") for k in keys_str.split(",")]
            return keys

        # Pattern 2: Return ... in `key_name`
        match = re.search(r"Return .* in `([a-zA-Z0-9_]+)`", system, re.IGNORECASE)
        if match:
            return [match.group(1)]

        # Pattern 3: "keys: key1, key2" or "Generate JSON with keys: key1, key2"
        match = re.search(r"(?:keys|with keys):\s*([a-zA-Z0-9_,\s]+)", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            return keys

        # Pattern 4: Look for JSON schema in system prompt
        match = re.search(r'\{[^}]*"([a-zA-Z0-9_]+)":\s*', system)
        if match:
            all_matches = re.findall(r'"([a-zA-Z0-9_]+)":\s*', system)
            if all_matches:
                return list(set(all_matches))

        return keys

    def _generate_mock_response(
        self,
        system: str = "",
        json_mode: bool = False,
        tool_results: list[ToolResult] | None = None,
    ) -> str:
        """
        Generate a mock response based on the system prompt and mode.
        """
        if json_mode:
            keys = self._extract_output_keys(system)
            
            # Incorporate tool results into the mock data if available
            result_context = ""
            if tool_results:
                result_context = " ".join([str(r.content) for r in tool_results])

            if keys:
                mock_data = {}
                for key in keys:
                    # Try to find a sensible value from tool results
                    found_value = None
                    if tool_results:
                        for res in tool_results:
                            try:
                                content_json = json.loads(res.content)
                                if isinstance(content_json, dict) and key in content_json:
                                    found_value = content_json[key]
                                    break
                                elif isinstance(content_json, dict) and len(content_json) == 1:
                                    # If tool returns a single value dict, use it
                                    found_value = list(content_json.values())[0]
                                    break
                            except:
                                # Not JSON, use raw content if key seems relevant
                                key_lower = key.lower()
                                relevant_terms = ["result", "data", "content", "message", "report", "code", "src", "output", "text"]
                                if any(term in key_lower for term in relevant_terms):
                                    found_value = res.content
                                    break
                    
                    if found_value is not None:
                        mock_data[key] = found_value
                    else:
                        mock_data[key] = f"mock_{key}_value"
                return json.dumps(mock_data, indent=2)
            else:
                return json.dumps({"result": f"mock_result_value incorporated: {result_context[:50]}"}, indent=2)
        else:
            if tool_results:
                return f"Mock response based on tool results: {str(tool_results[0].content)[:200]}"
            return "This is a mock response for testing purposes."

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """Generate a mock completion."""
        content = self._generate_mock_response(system=system, json_mode=json_mode)

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            stop_reason="mock_complete",
        )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[[ToolUse], ToolResult],
        max_iterations: int = 10,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """
        Simulate tool use in mock mode.
        """
        tool_results = []
        
        # Simulate one tool call if tools are available
        if tools:
            tool = tools[0]
            # Create mock inputs based on the tool's parameter schema
            mock_inputs = {}
            if "properties" in tool.parameters:
                for prop_name, prop_info in tool.parameters["properties"].items():
                    prop_type = prop_info.get("type")
                    if prop_type == "string":
                        mock_inputs[prop_name] = f"mock_{prop_name}"
                    elif prop_type == "integer" or prop_type == "number":
                        mock_inputs[prop_name] = 1
                    elif prop_type == "boolean":
                        mock_inputs[prop_name] = True
                    else:
                        mock_inputs[prop_name] = "mock_value"
            
            tool_use = ToolUse(
                name=tool.name,
                input=mock_inputs,
                id=f"mock_tool_use_{tool.name}"
            )
            
            try:
                result = tool_executor(tool_use)
                tool_results.append(result)
            except Exception as e:
                logger.error(f"Error in mock tool execution: {e}")

        # Try to generate JSON if the system prompt suggests structured output
        json_mode = "json" in system.lower() or "keys" in system.lower() or "Return" in system or "output_keys" in system

        content = self._generate_mock_response(
            system=system, 
            json_mode=json_mode,
            tool_results=tool_results
        )

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            stop_reason="mock_complete",
        )
