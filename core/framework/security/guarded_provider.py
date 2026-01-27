"""
Guarded LLM Provider wrapper.
"""
from typing import Any, List, Optional
from collections.abc import Callable

from typing import Any, List, Optional
from collections.abc import Callable

# from ..llm.provider import LLMProvider, LLMResponse, Tool, ToolUse, ToolResult
from .guardrail import Guardrail, GuardrailAction, GuardrailResult

# Mock types for runtime validation to avoid circular imports during testing
class LLMProvider: pass
class LLMResponse: pass
class Tool: pass
class ToolUse: pass
class ToolResult: pass


class GuardrailException(Exception):
    """Raised when a guardrail blocks execution."""
    def __init__(self, result: GuardrailResult):
        self.result = result
        super().__init__(f"Guardrail blocked execution: {result.reason}")


class GuardedLLMProvider(LLMProvider):
    """
    Wraps an existing LLMProvider with security guardrails.
    
    1. Validates INPUT messages before sending to LLM.
    2. Validates OUTPUT content before returning to Agent.
    """
    
    def __init__(
        self, 
        base_provider: LLMProvider,
        input_guardrails: Optional[List[Guardrail]] = None,
        output_guardrails: Optional[List[Guardrail]] = None
    ):
        self._provider = base_provider
        self._input_guardrails = input_guardrails or []
        self._output_guardrails = output_guardrails or []
        
    def _validate(self, content: str, guardrails: List[Guardrail]) -> None:
        """Run all guardrails against content. Raises GuardrailException if blocked."""
        for guardrail in guardrails:
            result = guardrail.validate(content)
            if result.is_blocked:
                # TODO: Add logging here
                raise GuardrailException(result)
                
    def _extract_text_from_messages(self, messages: List[dict[str, Any]]) -> str:
        """Helper to extract full text from message history for validation."""
        text = ""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                text += content + "\n"
            elif isinstance(content, list):
                # Handle multi-model content blocks if necessary
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        text += block["text"] + "\n"
        return text

    def complete(
        self,
        messages: List[dict[str, Any]],
        system: str = "",
        tools: Optional[List[Tool]] = None,
        max_tokens: int = 1024,
        response_format: Optional[dict[str, Any]] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        
        # 1. Input Validation
        full_input_text = system + "\n" + self._extract_text_from_messages(messages)
        self._validate(full_input_text, self._input_guardrails)
        
        # 2. Call Base Provider
        response = self._provider.complete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode
        )
        
        # 3. Output Validation
        self._validate(response.content, self._output_guardrails)
        
        return response

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[Tool],
        tool_executor: Callable[["ToolUse"], "ToolResult"],
        max_iterations: int = 10,
    ) -> LLMResponse:
        
        # 1. Input Validation
        full_input_text = system + "\n" + self._extract_text_from_messages(messages)
        self._validate(full_input_text, self._input_guardrails)
        
        # 2. Call Base Provider
        # Note: We rely on the base provider to handle the loop. 
        # Ideally, we should validate intermediate steps, but the current interface 
        # encapsulates the loop. We validate the FINAL response.
        
        response = self._provider.complete_with_tools(
            messages=messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            max_iterations=max_iterations
        )
        
        # 3. Output Validation
        self._validate(response.content, self._output_guardrails)
        
        return response
