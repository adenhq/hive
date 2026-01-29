"""
OpenTelemetry Tracing Examples for Hive.

This module provides practical examples of how to use Hive's distributed
tracing capabilities in different scenarios.

Quick Start:
    1. Start Jaeger: docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
    2. Set environment variables:
       export HIVE_TRACING_ENABLED=true
       export HIVE_OTLP_ENDPOINT=http://localhost:4317
    3. Run your Hive agent
    4. View traces at http://localhost:16686

Examples in this file:
    - Basic tracing setup
    - Custom span attributes
    - Parallel execution with context propagation
    - Error handling and exception recording
    - Integration with existing code
"""

import asyncio
from typing import Any


# =============================================================================
# EXAMPLE 1: Basic Tracing Setup
# =============================================================================

def example_basic_setup():
    """
    Basic tracing setup using environment variables.

    Set these environment variables before running:
        HIVE_TRACING_ENABLED=true
        HIVE_OTLP_ENDPOINT=http://localhost:4317
        HIVE_SERVICE_NAME=my-research-agent
    """
    from framework.observability import get_tracer, TracingConfig

    # Option 1: Use environment variables (recommended for production)
    tracer = get_tracer()  # Automatically loads from env

    # Option 2: Programmatic configuration (useful for testing)
    config = TracingConfig(
        enabled=True,
        service_name="my-agent",
        otlp_endpoint="http://localhost:4317",
        console_export=True,  # Also print spans to console for debugging
    )
    tracer = get_tracer(config)

    # Use the tracer
    with tracer.trace_run("run_001", "research_graph"):
        print("Executing with tracing enabled!")


# =============================================================================
# EXAMPLE 2: Manual Span Creation
# =============================================================================

async def example_manual_spans():
    """
    Create spans manually for custom operations.

    This is useful when you have operations that aren't automatically
    traced by the framework.
    """
    from framework.observability import get_tracer

    tracer = get_tracer()

    # Create a run span (root of the trace)
    with tracer.trace_run(
        run_id="run_manual_001",
        graph_id="custom_graph",
        goal_id="goal_123",
        goal_description="Analyze customer feedback",
    ) as run_span:

        # Create a node span
        with tracer.trace_node(
            node_id="analyze_sentiment",
            node_name="Sentiment Analyzer",
            node_type="llm_generate",
            input_keys=["feedback_text"],
            output_keys=["sentiment_score", "confidence"],
        ) as node_span:

            # Simulate some work
            await asyncio.sleep(0.1)

            # Create an LLM call span
            with tracer.trace_llm_call(
                model="claude-3-haiku-20240307",
                operation="complete",
                message_count=3,
            ) as llm_span:

                # Simulate LLM call
                await asyncio.sleep(0.2)

                # Record LLM metrics
                tracer.record_llm_result(
                    span=llm_span,
                    input_tokens=150,
                    output_tokens=50,
                    model="claude-3-haiku-20240307",
                    stop_reason="end_turn",
                )

            # Record node result
            tracer.record_node_result(
                span=node_span,
                success=True,
                tokens_used=200,
                latency_ms=300,
            )

        # Add custom attributes to run span
        if run_span:
            run_span.set_attribute("hive.custom_metric", 42)


# =============================================================================
# EXAMPLE 3: Parallel Execution with Context Propagation
# =============================================================================

async def example_parallel_execution():
    """
    Properly propagate trace context to parallel tasks.

    This is CRITICAL for maintaining correct span hierarchy when
    executing nodes in parallel with asyncio.gather().
    """
    from framework.observability import get_tracer

    tracer = get_tracer()

    async def process_item(carrier, item_id: str):
        """Process a single item with proper context."""
        # IMPORTANT: Activate the carrier to restore parent context
        with carrier.activate():
            with tracer.trace_node(
                node_id=f"process_{item_id}",
                node_name=f"Process Item {item_id}",
                node_type="function",
            ) as span:
                await asyncio.sleep(0.05)  # Simulate work
                if span:
                    span.set_attribute("item.id", item_id)
                return f"result_{item_id}"

    with tracer.trace_run("parallel_run_001", "batch_processor"):
        with tracer.trace_node(
            node_id="batch_orchestrator",
            node_name="Batch Orchestrator",
            node_type="function",
        ):
            # CRITICAL: Capture context BEFORE creating parallel tasks
            carrier = tracer.capture_context_for_parallel()

            # All parallel tasks will have their spans correctly
            # nested under the orchestrator span
            results = await asyncio.gather(
                process_item(carrier, "a"),
                process_item(carrier, "b"),
                process_item(carrier, "c"),
                process_item(carrier, "d"),
            )

            print(f"Processed {len(results)} items")


# =============================================================================
# EXAMPLE 4: Error Handling
# =============================================================================

async def example_error_handling():
    """
    Properly record errors and exceptions in traces.
    """
    from framework.observability import get_tracer

    tracer = get_tracer()

    with tracer.trace_run("error_run_001", "error_demo"):
        with tracer.trace_node(
            node_id="risky_operation",
            node_name="Risky Operation",
            node_type="llm_tool_use",
        ) as node_span:
            try:
                # Simulate an operation that might fail
                raise ValueError("Something went wrong!")

            except Exception as e:
                # Record the exception on the span
                tracer.record_exception(node_span, e)

                # Record failure in node result
                tracer.record_node_result(
                    span=node_span,
                    success=False,
                    error=str(e),
                )

                # Re-raise or handle as appropriate
                print(f"Caught and recorded error: {e}")


# =============================================================================
# EXAMPLE 5: Custom Tool Tracing
# =============================================================================

async def example_tool_tracing():
    """
    Trace custom tool invocations.
    """
    from framework.observability import get_tracer

    tracer = get_tracer()

    async def call_web_search(query: str) -> dict[str, Any]:
        """Simulated web search tool."""
        with tracer.trace_tool_call(
            tool_name="web_search",
            tool_input={"query": query},
        ) as tool_span:
            # Simulate API call
            await asyncio.sleep(0.1)

            result = {
                "results": ["Result 1", "Result 2"],
                "total": 2,
            }

            if tool_span:
                tool_span.set_attribute("tool.results_count", result["total"])

            return result

    with tracer.trace_run("tool_run_001", "search_agent"):
        with tracer.trace_node(
            node_id="search_node",
            node_name="Web Searcher",
            node_type="llm_tool_use",
        ):
            results = await call_web_search("Hive AI agents")
            print(f"Found {results['total']} results")


# =============================================================================
# EXAMPLE 6: Integration with GraphExecutor
# =============================================================================

def example_executor_integration():
    """
    The GraphExecutor automatically traces executions.

    When you use the standard GraphExecutor, tracing is automatic:
    - Each run creates a root span
    - Each node execution creates a child span
    - LLM calls within nodes create nested spans
    - Tool calls create their own spans

    Just enable tracing via environment variables and run your agent!
    """
    example_code = '''
    # This is already done for you in GraphExecutor!
    # Just enable tracing:

    export HIVE_TRACING_ENABLED=true
    export HIVE_OTLP_ENDPOINT=http://localhost:4317

    # Then run your agent normally:

    from framework.graph.executor import GraphExecutor
    from framework.runtime.core import Runtime

    runtime = Runtime("/path/to/storage")
    executor = GraphExecutor(runtime=runtime, llm=my_llm)

    # Tracing happens automatically!
    result = await executor.execute(graph, goal, input_data)

    # View traces in Jaeger at http://localhost:16686
    '''
    print(example_code)


# =============================================================================
# EXAMPLE 7: Viewing Traces in Jaeger
# =============================================================================

def example_jaeger_setup():
    """
    Instructions for setting up Jaeger to view traces.
    """
    instructions = '''
    ╔══════════════════════════════════════════════════════════════════╗
    ║                    JAEGER SETUP GUIDE                            ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║  1. Start Jaeger with Docker:                                    ║
    ║                                                                  ║
    ║     docker run -d --name jaeger \\                                ║
    ║       -p 16686:16686 \\                                           ║
    ║       -p 4317:4317 \\                                             ║
    ║       jaegertracing/all-in-one:latest                            ║
    ║                                                                  ║
    ║  2. Configure Hive:                                              ║
    ║                                                                  ║
    ║     export HIVE_TRACING_ENABLED=true                             ║
    ║     export HIVE_OTLP_ENDPOINT=http://localhost:4317              ║
    ║     export HIVE_SERVICE_NAME=my-research-agent                   ║
    ║                                                                  ║
    ║  3. Run your Hive agent                                          ║
    ║                                                                  ║
    ║  4. View traces at: http://localhost:16686                       ║
    ║                                                                  ║
    ║  Useful Jaeger queries:                                          ║
    ║  • service=hive-agent                                            ║
    ║  • service=hive-agent AND hive.run_id="run_123"                  ║
    ║  • service=hive-agent AND hive.node_type="llm_tool_use"          ║
    ║  • service=hive-agent AND error=true                             ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    '''
    print(instructions)


# =============================================================================
# RUN EXAMPLES
# =============================================================================

if __name__ == "__main__":
    import os

    # Enable console export for demo
    os.environ["HIVE_TRACING_ENABLED"] = "true"
    os.environ["HIVE_TRACING_CONSOLE_EXPORT"] = "true"

    print("\n" + "=" * 60)
    print("HIVE OPENTELEMETRY TRACING EXAMPLES")
    print("=" * 60)

    print("\n--- Example: Jaeger Setup ---")
    example_jaeger_setup()

    print("\n--- Example: Basic Setup ---")
    example_basic_setup()

    print("\n--- Example: Manual Spans ---")
    asyncio.run(example_manual_spans())

    print("\n--- Example: Parallel Execution ---")
    asyncio.run(example_parallel_execution())

    print("\n--- Example: Error Handling ---")
    asyncio.run(example_error_handling())

    print("\n--- Example: Tool Tracing ---")
    asyncio.run(example_tool_tracing())

    print("\n" + "=" * 60)
    print("Examples complete! Enable OTLP endpoint to see traces in Jaeger.")
    print("=" * 60)
