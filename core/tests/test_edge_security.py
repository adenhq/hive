"""
Tests for EdgeSpec condition evaluation security.

These tests verify that the _evaluate_condition method properly prevents
code injection attacks by using safe_eval instead of raw eval().

Related to: [Security]: EdgeSpec._evaluate_condition uses unsafe eval()
"""

import pytest
from framework.graph.edge import EdgeSpec, EdgeCondition


class TestEdgeConditionSecurity:
    """Security tests for EdgeSpec conditional evaluation."""

    def test_simple_condition_evaluation(self):
        """Test that simple, legitimate conditions work correctly."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output.get('confidence', 0) > 0.8",
        )

        # Should return True when condition is met
        result = edge.should_traverse(
            source_success=True,
            source_output={"confidence": 0.9},
            memory={},
        )
        assert result is True

        # Should return False when condition is not met
        result = edge.should_traverse(
            source_success=True,
            source_output={"confidence": 0.5},
            memory={},
        )
        assert result is False

    def test_memory_access_in_condition(self):
        """Test that conditions can safely access memory values."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="retry_count < 3",
        )

        # Memory values should be accessible
        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={"retry_count": 1},
        )
        assert result is True

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={"retry_count": 5},
        )
        assert result is False

    def test_boolean_literals_in_condition(self):
        """Test that lowercase true/false work in conditions."""
        edge_true = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="true",
        )

        edge_false = EdgeSpec(
            id="test-edge-2",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="false",
        )

        assert edge_true.should_traverse(True, {}, {}) is True
        assert edge_false.should_traverse(True, {}, {}) is False

    def test_blocks_private_attribute_access(self):
        """Test that accessing private attributes (__class__, __bases__, etc.) is blocked."""
        # Attempt to access __class__ - common code injection technique
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output.__class__.__bases__",
        )

        # Should return False (blocked) instead of executing
        result = edge.should_traverse(
            source_success=True,
            source_output={"data": "test"},
            memory={},
        )
        assert result is False

    def test_blocks_dunder_mro_access(self):
        """Test that __mro__ access for class hierarchy traversal is blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="().__class__.__mro__[-1].__subclasses__()",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_globals_access(self):
        """Test that accessing __globals__ is blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="(lambda: 0).__globals__",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_code_object_access(self):
        """Test that accessing __code__ is blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="(lambda: 0).__code__",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_import_attempts(self):
        """Test that import statements in conditions are blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="__import__('os').system('echo pwned')",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_eval_in_condition(self):
        """Test that nested eval() calls are blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="eval('1+1')",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_exec_in_condition(self):
        """Test that exec() calls are blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="exec('x=1')",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_compile_in_condition(self):
        """Test that compile() calls are blocked."""
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="compile('pass', '', 'exec')",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_blocks_subclass_enumeration(self):
        """Test that __subclasses__() enumeration attack is blocked."""
        # This is a common attack to find dangerous classes like os._wrap_close
        edge = EdgeSpec(
            id="malicious-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="''.__class__.__mro__[2].__subclasses__()",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_empty_condition_returns_true(self):
        """Test that empty/None condition expressions return True."""
        edge_none = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr=None,
        )

        edge_empty = EdgeSpec(
            id="test-edge-2",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="",
        )

        assert edge_none.should_traverse(True, {}, {}) is True
        assert edge_empty.should_traverse(True, {}, {}) is True

    def test_syntax_error_returns_false(self):
        """Test that syntax errors in conditions return False gracefully."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="if True then False",  # Invalid Python syntax
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={},
            memory={},
        )
        assert result is False

    def test_comparison_operators_work(self):
        """Test that standard comparison operators work correctly."""
        test_cases = [
            ("result == 42", {"result": 42}, True),
            ("result != 42", {"result": 42}, False),
            ("result > 10", {"result": 42}, True),
            ("result < 10", {"result": 42}, False),
            ("result >= 42", {"result": 42}, True),
            ("result <= 42", {"result": 42}, True),
        ]

        for expr, output, expected in test_cases:
            edge = EdgeSpec(
                id="test-edge",
                source="node_a",
                target="node_b",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr=expr,
            )
            result = edge.should_traverse(True, output, {})
            assert result is expected, f"Failed for expression: {expr}"

    def test_logical_operators_work(self):
        """Test that logical operators (and, or, not) work correctly."""
        test_cases = [
            ("result > 10 and result < 50", {"result": 42}, True),
            ("result > 10 and result < 20", {"result": 42}, False),
            ("result < 10 or result > 40", {"result": 42}, True),
            ("not result", {"result": False}, True),
            ("not result", {"result": True}, False),
        ]

        for expr, output, expected in test_cases:
            edge = EdgeSpec(
                id="test-edge",
                source="node_a",
                target="node_b",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr=expr,
            )
            result = edge.should_traverse(True, output, {})
            assert result is expected, f"Failed for expression: {expr}"

    def test_string_operations_work(self):
        """Test that safe string operations work in conditions."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="'error' in output.get('message', '')",
        )

        result_with_error = edge.should_traverse(
            source_success=True,
            source_output={"message": "An error occurred"},
            memory={},
        )
        assert result_with_error is True

        result_without_error = edge.should_traverse(
            source_success=True,
            source_output={"message": "Success"},
            memory={},
        )
        assert result_without_error is False

    def test_list_operations_work(self):
        """Test that safe list operations work in conditions."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="len(output.get('items', [])) > 0",
        )

        result_with_items = edge.should_traverse(
            source_success=True,
            source_output={"items": [1, 2, 3]},
            memory={},
        )
        assert result_with_items is True

        result_empty = edge.should_traverse(
            source_success=True,
            source_output={"items": []},
            memory={},
        )
        assert result_empty is False


class TestEdgeConditionTypes:
    """Tests for different EdgeCondition types."""

    def test_always_condition(self):
        """Test ALWAYS condition type."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS,
        )

        assert edge.should_traverse(True, {}, {}) is True
        assert edge.should_traverse(False, {}, {}) is True

    def test_on_success_condition(self):
        """Test ON_SUCCESS condition type."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_SUCCESS,
        )

        assert edge.should_traverse(True, {}, {}) is True
        assert edge.should_traverse(False, {}, {}) is False

    def test_on_failure_condition(self):
        """Test ON_FAILURE condition type."""
        edge = EdgeSpec(
            id="test-edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_FAILURE,
        )

        assert edge.should_traverse(True, {}, {}) is False
        assert edge.should_traverse(False, {}, {}) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
