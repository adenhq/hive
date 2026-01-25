"""
Shared Error Model for Graph Execution.

Provides consistent error handling across all graph executors with
clear distinction between retriable and fatal errors.
"""

from enum import Enum
from typing import Any
from dataclasses import dataclass, field


class ExecutionErrorType(str, Enum):
    """
    Categories of execution errors.
    
    Errors are classified as either retriable or fatal to enable
    consistent retry logic across all executors.
    """
    # Retriable errors - temporary issues that may succeed on retry
    RETRIABLE_TRANSIENT = "retriable_transient"  # Network timeouts, rate limits, temporary service issues
    RETRIABLE_VALIDATION = "retriable_validation"  # Input validation, output format issues
    
    # Fatal errors - permanent issues that won't succeed on retry
    FATAL_CONFIGURATION = "fatal_configuration"  # Missing tools, invalid node types, configuration errors
    FATAL_SECURITY = "fatal_security"  # Sandbox security violations, permission errors
    FATAL_EXCEPTION = "fatal_exception"  # Unexpected exceptions, programming errors


@dataclass
class ExecutionError:
    """
    Structured execution error with classification and context.
    
    Provides rich error information for debugging and enables
    consistent error handling across all executors.
    
    Example:
        error = ExecutionError(
            error_type=ExecutionErrorType.RETRIABLE_TRANSIENT,
            message="Rate limit exceeded",
            details={"retry_after": 60},
            source="llm_node",
        )
    """
    error_type: ExecutionErrorType
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    source: str = ""  # Which component raised the error (e.g., "executor", "worker_node", "llm_node")
    original_exception: Exception | None = None
    
    @property
    def retriable(self) -> bool:
        """Check if this error is retriable."""
        return is_retriable(self.error_type)
    
    def __str__(self) -> str:
        """Human-readable error string."""
        parts = [f"[{self.error_type.value}]"]
        if self.source:
            parts.append(f"({self.source})")
        parts.append(self.message)
        return " ".join(parts)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "source": self.source,
            "retriable": self.retriable,
            "original_exception": str(self.original_exception) if self.original_exception else None,
        }


def is_retriable(error_type: ExecutionErrorType) -> bool:
    """
    Check if an error type is retriable.
    
    Args:
        error_type: The error type to check
        
    Returns:
        True if the error is retriable, False otherwise
    """
    return error_type in {
        ExecutionErrorType.RETRIABLE_TRANSIENT,
        ExecutionErrorType.RETRIABLE_VALIDATION,
    }


def classify_exception(exception: Exception, context: str = "") -> ExecutionErrorType:
    """
    Classify an exception into an ExecutionErrorType.
    
    Uses heuristics to determine if an exception represents a retriable
    or fatal error based on exception type and message content.
    
    Args:
        exception: The exception to classify
        context: Optional context about where the exception occurred
        
    Returns:
        The appropriate ExecutionErrorType
        
    Example:
        error_type = classify_exception(TimeoutError("Connection timeout"))
        # Returns ExecutionErrorType.RETRIABLE_TRANSIENT
    """
    error_msg = str(exception).lower()
    exception_type = type(exception).__name__
    
    # Timeout errors are retriable
    if isinstance(exception, TimeoutError) or "timeout" in error_msg:
        return ExecutionErrorType.RETRIABLE_TRANSIENT
    
    # Rate limit errors are retriable
    if "rate" in error_msg and "limit" in error_msg:
        return ExecutionErrorType.RETRIABLE_TRANSIENT
    
    # Network/connection errors are retriable
    if any(keyword in error_msg for keyword in ["connection", "network", "unavailable", "503", "502", "504"]):
        return ExecutionErrorType.RETRIABLE_TRANSIENT
    
    # Validation errors are retriable (can fix input and retry)
    if isinstance(exception, (ValueError, TypeError)) or "validation" in error_msg:
        return ExecutionErrorType.RETRIABLE_VALIDATION
    
    # JSON decode errors are validation issues
    if "json" in error_msg and ("decode" in error_msg or "parse" in error_msg):
        return ExecutionErrorType.RETRIABLE_VALIDATION
    
    # Configuration errors are fatal
    if any(keyword in error_msg for keyword in ["not found", "missing", "not registered", "not configured"]):
        return ExecutionErrorType.FATAL_CONFIGURATION
    
    # Permission/security errors are fatal
    if isinstance(exception, PermissionError) or any(keyword in error_msg for keyword in ["permission", "forbidden", "unauthorized", "security"]):
        return ExecutionErrorType.FATAL_SECURITY
    
    # Import errors and attribute errors are usually configuration issues
    if isinstance(exception, (ImportError, AttributeError, ModuleNotFoundError)):
        return ExecutionErrorType.FATAL_CONFIGURATION
    
    # Default: treat as fatal exception
    return ExecutionErrorType.FATAL_EXCEPTION


def create_execution_error(
    error_type: ExecutionErrorType | str,
    message: str,
    source: str = "",
    details: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> ExecutionError:
    """
    Convenience function to create an ExecutionError.
    
    Args:
        error_type: Error type (enum or string)
        message: Error message
        source: Source component
        details: Additional context
        exception: Original exception if any
        
    Returns:
        ExecutionError instance
    """
    # Convert string to enum if needed
    if isinstance(error_type, str):
        error_type = ExecutionErrorType(error_type)
    
    return ExecutionError(
        error_type=error_type,
        message=message,
        source=source,
        details=details or {},
        original_exception=exception,
    )


def from_exception(
    exception: Exception,
    source: str = "",
    context: str = "",
    details: dict[str, Any] | None = None,
) -> ExecutionError:
    """
    Create an ExecutionError from an exception with automatic classification.
    
    Args:
        exception: The exception to wrap
        source: Source component
        context: Additional context for classification
        details: Additional details
        
    Returns:
        ExecutionError with classified error type
        
    Example:
        try:
            # some operation
        except Exception as e:
            error = from_exception(e, source="worker_node")
            return StepExecutionResult(success=False, execution_error=error)
    """
    error_type = classify_exception(exception, context)
    
    return ExecutionError(
        error_type=error_type,
        message=str(exception),
        source=source,
        details=details or {},
        original_exception=exception,
    )
