"""Mock LLM Provider for testing and structural validation without real LLM calls."""

import json
import re
from collections.abc import AsyncIterator, Callable
from typing import Any

from framework.llm.provider import LLMProvider, LLMResponse, Tool, ToolResult, ToolUse
from framework.llm.stream_events import (
    FinishEvent,
    StreamEvent,
    TextDeltaEvent,
    TextEndEvent,
)


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing agents without making real API calls.
    """

    def __init__(self, model: str = "mock-model"):
        self.model = model

    def _extract_output_keys(self, system: str) -> list[str]:
        """Extract output keys from system prompt."""
        # Preference 1: Explicitly defined output_keys: [...]
        match = re.search(r"output_keys:\s*\[(.*?)\]", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            return [k.strip().strip("\"'") for k in keys_str.split(",")]

        # Preference 2: set_output("key", ...)
        all_matches = re.findall(r'set_output\("([a-zA-Z0-9_]+)"', system)
        if all_matches:
            return list(dict.fromkeys(all_matches))

        # Preference 3: "Valid keys: [...]"
        match = re.search(r"Valid keys: \[(.*?)\]", system)
        if match:
            keys_str = match.group(1)
            return [k.strip().strip("'\"") for k in keys_str.split(",")]

        # Preference 4: "keys: key1, key2"
        match = re.search(r"(?:keys|with keys):\s*([a-zA-Z0-9_,\s]+)", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            return [k.strip() for k in keys_str.split(",") if k.strip()]

        return []

    def _generate_mock_response(self, system: str = "", json_mode: bool = False) -> str:
        if json_mode:
            keys = self._extract_output_keys(system)
            if keys:
                return json.dumps({key: f"mock_{key}_value" for key in keys}, indent=2)
            return json.dumps({"result": "mock_result_value"}, indent=2)
        return "This is a mock response for testing purposes."

    async def _generate_mock_completion(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        json_mode: bool = False,
    ) -> tuple[str, list[dict] | None]:
        import random
        
        turn_count = len(messages)
        output_keys = self._extract_output_keys(system)
        
        # Determine state from history
        has_asked = any(m.get("tool_calls") and any(tc["function"]["name"] == "ask_user" for tc in m["tool_calls"]) for m in messages)
        has_set_success = any(m.get("role") == "tool" and "successfully" in str(m.get("content")).lower() for m in messages)
        has_tool_results = any(m.get("role") == "tool" and "error" not in str(m.get("content")).lower() for m in messages)
        
        available_tools = {t.name: t for t in tools} if tools else {}

        # 1. Ask User if needed
        if "ask_user" in available_tools and not has_asked and turn_count < 5:
            return (
                f"Hello! I am ready to begin. What competitor should I analyze? (Turn {turn_count})",
                [{
                    "id": f"mock_call_ask_user_{turn_count}",
                    "type": "function",
                    "function": {"name": "ask_user", "arguments": json.dumps({"question": "What competitor should I analyze?"})}
                }]
            )

        # 2. Set Output if we have data or enough turns
        if "set_output" in available_tools and output_keys and not has_set_success and (has_tool_results or turn_count >= 2):
            target_key = output_keys[0]
            if "competitor_info" in output_keys:
                target_key = "competitor_info"
                value = {"target": "Apple", "raw_input": "Analyze Apple"}
            elif "analysis_report" in output_keys:
                target_key = "analysis_report"
                value = {"meta": {"target_name": "Apple"}, "positioning": {"core_promise": "Premium"}}
            else:
                value = f"mock_{target_key}_value"

            return (
                f"I have gathered the intelligence. Setting output '{target_key}' now.",
                [{
                    "id": f"mock_call_set_output_{turn_count}",
                    "type": "function",
                    "function": {"name": "set_output", "arguments": json.dumps({"key": target_key, "value": value})}
                }]
            )

        # 3. Fallback to text/JSON Response
        is_json = json_mode or bool(output_keys)
        content = self._generate_mock_response(system=system, json_mode=is_json)
        
        if is_json:
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    data["_mock_rand"] = random.random()
                    content = json.dumps(data)
            except Exception: pass
        else:
            content += f"\n\nProgress marker: {turn_count}-{random.random()}"
            
        return content, None

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
        is_json = json_mode or bool(self._extract_output_keys(system))
        content = self._generate_mock_response(system=system, json_mode=is_json)
        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=100,
            output_tokens=100,
            stop_reason="mock_complete",
        )

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[[ToolUse], ToolResult],
        max_iterations: int = 10,
    ) -> LLMResponse:
        """Run tool loop - mock implementation just calls complete."""
        return self.complete(messages, system=system, tools=tools)

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
        """Async mock completion (no I/O, returns immediately)."""
        return self.complete(
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
        """Async mock tool-use completion (no I/O, returns immediately)."""
        return self.complete_with_tools(
            messages=messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        content, tool_calls = await self._generate_mock_completion(
            messages, system=system, tools=tools, json_mode=False
        )
        
        if tool_calls:
            for tc in tool_calls:
                from framework.llm.stream_events import ToolCallEvent
                yield ToolCallEvent(
                    tool_use_id=tc["id"],
                    tool_name=tc["function"]["name"],
                    tool_input=json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                )
            yield FinishEvent(stop_reason="tool_use", model=self.model)
            return

        words = content.split(" ")
        accumulated = ""
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            accumulated += chunk
            yield TextDeltaEvent(content=chunk, snapshot=accumulated)

        yield TextEndEvent(full_text=accumulated)
        yield FinishEvent(stop_reason="mock_complete", model=self.model)
