"""
Hive Framework Exceptions.

This module defines the structured exception hierarchy for the Hive framework.
All exceptions raised during graph execution, tool usage, or LLM interactions
should inherit from HiveExecutionError.
"""


class HiveExecutionError(Exception):
    """Base exception for all Hive framework errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(HiveExecutionError):
    """Raised when a component is misconfigured or missing required dependencies."""
    pass


class ActionExecutionError(HiveExecutionError):
    """Base exception for errors occurring during action execution."""
    pass


class ToolExecutionError(ActionExecutionError):
    """Raised when a tool fails to execute."""
    pass


class LLMError(ActionExecutionError):
    """Base exception for LLM-related errors."""
    pass


class RateLimitError(LLMError):
    """Raised when an LLM provider rate limit is exceeded."""
    pass


class ContextLimitError(LLMError):
    """Raised when the context window is exceeded."""
    pass


class SubGraphError(ActionExecutionError):
    """Raised when a sub-graph execution fails."""
    pass


class CodeExecutionError(ActionExecutionError):
    """Raised when sandboxed code execution fails."""
    pass


class ValidationError(HiveExecutionError):
    """Raised when input or output validation fails."""
    pass
