"""Tests for the OpenTelemetry integration module."""

import asyncio
import pytest
from opentelemetry import trace
from framework.observability import (
    configure_logging,
    get_trace_context,
    set_trace_context,
)
from framework.observability.telemetry import (
    HAS_OTEL,
    get_tracer,
    trace_span,
    configure_telemetry,
)

@pytest.fixture(scope="session", autouse=True)
def setup_telemetry():
    """Configure telemetry once for the test session."""
    # Using a try-except to handle cases where it's already configured
    try:
        configure_telemetry(exporter_type="console")
    except Exception:
        pass

@pytest.mark.asyncio
async def test_trace_span_decorator():
    """Test that the trace_span decorator correctly wraps a function."""
    
    @trace_span("test.decorated")
    async def decorated_func(val: str):
        return f"hello {val}"

    result = await decorated_func("world")
    assert result == "hello world"

@pytest.mark.asyncio
async def test_trace_context_propagation():
    """Test that trace context is propagated through nested spans."""
    
    @trace_span("test.child")
    async def child():
        ctx = get_trace_context()
        return ctx.get("test_key")

    @trace_span("test.parent")
    async def parent():
        set_trace_context(test_key="propagate_me")
        return await child()

    result = await parent()
    assert result == "propagate_me"

def test_get_tracer():
    """Test that getting a tracer returns a valid tracer object."""
    tracer = get_tracer("test_module")
    assert tracer is not None
    if HAS_OTEL:
        # Should be an SDK Tracer
        assert hasattr(tracer, "start_as_current_span")
    else:
        # Should be our MockTracer
        from framework.observability.telemetry import MockTracer
        assert isinstance(tracer, MockTracer)

@pytest.mark.asyncio
async def test_manual_span():
    """Test that manual spans can be created using the tracer."""
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("manual_span") as span:
        span.set_attribute("attr1", "val1")
        assert span is not None
