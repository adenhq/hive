"""
Hive Observability - OpenTelemetry Distributed Tracing.

This module provides production-ready observability for Hive agents through
OpenTelemetry integration. It enables distributed tracing across graph
executions, LLM calls, tool invocations, and agent decisions.

Quick Start:
    # Enable via environment variables
    export HIVE_TRACING_ENABLED=true
    export HIVE_OTLP_ENDPOINT=http://localhost:4317
    export HIVE_SERVICE_NAME=my-research-agent

    # Or programmatically
    from framework.observability import get_tracer, TracingConfig

    config = TracingConfig(
        enabled=True,
        service_name="my-agent",
        otlp_endpoint="http://jaeger:4317",
    )
    tracer = get_tracer(config)

Usage Patterns:

    1. Graph Execution Tracing:
        ```python
        with tracer.trace_run(run_id, graph.id) as run_span:
            with tracer.trace_node(node.id, node.name, node.node_type) as node_span:
                result = await node.execute(ctx)
                tracer.record_node_result(node_span, result.success, result.tokens_used)
        ```

    2. LLM Call Tracing:
        ```python
        with tracer.trace_llm_call(model, "complete") as llm_span:
            response = await llm.complete(messages)
            tracer.record_llm_result(llm_span, response.input_tokens, response.output_tokens)
        ```

    3. Parallel Execution with Context Propagation:
        ```python
        # Capture context before spawning parallel tasks
        carrier = tracer.capture_context_for_parallel()

        async def parallel_node(node):
            with carrier.activate():  # Restores parent context
                return await execute_node(node)

        results = await asyncio.gather(*[parallel_node(n) for n in nodes])
        ```

Span Hierarchy:
    hive.run (root)
    └── node.{name}
        ├── llm.complete
        │   └── tool.{name}  (if tools used)
        ├── decision
        └── node.{next_name}
            └── ...

Attributes:
    All spans include these attributes when available:
    - hive.run_id: Unique execution run identifier
    - hive.graph_id: Graph being executed
    - hive.node_id: Current node
    - hive.success: Whether operation succeeded
    - hive.tokens_used: Total tokens consumed
    - hive.latency_ms: Operation duration

Integration with Backends:
    - Jaeger: Works out of box with OTLP endpoint
    - Datadog: Use OTLP ingest or DD agent
    - Grafana Tempo: OTLP compatible
    - Any OTLP-compatible backend
"""

from framework.observability.config import (
    TracingConfig,
    get_default_config,
    set_default_config,
)
from framework.observability.context import (
    HiveContextCarrier,
    attach_context,
    capture_context,
    extract_context_from_headers,
    get_graph_id,
    get_node_id,
    get_run_id,
    inject_context_to_headers,
)
from framework.observability.tracer import (
    HiveTracer,
    SpanTimer,
    get_tracer,
    reset_tracer,
    traced_function,
)

__all__ = [
    # Configuration
    "TracingConfig",
    "get_default_config",
    "set_default_config",
    # Tracer
    "HiveTracer",
    "get_tracer",
    "reset_tracer",
    "traced_function",
    "SpanTimer",
    # Context propagation
    "HiveContextCarrier",
    "capture_context",
    "attach_context",
    "get_run_id",
    "get_graph_id",
    "get_node_id",
    "inject_context_to_headers",
    "extract_context_from_headers",
]
