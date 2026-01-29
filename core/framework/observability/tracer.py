"""
HiveTracer - OpenTelemetry Integration for Hive Agent Tracing.

This module provides the core tracing functionality for Hive, enabling
distributed tracing across graph executions, LLM calls, and tool invocations.

The tracer automatically:
- Creates hierarchical spans for graph → node → LLM/tool execution
- Propagates context across parallel node execution
- Records key attributes (run_id, tokens, latency, cost)
- Exports to any OTLP-compatible backend (Jaeger, Datadog, Grafana, etc.)

Usage:
    from framework.observability import get_tracer

    tracer = get_tracer()

    with tracer.trace_run(run_id, graph_id) as run_span:
        with tracer.trace_node(node_id, node_name, node_type) as node_span:
            with tracer.trace_llm_call(model, node_id) as llm_span:
                response = await llm.complete(...)
                llm_span.set_attribute("hive.tokens", response.total_tokens)
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from framework.observability.config import TracingConfig, get_default_config
from framework.observability.context import (
    HiveContextCarrier,
    capture_context,
    get_graph_id,
    get_node_id,
    get_run_id,
    reset_run_context,
    set_node_context,
    reset_node_context,
    set_run_context,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class HiveTracer:
    """
    OpenTelemetry integration for Hive agent tracing.

    This class provides context-manager-based tracing for all Hive operations.
    It gracefully degrades to no-ops when tracing is disabled or OTel is unavailable.

    Key features:
    - Hierarchical span creation (run → node → llm/tool)
    - Automatic run_id propagation via contextvars
    - Context capture/attach for parallel execution
    - Zero overhead when disabled
    - Graceful degradation without OTel dependency

    Attributes:
        enabled: Whether tracing is currently enabled
        config: The TracingConfig being used
    """

    def __init__(self, config: TracingConfig | None = None):
        """
        Initialize the HiveTracer.

        Args:
            config: Tracing configuration. If None, loads from environment.
        """
        self.config = config or get_default_config()
        self._tracer: "Tracer | None" = None
        self._initialized = False

        if self.config.enabled:
            self._initialize_otel()

    @property
    def enabled(self) -> bool:
        """Whether tracing is enabled and initialized."""
        return self.config.enabled and self._initialized

    def _initialize_otel(self) -> None:
        """Initialize OpenTelemetry SDK components."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME

            # Build resource with service name and custom attributes
            resource_attrs = {
                SERVICE_NAME: self.config.service_name,
                "hive.version": "1.0.0",  # TODO: Get from package version
            }
            resource_attrs.update(self.config.resource_attributes)
            resource = Resource.create(resource_attrs)

            # Create provider
            provider = TracerProvider(resource=resource)

            # Add OTLP exporter
            if self.config.otlp_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                        OTLPSpanExporter,
                    )

                    exporter = OTLPSpanExporter(
                        endpoint=self.config.otlp_endpoint,
                        insecure=self.config.otlp_endpoint.startswith("http://"),
                    )
                    processor = BatchSpanProcessor(
                        exporter,
                        max_queue_size=self.config.max_queue_size,
                        max_export_batch_size=self.config.max_export_batch_size,
                        export_timeout_millis=self.config.export_timeout_ms,
                    )
                    provider.add_span_processor(processor)
                    logger.info(
                        f"OTLP exporter configured: {self.config.otlp_endpoint}"
                    )
                except ImportError:
                    logger.warning(
                        "OTLP exporter not available. Install opentelemetry-exporter-otlp"
                    )

            # Add console exporter for debugging
            if self.config.console_export:
                try:
                    from opentelemetry.sdk.trace.export import (
                        ConsoleSpanExporter,
                        SimpleSpanProcessor,
                    )

                    console_processor = SimpleSpanProcessor(ConsoleSpanExporter())
                    provider.add_span_processor(console_processor)
                    logger.info("Console span exporter enabled")
                except ImportError:
                    pass

            # Set as global provider
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(
                self.config.service_name,
                "1.0.0",
            )
            self._initialized = True
            logger.info(f"Tracing initialized: service={self.config.service_name}")

        except ImportError as e:
            logger.warning(f"OpenTelemetry not available: {e}")
            self._initialized = False

    def _get_base_attributes(self) -> dict[str, Any]:
        """Get base attributes to include on all spans."""
        attrs = {}
        run_id = get_run_id()
        graph_id = get_graph_id()
        node_id = get_node_id()

        if run_id:
            attrs["hive.run_id"] = run_id
        if graph_id:
            attrs["hive.graph_id"] = graph_id
        if node_id:
            attrs["hive.node_id"] = node_id

        return attrs

    @contextmanager
    def trace_run(
        self,
        run_id: str,
        graph_id: str,
        goal_id: str | None = None,
        goal_description: str | None = None,
    ):
        """
        Create the root span for an entire graph execution run.

        This sets up the run context in contextvars so all child spans
        automatically include the run_id.

        Args:
            run_id: Unique identifier for this run
            graph_id: Identifier for the graph being executed
            goal_id: Optional goal identifier
            goal_description: Optional goal description

        Yields:
            The span object (or None if tracing disabled)

        Example:
            with tracer.trace_run(run_id, graph.id) as span:
                result = await executor.execute(graph, goal)
        """
        # Always set run context, even if tracing disabled
        run_token, graph_token = set_run_context(run_id, graph_id)

        if not self.enabled or self._tracer is None:
            try:
                yield None
            finally:
                reset_run_context(run_token, graph_token)
            return

        attributes = {
            "hive.run_id": run_id,
            "hive.graph_id": graph_id,
        }
        if goal_id:
            attributes["hive.goal_id"] = goal_id
        if goal_description:
            attributes["hive.goal_description"] = goal_description[:200]  # Truncate

        try:
            with self._tracer.start_as_current_span(
                "hive.run",
                attributes=attributes,
            ) as span:
                yield span
        finally:
            reset_run_context(run_token, graph_token)

    @contextmanager
    def trace_node(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        input_keys: list[str] | None = None,
        output_keys: list[str] | None = None,
    ):
        """
        Create a span for node execution.

        Args:
            node_id: Unique identifier for the node
            node_name: Human-readable node name
            node_type: Node type (llm_generate, llm_tool_use, router, etc.)
            input_keys: Input memory keys this node reads
            output_keys: Output memory keys this node writes

        Yields:
            The span object (or None if tracing disabled)
        """
        node_token = set_node_context(node_id)

        if not self.enabled or self._tracer is None:
            try:
                yield None
            finally:
                reset_node_context(node_token)
            return

        attributes = self._get_base_attributes()
        attributes.update({
            "hive.node_id": node_id,
            "hive.node_name": node_name,
            "hive.node_type": node_type,
        })
        if input_keys:
            attributes["hive.input_keys"] = ",".join(input_keys)
        if output_keys:
            attributes["hive.output_keys"] = ",".join(output_keys)

        try:
            with self._tracer.start_as_current_span(
                f"node.{node_name}",
                attributes=attributes,
            ) as span:
                yield span
        finally:
            reset_node_context(node_token)

    @contextmanager
    def trace_llm_call(
        self,
        model: str,
        operation: str = "complete",
        system_prompt_length: int | None = None,
        message_count: int | None = None,
        tools_count: int | None = None,
    ):
        """
        Create a span for an LLM API call.

        Args:
            model: Model identifier (e.g., "claude-3-haiku-20240307")
            operation: Operation type ("complete" or "complete_with_tools")
            system_prompt_length: Length of system prompt
            message_count: Number of messages in conversation
            tools_count: Number of tools available

        Yields:
            The span object (or None if tracing disabled)

        Example:
            with tracer.trace_llm_call(self.model) as span:
                response = litellm.completion(...)
                if span:
                    span.set_attribute("hive.input_tokens", response.input_tokens)
                    span.set_attribute("hive.output_tokens", response.output_tokens)
        """
        if not self.enabled or self._tracer is None:
            yield None
            return

        attributes = self._get_base_attributes()
        attributes.update({
            "hive.llm.model": model,
            "hive.llm.operation": operation,
            "gen_ai.system": self._infer_provider(model),
            "gen_ai.request.model": model,
        })

        if system_prompt_length is not None:
            attributes["hive.llm.system_prompt_length"] = system_prompt_length
        if message_count is not None:
            attributes["hive.llm.message_count"] = message_count
        if tools_count is not None:
            attributes["hive.llm.tools_count"] = tools_count

        with self._tracer.start_as_current_span(
            f"llm.{operation}",
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
    ):
        """
        Create a span for a tool invocation.

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Input parameters for the tool

        Yields:
            The span object (or None if tracing disabled)
        """
        if not self.enabled or self._tracer is None:
            yield None
            return

        attributes = self._get_base_attributes()
        attributes.update({
            "hive.tool.name": tool_name,
        })

        # Add sanitized tool input (avoid sensitive data)
        if tool_input:
            attributes["hive.tool.input_keys"] = ",".join(tool_input.keys())

        with self._tracer.start_as_current_span(
            f"tool.{tool_name}",
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def trace_decision(
        self,
        intent: str,
        options_count: int,
        chosen_option: str,
    ):
        """
        Create a span for an agent decision.

        Args:
            intent: What the agent was trying to accomplish
            options_count: Number of options considered
            chosen_option: ID of the chosen option

        Yields:
            The span object (or None if tracing disabled)
        """
        if not self.enabled or self._tracer is None:
            yield None
            return

        attributes = self._get_base_attributes()
        attributes.update({
            "hive.decision.intent": intent[:200],  # Truncate long intents
            "hive.decision.options_count": options_count,
            "hive.decision.chosen": chosen_option,
        })

        with self._tracer.start_as_current_span(
            "decision",
            attributes=attributes,
        ) as span:
            yield span

    def record_node_result(
        self,
        span: "Span | None",
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        """
        Record the result of a node execution on its span.

        Args:
            span: The span to update (may be None if tracing disabled)
            success: Whether the node succeeded
            tokens_used: Total tokens consumed
            latency_ms: Execution time in milliseconds
            error: Error message if failed
        """
        if span is None:
            return

        try:
            from opentelemetry.trace import Status, StatusCode

            span.set_attribute("hive.success", success)
            span.set_attribute("hive.tokens_used", tokens_used)
            span.set_attribute("hive.latency_ms", latency_ms)

            if success:
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, error or "Unknown error"))
                if error:
                    span.set_attribute("hive.error", error[:500])
        except ImportError:
            pass

    def record_llm_result(
        self,
        span: "Span | None",
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
        stop_reason: str | None = None,
    ) -> None:
        """
        Record LLM call results on its span.

        Args:
            span: The span to update
            input_tokens: Prompt tokens
            output_tokens: Completion tokens
            model: Actual model used (may differ from requested)
            stop_reason: Why generation stopped
        """
        if span is None:
            return

        span.set_attribute("hive.llm.input_tokens", input_tokens)
        span.set_attribute("hive.llm.output_tokens", output_tokens)
        span.set_attribute("hive.llm.total_tokens", input_tokens + output_tokens)

        # Also use semantic conventions for AI/ML
        span.set_attribute("gen_ai.usage.prompt_tokens", input_tokens)
        span.set_attribute("gen_ai.usage.completion_tokens", output_tokens)

        if model:
            span.set_attribute("gen_ai.response.model", model)
        if stop_reason:
            span.set_attribute("gen_ai.response.finish_reasons", [stop_reason])

    def record_exception(
        self,
        span: "Span | None",
        exception: Exception,
    ) -> None:
        """
        Record an exception on a span.

        Args:
            span: The span to update
            exception: The exception that occurred
        """
        if span is None:
            return

        try:
            from opentelemetry.trace import Status, StatusCode

            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))
        except ImportError:
            pass

    def capture_context_for_parallel(self) -> HiveContextCarrier:
        """
        Capture the current context for propagation to parallel tasks.

        Returns:
            A HiveContextCarrier that can be activated in parallel tasks
        """
        return HiveContextCarrier()

    def get_current_span(self) -> "Span | None":
        """
        Get the currently active span.

        Returns:
            The current span or None
        """
        if not self.enabled:
            return None

        try:
            from opentelemetry import trace
            return trace.get_current_span()
        except ImportError:
            return None

    def add_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Add an event to the current span.

        Args:
            name: Event name
            attributes: Event attributes
        """
        span = self.get_current_span()
        if span is not None:
            span.add_event(name, attributes=attributes or {})

    def _infer_provider(self, model: str) -> str:
        """Infer the LLM provider from model name."""
        model_lower = model.lower()
        if "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        elif "mistral" in model_lower:
            return "mistral"
        elif "llama" in model_lower:
            return "meta"
        elif "deepseek" in model_lower:
            return "deepseek"
        else:
            return "unknown"


# Global tracer instance (lazy-loaded)
_global_tracer: HiveTracer | None = None


def get_tracer(config: TracingConfig | None = None) -> HiveTracer:
    """
    Get the global HiveTracer instance.

    Creates the tracer on first call with the provided or default config.
    Subsequent calls return the same instance (config parameter ignored).

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        The global HiveTracer instance
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = HiveTracer(config)
    return _global_tracer


def reset_tracer() -> None:
    """
    Reset the global tracer.

    Use this for testing or to reconfigure tracing.
    """
    global _global_tracer
    _global_tracer = None


def traced_function(
    span_name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to trace a function.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes

    Returns:
        Decorated function

    Example:
        @traced_function(span_name="my_operation")
        async def my_function():
            ...
    """
    def decorator(func: F) -> F:
        name = span_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            if not tracer.enabled or tracer._tracer is None:
                return await func(*args, **kwargs)

            with tracer._tracer.start_as_current_span(
                name,
                attributes=attributes or {},
            ):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            if not tracer.enabled or tracer._tracer is None:
                return func(*args, **kwargs)

            with tracer._tracer.start_as_current_span(
                name,
                attributes=attributes or {},
            ):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


class SpanTimer:
    """
    Context manager for timing operations and recording to span.

    Usage:
        with SpanTimer(span, "hive.operation_ms") as timer:
            # Do work
            pass
        # Duration automatically recorded to span
    """

    def __init__(self, span: "Span | None", attribute_name: str):
        self.span = span
        self.attribute_name = attribute_name
        self.start_time: float = 0

    def __enter__(self) -> "SpanTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        if self.span is not None:
            duration_ms = int((time.perf_counter() - self.start_time) * 1000)
            self.span.set_attribute(self.attribute_name, duration_ms)
