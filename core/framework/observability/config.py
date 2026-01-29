"""
OpenTelemetry Configuration for Hive.

Provides environment-based configuration for distributed tracing with
sensible defaults and zero-config operation.

Environment Variables:
    HIVE_TRACING_ENABLED: Enable/disable tracing (default: false)
    HIVE_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    HIVE_SERVICE_NAME: Service name for traces (default: hive-agent)
    HIVE_TRACING_SAMPLE_RATE: Sampling rate 0.0-1.0 (default: 1.0)
    HIVE_TRACING_CONSOLE_EXPORT: Export spans to console for debugging (default: false)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TracingConfig:
    """
    Configuration for OpenTelemetry tracing.

    Immutable configuration object that can be created from environment
    variables or passed explicitly.

    Attributes:
        enabled: Whether tracing is enabled
        service_name: Service name for span identification
        otlp_endpoint: OTLP collector gRPC endpoint
        sample_rate: Probability of sampling a trace (0.0-1.0)
        console_export: Also export spans to console (for debugging)
        resource_attributes: Additional resource attributes for all spans
        max_queue_size: Maximum spans queued before dropping
        max_export_batch_size: Maximum spans per export batch
        export_timeout_ms: Timeout for exporting spans
    """

    enabled: bool = False
    service_name: str = "hive-agent"
    otlp_endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0
    console_export: bool = False
    resource_attributes: dict[str, Any] = field(default_factory=dict)
    max_queue_size: int = 2048
    max_export_batch_size: int = 512
    export_timeout_ms: int = 30000

    @classmethod
    def from_env(cls) -> TracingConfig:
        """
        Create configuration from environment variables.

        This is the recommended way to configure tracing in production.
        All settings have sensible defaults for zero-config operation.

        Returns:
            TracingConfig populated from environment variables
        """
        def parse_bool(value: str | None, default: bool = False) -> bool:
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes", "on")

        def parse_float(value: str | None, default: float) -> float:
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                return default

        def parse_int(value: str | None, default: int) -> int:
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        # Parse resource attributes from HIVE_TRACING_RESOURCE_* env vars
        resource_attrs = {}
        for key, value in os.environ.items():
            if key.startswith("HIVE_TRACING_RESOURCE_"):
                attr_name = key[len("HIVE_TRACING_RESOURCE_"):].lower()
                resource_attrs[attr_name] = value

        return cls(
            enabled=parse_bool(os.environ.get("HIVE_TRACING_ENABLED")),
            service_name=os.environ.get("HIVE_SERVICE_NAME", "hive-agent"),
            otlp_endpoint=os.environ.get(
                "HIVE_OTLP_ENDPOINT", "http://localhost:4317"
            ),
            sample_rate=parse_float(
                os.environ.get("HIVE_TRACING_SAMPLE_RATE"), 1.0
            ),
            console_export=parse_bool(
                os.environ.get("HIVE_TRACING_CONSOLE_EXPORT")
            ),
            resource_attributes=resource_attrs,
            max_queue_size=parse_int(
                os.environ.get("HIVE_TRACING_MAX_QUEUE_SIZE"), 2048
            ),
            max_export_batch_size=parse_int(
                os.environ.get("HIVE_TRACING_MAX_BATCH_SIZE"), 512
            ),
            export_timeout_ms=parse_int(
                os.environ.get("HIVE_TRACING_EXPORT_TIMEOUT_MS"), 30000
            ),
        )

    def with_overrides(self, **kwargs: Any) -> TracingConfig:
        """
        Create a new config with specific values overridden.

        Args:
            **kwargs: Fields to override

        Returns:
            New TracingConfig with overrides applied
        """
        current = {
            "enabled": self.enabled,
            "service_name": self.service_name,
            "otlp_endpoint": self.otlp_endpoint,
            "sample_rate": self.sample_rate,
            "console_export": self.console_export,
            "resource_attributes": dict(self.resource_attributes),
            "max_queue_size": self.max_queue_size,
            "max_export_batch_size": self.max_export_batch_size,
            "export_timeout_ms": self.export_timeout_ms,
        }
        current.update(kwargs)
        return TracingConfig(**current)


# Default configuration singleton (lazy-loaded from environment)
_default_config: TracingConfig | None = None


def get_default_config() -> TracingConfig:
    """
    Get the default tracing configuration.

    Lazily loads from environment on first call.
    Thread-safe for concurrent access.

    Returns:
        The default TracingConfig instance
    """
    global _default_config
    if _default_config is None:
        _default_config = TracingConfig.from_env()
    return _default_config


def set_default_config(config: TracingConfig) -> None:
    """
    Set the default tracing configuration.

    Use this for testing or programmatic configuration.

    Args:
        config: The configuration to use as default
    """
    global _default_config
    _default_config = config
