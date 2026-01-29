"""
Trace Context Propagation for Hive.

This module provides utilities for propagating OpenTelemetry context
across async boundaries, especially during parallel node execution.

The key insight is that when nodes execute in parallel via asyncio.gather(),
each task needs the parent's trace context explicitly attached to maintain
proper parent-child span relationships.

Usage:
    # Before spawning parallel tasks
    parent_ctx = capture_context()

    async def run_with_context(node):
        with attach_context(parent_ctx):
            return await execute_node(node)

    # All child spans correctly nest under parent
    results = await asyncio.gather(*[run_with_context(n) for n in nodes])
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

# Lazy imports for optional OpenTelemetry dependency
if TYPE_CHECKING:
    from opentelemetry.context import Context

# ContextVar for Hive-specific run correlation
_current_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hive_run_id", default=None
)

_current_graph_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hive_graph_id", default=None
)

_current_node_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hive_node_id", default=None
)


def set_run_context(
    run_id: str,
    graph_id: str | None = None,
) -> tuple[contextvars.Token, contextvars.Token | None]:
    """
    Set the current run context in contextvars.

    This should be called at the start of a graph execution to establish
    the run_id for all child spans.

    Args:
        run_id: Unique identifier for this execution run
        graph_id: Optional graph identifier

    Returns:
        Tokens for resetting the context (use in finally block)
    """
    run_token = _current_run_id.set(run_id)
    graph_token = _current_graph_id.set(graph_id) if graph_id else None
    return run_token, graph_token


def reset_run_context(
    run_token: contextvars.Token,
    graph_token: contextvars.Token | None,
) -> None:
    """
    Reset the run context using tokens from set_run_context.

    Args:
        run_token: Token from setting run_id
        graph_token: Token from setting graph_id (may be None)
    """
    _current_run_id.reset(run_token)
    if graph_token is not None:
        _current_graph_id.reset(graph_token)


def get_run_id() -> str | None:
    """Get the current run_id from context."""
    return _current_run_id.get()


def get_graph_id() -> str | None:
    """Get the current graph_id from context."""
    return _current_graph_id.get()


def set_node_context(node_id: str) -> contextvars.Token:
    """
    Set the current node context.

    Args:
        node_id: The node being executed

    Returns:
        Token for resetting
    """
    return _current_node_id.set(node_id)


def reset_node_context(token: contextvars.Token) -> None:
    """Reset node context using token."""
    _current_node_id.reset(token)


def get_node_id() -> str | None:
    """Get the current node_id from context."""
    return _current_node_id.get()


def capture_context() -> "Context | None":
    """
    Capture the current OpenTelemetry context for propagation.

    Use this before spawning parallel tasks to preserve the trace context.

    Returns:
        The current OTel context, or None if OTel is not available
    """
    try:
        from opentelemetry import context as otel_context
        return otel_context.get_current()
    except ImportError:
        return None


@contextmanager
def attach_context(ctx: "Context | None"):
    """
    Attach a captured context in a parallel task.

    This is a context manager that attaches the captured OTel context
    and detaches it when the block exits.

    Args:
        ctx: Context captured via capture_context()

    Yields:
        None

    Example:
        parent_ctx = capture_context()

        async def parallel_task():
            with attach_context(parent_ctx):
                # Spans created here are children of parent
                ...
    """
    if ctx is None:
        yield
        return

    try:
        from opentelemetry import context as otel_context
        token = otel_context.attach(ctx)
        try:
            yield
        finally:
            otel_context.detach(token)
    except ImportError:
        yield


def get_current_span_context() -> dict[str, Any]:
    """
    Get the current span context as a dictionary.

    Useful for serializing context across process boundaries
    (e.g., for distributed agents).

    Returns:
        Dict with trace_id, span_id, and trace_flags if available
    """
    try:
        from opentelemetry import trace
        from opentelemetry.trace import format_trace_id, format_span_id

        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx.is_valid:
            return {
                "trace_id": format_trace_id(ctx.trace_id),
                "span_id": format_span_id(ctx.span_id),
                "trace_flags": ctx.trace_flags,
                "is_remote": ctx.is_remote,
            }
    except ImportError:
        pass

    return {}


def inject_context_to_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Inject trace context into HTTP headers for distributed tracing.

    Args:
        headers: Existing headers dict

    Returns:
        Headers with trace context injected
    """
    try:
        from opentelemetry.propagate import inject
        inject(headers)
    except ImportError:
        pass
    return headers


def extract_context_from_headers(headers: dict[str, str]) -> "Context | None":
    """
    Extract trace context from HTTP headers.

    Args:
        headers: Headers containing trace context

    Returns:
        Extracted context or None
    """
    try:
        from opentelemetry.propagate import extract
        return extract(headers)
    except ImportError:
        return None


class HiveContextCarrier:
    """
    Context carrier for Hive-specific context propagation.

    This packages both OpenTelemetry context and Hive-specific
    run context for propagation across async boundaries.
    """

    def __init__(self):
        """Capture current context."""
        self.otel_context = capture_context()
        self.run_id = get_run_id()
        self.graph_id = get_graph_id()
        self.node_id = get_node_id()

    @contextmanager
    def activate(self):
        """
        Activate this carrier's context in a new async task.

        Usage:
            carrier = HiveContextCarrier()

            async def parallel_task():
                with carrier.activate():
                    # Full context restored
                    ...
        """
        # Restore Hive context
        run_token = None
        graph_token = None
        node_token = None

        if self.run_id:
            run_token = _current_run_id.set(self.run_id)
        if self.graph_id:
            graph_token = _current_graph_id.set(self.graph_id)
        if self.node_id:
            node_token = _current_node_id.set(self.node_id)

        try:
            # Restore OTel context
            with attach_context(self.otel_context):
                yield
        finally:
            # Reset Hive context
            if run_token is not None:
                _current_run_id.reset(run_token)
            if graph_token is not None:
                _current_graph_id.reset(graph_token)
            if node_token is not None:
                _current_node_id.reset(node_token)
