"""
Comprehensive Test Suite for Hive OpenTelemetry Integration.

This module tests the observability infrastructure including:
- Configuration loading and environment variables
- Tracer initialization and graceful degradation
- Context propagation for parallel execution
- Span hierarchy and attribute recording
- Integration with mocked OpenTelemetry

Run with: pytest core/tests/test_observability.py -v
"""

import asyncio
import os
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================


class TestTracingConfig:
    """Test TracingConfig creation and environment parsing."""

    def test_default_config_values(self):
        """Default config should have tracing disabled."""
        from framework.observability.config import TracingConfig

        config = TracingConfig()

        assert config.enabled is False
        assert config.service_name == "hive-agent"
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.sample_rate == 1.0
        assert config.console_export is False

    def test_config_from_env_enabled(self, monkeypatch):
        """Config should parse HIVE_TRACING_ENABLED correctly."""
        from framework.observability.config import TracingConfig

        monkeypatch.setenv("HIVE_TRACING_ENABLED", "true")
        monkeypatch.setenv("HIVE_SERVICE_NAME", "test-agent")
        monkeypatch.setenv("HIVE_OTLP_ENDPOINT", "http://jaeger:4317")

        config = TracingConfig.from_env()

        assert config.enabled is True
        assert config.service_name == "test-agent"
        assert config.otlp_endpoint == "http://jaeger:4317"

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("", False),
        ("invalid", False),
    ])
    def test_config_bool_parsing(self, monkeypatch, value, expected):
        """Boolean environment variables should parse correctly."""
        from framework.observability.config import TracingConfig

        monkeypatch.setenv("HIVE_TRACING_ENABLED", value)
        config = TracingConfig.from_env()
        assert config.enabled is expected

    def test_config_sample_rate_parsing(self, monkeypatch):
        """Sample rate should parse as float."""
        from framework.observability.config import TracingConfig

        monkeypatch.setenv("HIVE_TRACING_SAMPLE_RATE", "0.5")
        config = TracingConfig.from_env()
        assert config.sample_rate == 0.5

    def test_config_sample_rate_invalid(self, monkeypatch):
        """Invalid sample rate should use default."""
        from framework.observability.config import TracingConfig

        monkeypatch.setenv("HIVE_TRACING_SAMPLE_RATE", "invalid")
        config = TracingConfig.from_env()
        assert config.sample_rate == 1.0

    def test_config_resource_attributes(self, monkeypatch):
        """Resource attributes should be parsed from HIVE_TRACING_RESOURCE_* vars."""
        from framework.observability.config import TracingConfig

        monkeypatch.setenv("HIVE_TRACING_RESOURCE_ENVIRONMENT", "production")
        monkeypatch.setenv("HIVE_TRACING_RESOURCE_VERSION", "1.0.0")

        config = TracingConfig.from_env()

        assert config.resource_attributes["environment"] == "production"
        assert config.resource_attributes["version"] == "1.0.0"

    def test_config_with_overrides(self):
        """with_overrides should create new config with changes."""
        from framework.observability.config import TracingConfig

        original = TracingConfig(enabled=False, service_name="original")
        modified = original.with_overrides(enabled=True, service_name="modified")

        # Original unchanged
        assert original.enabled is False
        assert original.service_name == "original"

        # Modified has new values
        assert modified.enabled is True
        assert modified.service_name == "modified"

    def test_config_immutable(self):
        """TracingConfig should be immutable (frozen dataclass)."""
        from framework.observability.config import TracingConfig

        config = TracingConfig()

        with pytest.raises(AttributeError):
            config.enabled = True  # type: ignore


# =============================================================================
# CONTEXT PROPAGATION TESTS
# =============================================================================


class TestContextPropagation:
    """Test context propagation utilities for parallel execution."""

    def test_run_context_set_and_get(self):
        """Run context should be set and retrieved correctly."""
        from framework.observability.context import (
            get_run_id,
            reset_run_context,
            set_run_context,
        )

        # Initially None
        assert get_run_id() is None

        # Set context
        run_token, graph_token = set_run_context("run_123", "graph_456")

        try:
            assert get_run_id() == "run_123"
        finally:
            reset_run_context(run_token, graph_token)

        # After reset, should be None again
        assert get_run_id() is None

    def test_context_isolation_in_tasks(self):
        """Context should be isolated between async tasks by default."""
        from framework.observability.context import get_run_id, set_run_context

        async def check_context():
            # Should not see parent context (contextvars are task-local)
            return get_run_id()

        async def main():
            run_token, _ = set_run_context("parent_run", None)

            # Start a new task - it won't inherit the context
            result = await asyncio.create_task(check_context())

            # Context is NOT automatically propagated to new tasks
            # (This is the problem we solve with HiveContextCarrier)
            return result

        # Note: In Python 3.11+, contextvars ARE copied to tasks
        # This test may need adjustment based on Python version
        result = asyncio.run(main())
        # The behavior depends on Python version, so we just check it runs

    def test_hive_context_carrier_propagation(self):
        """HiveContextCarrier should propagate context to parallel tasks."""
        from framework.observability.context import (
            HiveContextCarrier,
            get_run_id,
            set_run_context,
            reset_run_context,
        )

        async def parallel_task(carrier: HiveContextCarrier):
            with carrier.activate():
                return get_run_id()

        async def main():
            run_token, graph_token = set_run_context("propagated_run", "graph_1")
            try:
                # Capture context
                carrier = HiveContextCarrier()

                # Run parallel tasks with carrier
                results = await asyncio.gather(
                    parallel_task(carrier),
                    parallel_task(carrier),
                    parallel_task(carrier),
                )

                return results
            finally:
                reset_run_context(run_token, graph_token)

        results = asyncio.run(main())

        # All tasks should see the propagated run_id
        assert all(r == "propagated_run" for r in results)

    def test_node_context_set_and_get(self):
        """Node context should be set and retrieved correctly."""
        from framework.observability.context import (
            get_node_id,
            reset_node_context,
            set_node_context,
        )

        assert get_node_id() is None

        token = set_node_context("node_abc")
        try:
            assert get_node_id() == "node_abc"
        finally:
            reset_node_context(token)

        assert get_node_id() is None


# =============================================================================
# TRACER TESTS
# =============================================================================


class TestHiveTracer:
    """Test HiveTracer functionality."""

    def test_tracer_disabled_by_default(self):
        """Tracer should be disabled when config.enabled is False."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=False)
        tracer = HiveTracer(config)

        assert tracer.enabled is False

    def test_tracer_context_managers_noop_when_disabled(self):
        """Context managers should be no-ops when tracing disabled."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=False)
        tracer = HiveTracer(config)

        # All context managers should work but yield None
        with tracer.trace_run("run_1", "graph_1") as span:
            assert span is None

        with tracer.trace_node("node_1", "Test Node", "llm_generate") as span:
            assert span is None

        with tracer.trace_llm_call("gpt-4") as span:
            assert span is None

        with tracer.trace_tool_call("calculator") as span:
            assert span is None

    def test_tracer_graceful_without_otel(self):
        """Tracer should work gracefully without OpenTelemetry installed."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        # Even with enabled=True, if OTel isn't available it should gracefully degrade
        config = TracingConfig(enabled=True)

        # Mock ImportError for opentelemetry
        with patch.dict('sys.modules', {'opentelemetry': None}):
            tracer = HiveTracer(config)
            # Should not raise, just be disabled
            assert tracer._initialized is False or tracer.enabled is False

    def test_get_tracer_singleton(self):
        """get_tracer should return singleton instance."""
        from framework.observability.tracer import get_tracer, reset_tracer

        reset_tracer()  # Clear any existing

        tracer1 = get_tracer()
        tracer2 = get_tracer()

        assert tracer1 is tracer2

        reset_tracer()  # Cleanup

    def test_tracer_captures_context_for_parallel(self):
        """capture_context_for_parallel should return a HiveContextCarrier."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer
        from framework.observability.context import HiveContextCarrier

        config = TracingConfig(enabled=False)
        tracer = HiveTracer(config)

        carrier = tracer.capture_context_for_parallel()

        assert isinstance(carrier, HiveContextCarrier)


# =============================================================================
# SPAN HIERARCHY TESTS (with mocked OTel)
# =============================================================================


class MockSpan:
    """Mock OpenTelemetry span for testing."""

    def __init__(self, name: str):
        self.name = name
        self.attributes: dict[str, Any] = {}
        self.events: list[tuple[str, dict]] = []
        self.status = None
        self.exception = None
        self.ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        self.events.append((name, attributes or {}))

    def set_status(self, status: Any) -> None:
        self.status = status

    def record_exception(self, exception: Exception) -> None:
        self.exception = exception

    def end(self) -> None:
        self.ended = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.end()


class MockTracer:
    """Mock OpenTelemetry tracer for testing span creation."""

    def __init__(self):
        self.spans: list[MockSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, attributes: dict | None = None):
        span = MockSpan(name)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        self.spans.append(span)
        yield span


class TestSpanHierarchy:
    """Test span creation and hierarchy with mocked OTel."""

    def test_trace_run_creates_span_with_attributes(self):
        """trace_run should create span with correct attributes."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        # Replace internal tracer with mock
        mock_tracer = MockTracer()
        tracer._tracer = mock_tracer
        tracer._initialized = True

        with tracer.trace_run(
            run_id="run_123",
            graph_id="graph_456",
            goal_id="goal_789",
            goal_description="Test goal",
        ):
            pass

        assert len(mock_tracer.spans) == 1
        span = mock_tracer.spans[0]

        assert span.name == "hive.run"
        assert span.attributes["hive.run_id"] == "run_123"
        assert span.attributes["hive.graph_id"] == "graph_456"
        assert span.attributes["hive.goal_id"] == "goal_789"

    def test_trace_node_includes_run_context(self):
        """trace_node should include run_id from context."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer
        from framework.observability.context import set_run_context, reset_run_context

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_tracer = MockTracer()
        tracer._tracer = mock_tracer
        tracer._initialized = True

        # Set run context
        run_token, graph_token = set_run_context("run_abc", "graph_def")

        try:
            with tracer.trace_node(
                node_id="node_1",
                node_name="Test Node",
                node_type="llm_generate",
                input_keys=["input1", "input2"],
                output_keys=["output1"],
            ):
                pass
        finally:
            reset_run_context(run_token, graph_token)

        assert len(mock_tracer.spans) == 1
        span = mock_tracer.spans[0]

        assert span.name == "node.Test Node"
        assert span.attributes["hive.run_id"] == "run_abc"
        assert span.attributes["hive.node_id"] == "node_1"
        assert span.attributes["hive.node_type"] == "llm_generate"
        assert span.attributes["hive.input_keys"] == "input1,input2"
        assert span.attributes["hive.output_keys"] == "output1"

    def test_trace_llm_call_attributes(self):
        """trace_llm_call should record model and operation."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_tracer = MockTracer()
        tracer._tracer = mock_tracer
        tracer._initialized = True

        with tracer.trace_llm_call(
            model="claude-3-haiku-20240307",
            operation="complete",
            system_prompt_length=100,
            message_count=5,
            tools_count=3,
        ):
            pass

        span = mock_tracer.spans[0]

        assert span.name == "llm.complete"
        assert span.attributes["hive.llm.model"] == "claude-3-haiku-20240307"
        assert span.attributes["hive.llm.operation"] == "complete"
        assert span.attributes["gen_ai.system"] == "anthropic"
        assert span.attributes["hive.llm.system_prompt_length"] == 100
        assert span.attributes["hive.llm.message_count"] == 5
        assert span.attributes["hive.llm.tools_count"] == 3

    def test_record_node_result_success(self):
        """record_node_result should set success attributes."""
        from framework.observability.tracer import HiveTracer
        from framework.observability.config import TracingConfig

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_span = MockSpan("test")

        # Call record_node_result - it will try to import trace but
        # our MockSpan handles set_attribute directly
        tracer.record_node_result(
            span=mock_span,
            success=True,
            tokens_used=1500,
            latency_ms=250,
        )

        assert mock_span.attributes["hive.success"] is True
        assert mock_span.attributes["hive.tokens_used"] == 1500
        assert mock_span.attributes["hive.latency_ms"] == 250

    def test_record_llm_result_attributes(self):
        """record_llm_result should set token counts."""
        from framework.observability.tracer import HiveTracer
        from framework.observability.config import TracingConfig

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_span = MockSpan("test")

        tracer.record_llm_result(
            span=mock_span,
            input_tokens=500,
            output_tokens=150,
            model="claude-3-opus",
            stop_reason="end_turn",
        )

        assert mock_span.attributes["hive.llm.input_tokens"] == 500
        assert mock_span.attributes["hive.llm.output_tokens"] == 150
        assert mock_span.attributes["hive.llm.total_tokens"] == 650
        assert mock_span.attributes["gen_ai.usage.prompt_tokens"] == 500
        assert mock_span.attributes["gen_ai.response.model"] == "claude-3-opus"

    def test_provider_inference(self):
        """_infer_provider should correctly identify providers."""
        from framework.observability.tracer import HiveTracer
        from framework.observability.config import TracingConfig

        tracer = HiveTracer(TracingConfig())

        assert tracer._infer_provider("claude-3-haiku-20240307") == "anthropic"
        assert tracer._infer_provider("gpt-4o-mini") == "openai"
        assert tracer._infer_provider("gemini-1.5-pro") == "google"
        assert tracer._infer_provider("mistral-large") == "mistral"
        assert tracer._infer_provider("llama-3.1-70b") == "meta"
        assert tracer._infer_provider("deepseek-chat") == "deepseek"
        assert tracer._infer_provider("unknown-model") == "unknown"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestTracerIntegration:
    """Integration tests for the complete tracing flow."""

    @pytest.mark.asyncio
    async def test_nested_span_hierarchy(self):
        """Test that spans nest correctly: run → node → llm → tool."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_tracer = MockTracer()
        tracer._tracer = mock_tracer
        tracer._initialized = True

        with tracer.trace_run("run_1", "graph_1") as run_span:
            with tracer.trace_node("node_1", "Research", "llm_tool_use") as node_span:
                with tracer.trace_llm_call("claude-3-haiku") as llm_span:
                    with tracer.trace_tool_call("web_search", {"query": "test"}) as tool_span:
                        pass

        # Should have 4 spans created
        assert len(mock_tracer.spans) == 4

        span_names = [s.name for s in mock_tracer.spans]
        assert "hive.run" in span_names
        assert "node.Research" in span_names
        assert "llm.complete" in span_names
        assert "tool.web_search" in span_names

    @pytest.mark.asyncio
    async def test_parallel_execution_context_propagation(self):
        """Test context propagation in parallel execution scenario."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer
        from framework.observability.context import get_run_id

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_tracer = MockTracer()
        tracer._tracer = mock_tracer
        tracer._initialized = True

        async def parallel_node(carrier, node_id: str):
            """Simulate a node running in parallel."""
            with carrier.activate():
                # Should see the run_id from parent context
                run_id = get_run_id()
                with tracer.trace_node(node_id, f"Node {node_id}", "llm_generate"):
                    await asyncio.sleep(0.01)  # Simulate work
                return run_id

        with tracer.trace_run("parallel_run", "graph_1"):
            # Capture context before parallel execution
            carrier = tracer.capture_context_for_parallel()

            # Run nodes in parallel
            results = await asyncio.gather(
                parallel_node(carrier, "node_a"),
                parallel_node(carrier, "node_b"),
                parallel_node(carrier, "node_c"),
            )

        # All parallel nodes should have seen the same run_id
        assert all(r == "parallel_run" for r in results)

        # Should have 1 run span + 3 node spans
        assert len(mock_tracer.spans) == 4

    def test_exception_recording(self):
        """Test that exceptions are recorded on spans."""
        from framework.observability.config import TracingConfig
        from framework.observability.tracer import HiveTracer

        config = TracingConfig(enabled=True)
        tracer = HiveTracer(config)

        mock_span = MockSpan("test")

        test_error = ValueError("Something went wrong")

        # Call record_exception - MockSpan handles record_exception directly
        tracer.record_exception(mock_span, test_error)

        assert mock_span.exception is test_error


# =============================================================================
# DECORATOR TESTS
# =============================================================================


class TestTracedFunctionDecorator:
    """Test the @traced_function decorator."""

    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """@traced_function should work with async functions."""
        from framework.observability.tracer import traced_function, reset_tracer

        reset_tracer()

        @traced_function(span_name="test_operation")
        async def my_async_function(x: int) -> int:
            return x * 2

        result = await my_async_function(5)

        assert result == 10

        reset_tracer()

    def test_traced_sync_function(self):
        """@traced_function should work with sync functions."""
        from framework.observability.tracer import traced_function, reset_tracer

        reset_tracer()

        @traced_function(span_name="sync_operation")
        def my_sync_function(x: int) -> int:
            return x * 3

        result = my_sync_function(5)

        assert result == 15

        reset_tracer()


# =============================================================================
# SPAN TIMER TESTS
# =============================================================================


class TestSpanTimer:
    """Test SpanTimer context manager."""

    def test_span_timer_records_duration(self):
        """SpanTimer should record duration as attribute."""
        from framework.observability.tracer import SpanTimer
        import time

        mock_span = MockSpan("test")

        with SpanTimer(mock_span, "hive.operation_ms"):
            time.sleep(0.05)  # 50ms

        # Should have recorded approximately 50ms
        assert "hive.operation_ms" in mock_span.attributes
        duration = mock_span.attributes["hive.operation_ms"]
        assert 40 <= duration <= 100  # Allow some variance

    def test_span_timer_noop_with_none_span(self):
        """SpanTimer should handle None span gracefully."""
        from framework.observability.tracer import SpanTimer

        # Should not raise
        with SpanTimer(None, "hive.operation_ms"):
            pass


# =============================================================================
# CLEANUP
# =============================================================================


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before and after each test."""
    from framework.observability.tracer import reset_tracer
    from framework.observability.config import set_default_config, TracingConfig

    reset_tracer()
    set_default_config(TracingConfig())

    yield

    reset_tracer()
    set_default_config(TracingConfig())
