"""
Integration tests verifying error handling consistency.

These tests verify that the error handling contract is properly
implemented and that both executors follow the same semantics.
"""

import pytest
from framework.graph.execution_errors import (
    ExecutionError,
    ErrorCode,
    ErrorCategory,
)
from framework.graph.executor import GraphExecutor
from framework.graph.flexible_executor import FlexibleGraphExecutor


def test_execution_error_is_base_class():
    """ExecutionError should be importable from both executor modules."""
    from framework.graph.executor import ExecutionError as ExecutorError
    from framework.graph.flexible_executor import ExecutionError as FlexError
    
    # Both should refer to the same class
    assert ExecutorError is FlexError
    assert ExecutorError.__module__ == 'framework.graph.execution_errors'


def test_error_codes_consistent():
    """Error codes should be the same across both modules."""
    from framework.graph.executor import ErrorCode as ExecutorCode
    from framework.graph.flexible_executor import ErrorCode as FlexCode
    
    assert ExecutorCode is FlexCode
    
    # Verify all important codes exist
    important_codes = [
        'TIMEOUT',
        'MISSING_TOOL',
        'INVALID_NODE_TYPE',
        'NODE_NOT_FOUND',
        'EXECUTION_FAILED',
        'APPROVAL_REJECTED',
    ]
    
    for code in important_codes:
        assert hasattr(ErrorCode, code)


def test_error_categories_consistent():
    """Error categories should be the same across both modules."""
    from framework.graph.executor import ErrorCategory as ExecutorCategory
    from framework.graph.flexible_executor import ErrorCategory as FlexCategory
    
    assert ExecutorCategory is FlexCategory
    
    # Verify all categories exist
    required_categories = [
        'RETRIABLE',
        'FATAL',
        'DEPENDENCY',
        'VALIDATION',
        'USER',
        'RESOURCE',
        'UNKNOWN',
    ]
    
    for category in required_categories:
        assert hasattr(ErrorCategory, category)


def test_classify_error_function_available():
    """classify_error should be importable from both modules."""
    from framework.graph.executor import classify_error as executor_classify
    from framework.graph.flexible_executor import classify_error as flex_classify
    
    assert executor_classify is flex_classify
    
    # Test it works
    error = executor_classify(ValueError("test"))
    assert isinstance(error, ExecutionError)


def test_error_specializations_available():
    """All error specializations should be available."""
    from framework.graph.executor import (
        FatalExecutionError,
        RetriableExecutionError,
        ValidationExecutionError,
        DependencyExecutionError,
        UserExecutionError,
    )
    
    # Verify they're all ExecutionError subclasses
    assert issubclass(FatalExecutionError, ExecutionError)
    assert issubclass(RetriableExecutionError, ExecutionError)
    assert issubclass(ValidationExecutionError, ExecutionError)
    assert issubclass(DependencyExecutionError, ExecutionError)
    assert issubclass(UserExecutionError, ExecutionError)


def test_both_executors_import_errors():
    """Both executors should successfully import error classes."""
    # This test verifies that imports work without circular dependencies
    
    # GraphExecutor imports
    assert hasattr(GraphExecutor, '__init__')
    
    # FlexibleGraphExecutor imports
    assert hasattr(FlexibleGraphExecutor, '__init__')
    
    # Both can be instantiated with minimal args (mocked runtime)
    from unittest.mock import Mock
    mock_runtime = Mock()
    
    executor = GraphExecutor(runtime=mock_runtime)
    assert executor is not None
    
    flex_executor = FlexibleGraphExecutor(runtime=mock_runtime)
    assert flex_executor is not None


def test_error_codes_mapping():
    """Error code to retriable mapping should be complete."""
    from framework.graph.execution_errors import CODE_TO_RETRIABLE
    
    # Verify structure
    assert isinstance(CODE_TO_RETRIABLE, dict)
    
    # Verify retriable codes
    retriable_codes = [
        ErrorCode.TIMEOUT,
        ErrorCode.RATE_LIMIT,
        ErrorCode.TRANSIENT_FAILURE,
    ]
    
    for code in retriable_codes:
        assert CODE_TO_RETRIABLE[code] is True
    
    # Verify non-retriable codes
    non_retriable_codes = [
        ErrorCode.INVALID_NODE_TYPE,
        ErrorCode.MISSING_TOOL,
        ErrorCode.APPROVAL_REJECTED,
    ]
    
    for code in non_retriable_codes:
        assert CODE_TO_RETRIABLE[code] is False


def test_error_context_preservation():
    """Errors should preserve context through classification."""
    from framework.graph.execution_errors import classify_error
    
    # Test with a builtin exception
    original = ValueError("Invalid value for parameter X")
    error = classify_error(original)
    
    # Verify context is available
    assert error.context == {}  # No initial context
    
    # Add context
    error.context['parameter'] = 'X'
    error.context['value'] = 'invalid'
    
    # Verify context is preserved
    error_dict = error.to_dict()
    assert error_dict['context']['parameter'] == 'X'
    assert error_dict['context']['value'] == 'invalid'


def test_error_serialization():
    """Errors should be serializable for logging."""
    from framework.graph.execution_errors import FatalExecutionError
    
    error = FatalExecutionError(
        code=ErrorCode.MISSING_TOOL,
        message="Tool 'search' not found",
        context={"node_id": "node_1", "tools": ["search", "read"]},
    )
    
    # Serialize to dict
    error_dict = error.to_dict()
    
    # Verify all fields
    assert error_dict['code'] == 'MISSING_TOOL'
    assert error_dict['message'] == "Tool 'search' not found"
    assert error_dict['category'] == 'fatal'
    assert error_dict['retriable'] is False
    assert error_dict['context']['node_id'] == 'node_1'
    assert 'search' in error_dict['context']['tools']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
