#core/framework/errors.py

class HiveError(Exception):
    """Base class for all Hive execution errors."""
    error_type = "UNKNOWN"
    retryable = False

    def __init__(self, message, *, node_id=None, original_exception=None):
        super().__init__(message)
        self.node_id = node_id
        self.original_exception = original_exception


class LLMProviderError(HiveError):
    error_type = "LLM_PROVIDER"
    retryable = True


class ToolExecutionError(HiveError):
    error_type = "TOOL_EXECUTION"
    retryable = False


class ConfigurationError(HiveError):
    error_type = "CONFIGURATION"
    retryable = False


class TimeoutError(HiveError):
    error_type = "TIMEOUT"
    retryable = True
