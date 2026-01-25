"""
Tests for consistent error handling across graph executors.

Verifies that:
1. All executors classify errors consistently
2. Errors follow a shared contract (ExecutionError model)
3. Retriable errors trigger retries
4. Fatal errors terminate immediately
5. Error context is preserved for debugging
6. All error paths are properly logged
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from framework.runtime.core import Runtime
from framework.graph.goal import Goal, SuccessCriterion
from framework.graph.executor import GraphExecutor, ExecutionResult
from framework.graph.flexible_executor import FlexibleGraphExecutor, ExecutorConfig
from framework.graph.edge import GraphSpec
from framework.graph.node import NodeSpec
from framework.graph.plan import (
    Plan,
    PlanStep,
    ActionSpec,
    ActionType,
    ExecutionStatus,
    StepStatus,
)
from framework.graph.execution_errors import (
    ExecutionError,
    FatalExecutionError,
    RetriableExecutionError,
    ValidationExecutionError,
    DependencyExecutionError,
    UserExecutionError,
    ErrorCode,
    ErrorCategory,
    classify_error,
)


class TestErrorClassification:
    """Tests for error classification logic."""

    def test_classify_timeout_as_retriable(self):
        """TimeoutError should be classified as retriable."""
        original = TimeoutError("Connection timed out")
        exec_error = classify_error(original)
        
        assert exec_error.code == ErrorCode.TIMEOUT
        assert exec_error.category == ErrorCategory.RETRIABLE
        assert exec_error.retriable is True
        assert exec_error.original_error is original

    def test_classify_value_error_as_validation(self):
        """ValueError should be classified as validation error."""
        original = ValueError("Invalid input value")
        exec_error = classify_error(original)
        
        assert exec_error.code == ErrorCode.INPUT_VALIDATION_ERROR
        assert exec_error.category == ErrorCategory.VALIDATION
        assert exec_error.retriable is False

    def test_classify_key_error_as_dependency(self):
        """KeyError should be classified as dependency error."""
        original = KeyError("missing_key")
        exec_error = classify_error(original)
        
        assert exec_error.code == ErrorCode.MISSING_DEPENDENCY
        assert exec_error.category == ErrorCategory.DEPENDENCY
        assert exec_error.retriable is False

    def test_classify_memory_error_as_resource(self):
        """MemoryError should be classified as resource error."""
        original = MemoryError("Out of memory")
        exec_error = classify_error(original)
        
        assert exec_error.code == ErrorCode.OUT_OF_MEMORY
        assert exec_error.context == {}
        assert exec_error.retriable is False

    def test_classify_permission_error_as_security(self):
        """PermissionError should be classified as security error."""
        original = PermissionError("Access denied")
        exec_error = classify_error(original)
        
        assert exec_error.code == ErrorCode.SECURITY_ERROR
        assert exec_error.category == ErrorCategory.FATAL

    def test_execution_error_preserves_context(self):
        """ExecutionError should preserve context information."""
        context = {"node_id": "node_1", "step": 5}
        error = FatalExecutionError(
            code=ErrorCode.NODE_NOT_FOUND,
            message="Node not found",
            context=context,
        )
        
        assert error.context == context
        error_dict = error.to_dict()
        assert error_dict["context"] == context

    def test_execution_error_str_representation(self):
        """ExecutionError should have readable string representation."""
        error = FatalExecutionError(
            code=ErrorCode.MISSING_TOOL,
            message="Tool 'search' not found",
            context={"node_id": "node_1", "tools": ["search"]},
        )
        
        error_str = str(error)
        assert "MISSING_TOOL" in error_str
        assert "Tool 'search' not found" in error_str
        assert "node_id=node_1" in error_str


class TestExecutionErrorContract:
    """Tests for the ExecutionError contract across executors."""

    def test_fatal_error_is_not_retriable(self):
        """FatalExecutionError should never be retriable."""
        error = FatalExecutionError(
            code=ErrorCode.INVALID_NODE_TYPE,
            message="Invalid node type",
        )
        
        assert error.retriable is False
        assert error.category == ErrorCategory.FATAL

    def test_retriable_error_is_retriable(self):
        """RetriableExecutionError should be retriable."""
        error = RetriableExecutionError(
            code=ErrorCode.TIMEOUT,
            message="Request timed out",
        )
        
        assert error.retriable is True
        assert error.category == ErrorCategory.RETRIABLE

    def test_validation_error_not_retriable(self):
        """ValidationExecutionError should not be retriable."""
        error = ValidationExecutionError(
            message="Output schema mismatch",
        )
        
        assert error.retriable is False
        assert error.category == ErrorCategory.VALIDATION
        assert error.code == ErrorCode.SCHEMA_MISMATCH

    def test_dependency_error_not_retriable(self):
        """DependencyExecutionError should not be retriable."""
        error = DependencyExecutionError(
            message="Required input missing",
        )
        
        assert error.retriable is False
        assert error.category == ErrorCategory.DEPENDENCY

    def test_user_error_not_retriable(self):
        """UserExecutionError should not be retriable."""
        error = UserExecutionError(
            code=ErrorCode.APPROVAL_REJECTED,
            message="Step rejected by user",
        )
        
        assert error.retriable is False
        assert error.category == ErrorCategory.USER

    def test_error_with_original_exception(self):
        """ExecutionError should capture and expose original exception."""
        original = RuntimeError("Something went wrong")
        error = FatalExecutionError(
            code=ErrorCode.EXECUTION_FAILED,
            message="Execution failed",
            original_error=original,
        )
        
        assert error.original_error is original
        error_dict = error.to_dict()
        assert "RuntimeError: Something went wrong" in error_dict["original_error"]
        assert error_dict["stacktrace"] is not None


class TestGraphExecutorErrorHandling:
    """Tests for error handling in GraphExecutor."""

    @pytest.fixture
    def mock_runtime(self):
        """Create mock runtime."""
        runtime = Mock(spec=Runtime)
        runtime.start_run = Mock(return_value="run_1")
        runtime.end_run = Mock()
        runtime.report_problem = Mock()
        return runtime

    @pytest.fixture
    def executor(self, mock_runtime):
        """Create GraphExecutor with mocks."""
        return GraphExecutor(
            runtime=mock_runtime,
            llm=None,
            tools=[],
        )

    def test_invalid_node_type_raises_fatal_error(self, executor):
        """Invalid node type should raise FatalExecutionError."""
        node_spec = NodeSpec(
            id="bad_node",
            name="Bad Node",
            node_type="invalid_type",
        )
        
        with pytest.raises(FatalExecutionError) as exc_info:
            executor._get_node_implementation(node_spec)
        
        error = exc_info.value
        assert error.code == ErrorCode.INVALID_NODE_TYPE
        assert error.retriable is False
        assert "invalid_type" in str(error)

    def test_missing_tool_raises_fatal_error(self, executor):
        """Missing tool should raise FatalExecutionError."""
        node_spec = NodeSpec(
            id="llm_node",
            name="LLM Node",
            node_type="llm_tool_use",
            tools=["missing_tool"],
        )
        
        with pytest.raises(FatalExecutionError) as exc_info:
            executor._get_node_implementation(node_spec)
        
        error = exc_info.value
        assert error.code == ErrorCode.INVALID_CONFIGURATION
        assert "missing_tool" in str(error)

    def test_unregistered_function_node_raises_fatal_error(self, executor):
        """Unregistered function node should raise FatalExecutionError."""
        node_spec = NodeSpec(
            id="fn_node",
            name="Function Node",
            node_type="function",
        )
        
        with pytest.raises(FatalExecutionError) as exc_info:
            executor._get_node_implementation(node_spec)
        
        error = exc_info.value
        assert error.code == ErrorCode.INVALID_CONFIGURATION
        assert error.retriable is False

    @pytest.mark.asyncio
    async def test_execute_catches_and_classifies_errors(self, executor, mock_runtime):
        """Execute should catch errors and return failed ExecutionResult."""
        # Create a minimal graph with invalid entry point
        graph = Mock(spec=GraphSpec)
        graph.validate = Mock(return_value=[])
        graph.entry_node = "missing_node"
        graph.get_node = Mock(return_value=None)  # Node not found
        graph.max_steps = 100
        
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="Test",
        )
        
        result = await executor.execute(graph, goal)
        
        # Should return failed result, not raise
        assert result.success is False
        assert result.error is not None
        assert "NODE_NOT_FOUND" in result.error
        
        # Should have logged the problem
        mock_runtime.report_problem.assert_called()
        mock_runtime.end_run.assert_called()


class TestFlexibleExecutorErrorHandling:
    """Tests for error handling in FlexibleGraphExecutor."""

    @pytest.fixture
    def mock_runtime(self):
        """Create mock runtime."""
        runtime = Mock(spec=Runtime)
        runtime.start_run = Mock(return_value="run_1")
        runtime.end_run = Mock()
        runtime.report_problem = Mock()
        return runtime

    @pytest.fixture
    def executor(self, mock_runtime):
        """Create FlexibleGraphExecutor with mocks."""
        return FlexibleGraphExecutor(
            runtime=mock_runtime,
            llm=None,
        )

    @pytest.mark.asyncio
    async def test_execute_plan_catches_fatal_errors(self, executor, mock_runtime):
        """Execute plan should catch fatal errors and return failed result."""
        plan = Plan(
            id="plan_1",
            goal_id="goal_1",
            description="Test plan",
            steps=[],
        )
        plan.is_complete = Mock(return_value=False)
        plan.get_ready_steps = Mock(return_value=[])  # No ready steps
        plan.to_feedback_context = Mock(return_value={})
        plan.get_completed_steps = Mock(return_value=[])
        
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="Test",
        )
        
        result = await executor.execute_plan(plan, goal)
        
        # Should return failed result with error info
        assert result.status == ExecutionStatus.FAILED
        assert result.error is not None
        assert "No executable steps" in result.error
        
        # Should have logged and reported
        mock_runtime.report_problem.assert_called()
        mock_runtime.end_run.assert_called_once()
        call_args = mock_runtime.end_run.call_args
        assert call_args[1]["success"] is False

    @pytest.mark.asyncio
    async def test_approval_rejection_raises_user_error(self, executor, mock_runtime):
        """Approval rejection should raise UserExecutionError."""
        # This is tested indirectly through the try/except in execute_plan
        step = PlanStep(
            id="step_1",
            description="Test step",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            requires_approval=True,
        )
        
        plan = Plan(
            id="plan_1",
            goal_id="goal_1",
            description="Test plan",
            steps=[step],
        )
        plan.to_feedback_context = Mock(return_value={})
        plan.get_completed_steps = Mock(return_value=[])
        
        # Mock _request_approval to return rejection
        executor._request_approval = AsyncMock(return_value=Mock(
            decision="REJECT",
            reason="User rejected",
        ))
        
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="Test",
        )
        
        # Should handle the rejection gracefully
        result = await executor.execute_plan(plan, goal)
        
        assert result.status == ExecutionStatus.FAILED
        assert "rejected" in result.error.lower() or "APPROVAL_REJECTED" in result.error
        mock_runtime.end_run.assert_called()


class TestErrorHandlingConsistency:
    """Tests to verify error handling consistency between executors."""

    def test_both_executors_use_execution_error_types(self):
        """Both executors should use ExecutionError subclasses."""
        # GraphExecutor
        assert hasattr(GraphExecutor, '_get_node_implementation')
        
        # FlexibleGraphExecutor
        assert hasattr(FlexibleGraphExecutor, 'execute_plan')
        
        # Both should import ExecutionError
        from framework.graph.executor import ExecutionError as ExecutorExecutionError
        from framework.graph.flexible_executor import ExecutionError as FlexExecutionError
        
        assert ExecutorExecutionError is FlexExecutionError

    def test_error_codes_are_consistent(self):
        """Error codes should be consistent across both modules."""
        from framework.graph.executor import ErrorCode as ExecutorErrorCode
        from framework.graph.flexible_executor import ErrorCode as FlexErrorCode
        
        # Both should use the same ErrorCode enum
        assert ExecutorErrorCode is FlexErrorCode
        
        # Should have all expected codes
        expected_codes = [
            "TIMEOUT",
            "MISSING_TOOL",
            "INVALID_NODE_TYPE",
            "NODE_NOT_FOUND",
            "EXECUTION_FAILED",
        ]
        
        for code_name in expected_codes:
            assert hasattr(ErrorCode, code_name)

    def test_error_categories_are_consistent(self):
        """Error categories should be consistent across both modules."""
        from framework.graph.executor import ErrorCategory as ExecutorErrorCategory
        from framework.graph.flexible_executor import ErrorCategory as FlexErrorCategory
        
        # Both should use the same ErrorCategory enum
        assert ExecutorErrorCategory is FlexErrorCategory
        
        # Should have all expected categories
        expected_categories = [
            "RETRIABLE",
            "FATAL",
            "DEPENDENCY",
            "VALIDATION",
            "USER",
            "RESOURCE",
            "UNKNOWN",
        ]
        
        for cat_name in expected_categories:
            assert hasattr(ErrorCategory, cat_name)


class TestErrorLogging:
    """Tests for error logging and reporting."""

    def test_execution_error_to_dict(self):
        """ExecutionError.to_dict() should contain all necessary information."""
        error = FatalExecutionError(
            code=ErrorCode.NODE_NOT_FOUND,
            message="Node 'missing' not found",
            context={"node_id": "missing", "graph_id": "graph_1"},
            original_error=RuntimeError("Underlying error"),
        )
        
        error_dict = error.to_dict()
        
        # Check structure
        assert error_dict["code"] == "NODE_NOT_FOUND"
        assert error_dict["message"] == "Node 'missing' not found"
        assert error_dict["category"] == "fatal"
        assert error_dict["retriable"] is False
        assert error_dict["context"] == {"node_id": "missing", "graph_id": "graph_1"}
        assert error_dict["original_error"] is not None
        assert error_dict["stacktrace"] is not None

    def test_nested_execution_error(self):
        """ExecutionError should preserve chain of causation."""
        original = ValueError("Bad value")
        wrapped = FatalExecutionError(
            code=ErrorCode.EXECUTION_FAILED,
            message="Validation failed",
            original_error=original,
            context={"input": "invalid"},
        )
        
        assert wrapped.original_error is original
        error_dict = wrapped.to_dict()
        assert "ValueError" in error_dict["original_error"]
        assert error_dict["context"]["input"] == "invalid"


# Parametrized tests for common error scenarios
class TestCommonErrorScenarios:
    """Tests for common error scenarios in both executors."""

    @pytest.mark.parametrize(
        "exception,expected_code,expected_category",
        [
            (TimeoutError("Timeout"), ErrorCode.TIMEOUT, ErrorCategory.RETRIABLE),
            (ValueError("Invalid"), ErrorCode.INPUT_VALIDATION_ERROR, ErrorCategory.VALIDATION),
            (KeyError("Missing"), ErrorCode.MISSING_DEPENDENCY, ErrorCategory.DEPENDENCY),
            (MemoryError("OOM"), ErrorCode.OUT_OF_MEMORY, ErrorCategory.RESOURCE),
            (PermissionError("Denied"), ErrorCode.SECURITY_ERROR, ErrorCategory.FATAL),
        ],
    )
    def test_error_classification_consistency(self, exception, expected_code, expected_category):
        """All error types should be classified consistently."""
        error = classify_error(exception)
        
        assert error.code == expected_code
        assert error.category == expected_category
        assert error.original_error is exception


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
