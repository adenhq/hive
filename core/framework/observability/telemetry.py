"""
OpenTelemetry integration for agent observability.

This module provides a lightweight wrapper for OpenTelemetry tracing,
allowing for zero-configuration defaults and easy instrumentation
of core framework components.
"""

import functools
import logging
import os
from collections.abc import Callable
from typing import Any, TypeVar

# Try to import OpenTelemetry, but don't fail if not installed
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def get_tracer(name: str):
    """
    Get a tracer instance.

    Args:
        name: The name of the tracer (usually __name__).

    Returns:
        An OpenTelemetry tracer if available, otherwise a mock.
    """
    if HAS_OTEL:
        return trace.get_tracer(name)
    return MockTracer()


class MockTracer:
    """A mock tracer that no-ops when OpenTelemetry is not available."""

    def start_as_current_span(self, name: str, *args, **kwargs):
        return MockSpan()

    def start_span(self, name: str, *args, **kwargs):
        return MockSpan()


class MockSpan:
    """A mock span that no-ops."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_attribute(self, key: str, value: Any):
        pass

    def set_attributes(self, attributes: dict[str, Any]):
        pass

    def record_exception(self, exception: Exception, *args, **kwargs):
        pass

    def set_status(self, status: Any, *args, **kwargs):
        pass

    def add_event(self, name: str, *args, **kwargs):
        pass

    def end(self, *args, **kwargs):
        pass


def configure_telemetry(service_name: str = "hive", exporter_type: str | None = None) -> None:
    """
    Configure OpenTelemetry tracing.

    Defaults to no-op or console logging if not configured, ensuring
    zero friction for new users.

    Args:
        service_name: Name of the service for traces.
        exporter_type: 'otlp', 'console', or None (no-op).
                       Can also be set via HIVE_OTEL_EXPORTER env var.
    """
    if not HAS_OTEL:
        logger.debug("OpenTelemetry not installed, skipping telemetry configuration.")
        return

    exporter_type = exporter_type or os.getenv("HIVE_OTEL_EXPORTER")

    if not exporter_type:
        logger.debug("Telemetry exporter not configured, traces will not be exported.")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter_type == "console":
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
    elif exporter_type == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter()
            processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(processor)
        except ImportError:
            logger.error(
                "OTLP exporter requested but opentelemetry-exporter-otlp not installed."
            )
            return
        except Exception as e:
            logger.error(f"Failed to initialize OTLP exporter: {e}")
            return

    trace.set_tracer_provider(provider)
    logger.info(f"OpenTelemetry configured with {exporter_type} exporter.")


def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Callable[[F], F]:
    """
    Decorator for easy span instrumentation.

    Args:
        name: Name of the span.
        attributes: Initial attributes for the span.

    Returns:
        Decorated function.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(name) as span:
                from framework.observability.logging import get_trace_context
                context = get_trace_context()
                if context:
                    span.set_attributes(context)
                if attributes:
                    span.set_attributes(attributes)
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if HAS_OTEL:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(name) as span:
                from framework.observability.logging import get_trace_context
                context = get_trace_context()
                if context:
                    span.set_attributes(context)
                if attributes:
                    span.set_attributes(attributes)
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if HAS_OTEL:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
