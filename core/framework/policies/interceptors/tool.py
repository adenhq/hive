"""Tool call interceptor for creating policy events.

The ToolInterceptor creates PolicyEvents from tool calls and results,
enabling policies to evaluate tool usage.
"""

from typing import Any, Optional

from framework.policies.decisions import PolicyAction
from framework.policies.engine import AggregatedDecision, PolicyEngine
from framework.policies.events import PolicyEvent, PolicyEventType
from framework.policies.exceptions import ConfirmationRequiredError, PolicyViolationError


class ToolInterceptor:
    """Intercepts tool calls and evaluates them against policies.

    The interceptor creates PolicyEvents from tool calls and submits
    them to the PolicyEngine for evaluation. It provides methods for
    both before and after tool execution.

    Example:
        engine = PolicyEngine()
        engine.register_policy(HighRiskToolGatingPolicy())
        interceptor = ToolInterceptor(engine, execution_id="exec-123")

        # Before calling a tool
        result = await interceptor.before_call("file_delete", {"path": "/tmp/x"})
        if result.requires_confirmation:
            # Request human approval
            approved = await request_human_approval(result.confirmation_decision)
            if not approved:
                return

        # Execute the tool
        tool_result = await execute_tool("file_delete", {"path": "/tmp/x"})

        # After tool execution
        await interceptor.after_call("file_delete", tool_result)
    """

    def __init__(
        self,
        engine: PolicyEngine,
        execution_id: str,
        stream_id: Optional[str] = None,
    ) -> None:
        """Initialize the ToolInterceptor.

        Args:
            engine: The PolicyEngine to use for evaluation
            execution_id: The current execution ID
            stream_id: Optional stream identifier
        """
        self._engine = engine
        self._execution_id = execution_id
        self._stream_id = stream_id
        self._correlation_counter = 0

    def _next_correlation_id(self) -> str:
        """Generate the next correlation ID for tracking call pairs."""
        self._correlation_counter += 1
        return f"{self._execution_id}:tool:{self._correlation_counter}"

    async def before_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AggregatedDecision:
        """Evaluate a tool call before execution.

        Creates a TOOL_CALL event and submits it to the policy engine.

        Args:
            tool_name: Name of the tool being called
            args: Arguments being passed to the tool
            metadata: Optional additional context

        Returns:
            AggregatedDecision from policy evaluation

        Raises:
            PolicyViolationError: If engine.raise_on_block and BLOCK
            ConfirmationRequiredError: If engine.raise_on_confirm and REQUIRE_CONFIRM
        """
        correlation_id = self._next_correlation_id()

        event = PolicyEvent.create(
            event_type=PolicyEventType.TOOL_CALL,
            payload={
                "tool_name": tool_name,
                "args": args,
                "metadata": metadata or {},
            },
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            correlation_id=correlation_id,
        )

        return await self._engine.evaluate(event)

    async def after_call(
        self,
        tool_name: str,
        result: Any,
        *,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> AggregatedDecision:
        """Evaluate a tool result after execution.

        Creates a TOOL_RESULT event and submits it to the policy engine.
        This allows policies to detect injection attempts in tool output.

        Args:
            tool_name: Name of the tool that was called
            result: The result returned by the tool
            success: Whether the tool call succeeded
            error: Error message if the call failed
            metadata: Optional additional context
            correlation_id: Optional ID to correlate with before_call

        Returns:
            AggregatedDecision from policy evaluation
        """
        event = PolicyEvent.create(
            event_type=PolicyEventType.TOOL_RESULT,
            payload={
                "tool_name": tool_name,
                "result": result,
                "success": success,
                "error": error,
                "metadata": metadata or {},
            },
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            correlation_id=correlation_id,
        )

        return await self._engine.evaluate(event)

    async def intercept(
        self,
        tool_name: str,
        args: dict[str, Any],
        execute_fn: Any,  # Callable that executes the tool
        *,
        metadata: Optional[dict[str, Any]] = None,
        on_confirm_required: Optional[Any] = None,  # Callback for confirmation
    ) -> Any:
        """Full interception: evaluate before, execute, evaluate after.

        This is a convenience method that handles the full lifecycle
        of tool interception.

        Args:
            tool_name: Name of the tool to call
            args: Arguments for the tool
            execute_fn: Async function to execute the tool
            metadata: Optional additional context
            on_confirm_required: Optional callback for confirmation requests

        Returns:
            The tool execution result

        Raises:
            PolicyViolationError: If the tool call is blocked
            ConfirmationRequiredError: If confirmation is required and no callback
        """
        # Evaluate before
        before_result = await self.before_call(tool_name, args, metadata=metadata)

        # Handle confirmation requirement
        if before_result.requires_confirmation:
            if on_confirm_required:
                approved = await on_confirm_required(
                    before_result.confirmation_decision
                )
                if not approved:
                    raise PolicyViolationError(
                        before_result.confirmation_decision,  # type: ignore
                        PolicyEvent.create(
                            event_type=PolicyEventType.TOOL_CALL,
                            payload={"tool_name": tool_name, "args": args},
                            execution_id=self._execution_id,
                        ),
                        message="User denied confirmation",
                    )
            else:
                raise ConfirmationRequiredError(
                    before_result.confirmation_decision,  # type: ignore
                    PolicyEvent.create(
                        event_type=PolicyEventType.TOOL_CALL,
                        payload={"tool_name": tool_name, "args": args},
                        execution_id=self._execution_id,
                    ),
                )

        # Execute the tool
        try:
            result = await execute_fn(tool_name, args)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            raise  # Re-raise after recording

        finally:
            # Evaluate after (even on error)
            await self.after_call(
                tool_name,
                result,
                success=success,
                error=error,
                metadata=metadata,
            )

        return result
