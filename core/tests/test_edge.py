"""
Comprehensive tests for edge routing and conditional execution.

This test suite covers:
- All EdgeCondition types (ALWAYS, ON_SUCCESS, ON_FAILURE, CONDITIONAL, LLM_DECIDE)
- Input key mapping between nodes
- Conditional expression evaluation via safe_eval
- LLM-powered routing decisions
- Edge priority handling
- Error cases and edge validation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from framework.graph.edge import EdgeSpec, EdgeCondition, GraphSpec
from framework.graph.goal import Goal


class TestEdgeConditionAlways:
    """Test EdgeCondition.ALWAYS routing."""

    def test_always_traverses_on_success(self):
        """ALWAYS condition should traverse regardless of source success."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS,
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "success"},
            memory={}
        ) is True

    def test_always_traverses_on_failure(self):
        """ALWAYS condition should traverse even if source fails."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS,
        )

        assert edge.should_traverse(
            source_success=False,
            source_output={"error": "failed"},
            memory={}
        ) is True

    def test_always_with_no_output(self):
        """ALWAYS condition should traverse with empty output."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS,
        )

        assert edge.should_traverse(
            source_success=False,
            source_output={},
            memory={}
        ) is True


class TestEdgeConditionOnSuccess:
    """Test EdgeCondition.ON_SUCCESS routing."""

    def test_on_success_traverses_when_successful(self):
        """ON_SUCCESS should traverse only when source succeeds."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_SUCCESS,
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "success"},
            memory={}
        ) is True

    def test_on_success_blocks_on_failure(self):
        """ON_SUCCESS should NOT traverse when source fails."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_SUCCESS,
        )

        assert edge.should_traverse(
            source_success=False,
            source_output={"error": "failed"},
            memory={}
        ) is False


class TestEdgeConditionOnFailure:
    """Test EdgeCondition.ON_FAILURE routing."""

    def test_on_failure_blocks_on_success(self):
        """ON_FAILURE should NOT traverse when source succeeds."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_FAILURE,
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "success"},
            memory={}
        ) is False

    def test_on_failure_traverses_when_failed(self):
        """ON_FAILURE should traverse when source fails."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ON_FAILURE,
        )

        assert edge.should_traverse(
            source_success=False,
            source_output={"error": "failed"},
            memory={}
        ) is True


class TestEdgeConditionConditional:
    """Test EdgeCondition.CONDITIONAL with expression evaluation."""

    def test_conditional_simple_comparison(self):
        """Conditional edge with simple numeric comparison."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output['score'] > 0.8",
        )

        # Should traverse when score > 0.8
        assert edge.should_traverse(
            source_success=True,
            source_output={"score": 0.9},
            memory={}
        ) is True

        # Should not traverse when score <= 0.8
        assert edge.should_traverse(
            source_success=True,
            source_output={"score": 0.7},
            memory={}
        ) is False

    def test_conditional_uses_memory_directly(self):
        """Conditional edge can access memory keys directly."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="retry_count < 3",
        )

        # Should traverse when retry_count < 3
        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "step1"},
            memory={"retry_count": 1}
        ) is True

        # Should not traverse when retry_count >= 3
        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "step1"},
            memory={"retry_count": 5}
        ) is False

    def test_conditional_complex_expression(self):
        """Conditional edge with complex expression."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output['status'] == 'pending' and retry_count < 3",
        )

        # Should traverse: status=pending AND retry_count < 3
        assert edge.should_traverse(
            source_success=True,
            source_output={"status": "pending"},
            memory={"retry_count": 1}
        ) is True

        # Should not traverse: status != pending
        assert edge.should_traverse(
            source_success=True,
            source_output={"status": "complete"},
            memory={"retry_count": 1}
        ) is False

        # Should not traverse: retry_count >= 3
        assert edge.should_traverse(
            source_success=True,
            source_output={"status": "pending"},
            memory={"retry_count": 5}
        ) is False

    def test_conditional_with_ternary_expression(self):
        """Conditional edge with ternary (if-else) expression."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="True if output['value'] > 100 else False",
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"value": 150},
            memory={}
        ) is True

        assert edge.should_traverse(
            source_success=True,
            source_output={"value": 50},
            memory={}
        ) is False

    def test_conditional_with_membership_test(self):
        """Conditional edge with 'in' operator."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output['status'] in ['pending', 'processing']",
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"status": "pending"},
            memory={}
        ) is True

        assert edge.should_traverse(
            source_success=True,
            source_output={"status": "complete"},
            memory={}
        ) is False

    def test_conditional_with_invalid_expression_returns_false(self):
        """Invalid expressions should fail gracefully (return False)."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="undefined_variable > 5",
        )

        # Invalid expression should return False
        assert edge.should_traverse(
            source_success=True,
            source_output={"value": 10},
            memory={}
        ) is False

    def test_conditional_empty_expression_defaults_to_true(self):
        """Empty condition_expr should default to True."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="",
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={}
        ) is True

    def test_conditional_with_nested_attribute_access(self):
        """Conditional with nested output structure."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="len(output['items']) > 0",
        )

        assert edge.should_traverse(
            source_success=True,
            source_output={"items": [1, 2, 3]},
            memory={}
        ) is True

        assert edge.should_traverse(
            source_success=True,
            source_output={"items": []},
            memory={}
        ) is False


class TestEdgeConditionLLMDecide:
    """Test EdgeCondition.LLM_DECIDE routing."""

    def test_llm_decide_fallback_to_on_success_when_no_llm(self):
        """LLM_DECIDE should fallback to ON_SUCCESS when LLM is None."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.LLM_DECIDE,
            description="Decide if we should proceed",
        )

        # Should fallback to ON_SUCCESS behavior
        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={},
            llm=None,
            goal=None
        ) is True

        assert edge.should_traverse(
            source_success=False,
            source_output={"error": "failed"},
            memory={},
            llm=None,
            goal=None
        ) is False

    def test_llm_decide_fallback_to_on_success_when_no_goal(self):
        """LLM_DECIDE should fallback to ON_SUCCESS when goal is None."""
        mock_llm = MagicMock()

        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.LLM_DECIDE,
        )

        # Should fallback to ON_SUCCESS
        assert edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={},
            llm=mock_llm,
            goal=None
        ) is True

    def test_llm_decide_calls_llm_when_available(self):
        """LLM_DECIDE should call LLM when both llm and goal are available."""
        mock_llm = MagicMock()
        mock_llm.complete = MagicMock(return_value=MagicMock(
            content='{"proceed": true, "reasoning": "test reasoning"}'
        ))

        mock_goal = MagicMock()
        mock_goal.name = "Test Goal"
        mock_goal.description = "Test goal description"

        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.LLM_DECIDE,
            description="Test edge",
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={"step": 1},
            llm=mock_llm,
            goal=mock_goal,
            source_node_name="node_a",
            target_node_name="node_b"
        )

        # Should have called LLM
        mock_llm.complete.assert_called_once()
        assert result is True

    def test_llm_decide_parses_proceed_false(self):
        """LLM_DECIDE should respect 'proceed: false' from LLM."""
        mock_llm = MagicMock()
        mock_llm.complete = MagicMock(return_value=MagicMock(
            content='{"proceed": false, "reasoning": "not needed"}'
        ))

        mock_goal = MagicMock()
        mock_goal.name = "Test Goal"
        mock_goal.description = "Test goal description"

        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.LLM_DECIDE,
        )

        result = edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={},
            llm=mock_llm,
            goal=mock_goal
        )

        assert result is False

    def test_llm_decide_fallback_on_llm_error(self):
        """LLM_DECIDE should fallback to ON_SUCCESS on LLM error."""
        mock_llm = MagicMock()
        mock_llm.complete = MagicMock(side_effect=Exception("LLM error"))

        mock_goal = MagicMock()
        mock_goal.name = "Test Goal"
        mock_goal.description = "Test goal"

        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.LLM_DECIDE,
        )

        # Should fallback to on_success (True)
        result = edge.should_traverse(
            source_success=True,
            source_output={"result": "ok"},
            memory={},
            llm=mock_llm,
            goal=mock_goal
        )

        assert result is True


class TestEdgeInputMapping:
    """Test input mapping from source to target nodes."""

    def test_map_inputs_from_source_output(self):
        """Input mapping should extract keys from source output."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            input_mapping={"value": "result", "timestamp": "ts"},
        )

        mapped = edge.map_inputs(
            source_output={"result": 42, "ts": "2024-01-01"},
            memory={}
        )

        assert mapped == {"value": 42, "timestamp": "2024-01-01"}

    def test_map_inputs_from_memory(self):
        """Input mapping should fallback to memory if not in source output."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            input_mapping={"context": "stored_context"},
        )

        mapped = edge.map_inputs(
            source_output={"result": "ok"},
            memory={"stored_context": "important data"}
        )

        assert mapped == {"context": "important data"}

    def test_map_inputs_prefers_source_output(self):
        """Input mapping should prefer source_output over memory."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            input_mapping={"value": "data"},
        )

        mapped = edge.map_inputs(
            source_output={"data": "from_output"},
            memory={"data": "from_memory"}
        )

        # Should use source_output value
        assert mapped == {"value": "from_output"}

    def test_map_inputs_empty_mapping_returns_all_output(self):
        """No input_mapping should return all source_output."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
        )

        source_output = {"result": "ok", "count": 5}
        mapped = edge.map_inputs(source_output, memory={})

        assert mapped == source_output

    def test_map_inputs_missing_keys_excluded(self):
        """Missing source keys should be excluded from mapped output."""
        edge = EdgeSpec(
            id="test_edge",
            source="node_a",
            target="node_b",
            input_mapping={"value": "result", "extra": "nonexistent"},
        )

        mapped = edge.map_inputs(
            source_output={"result": 42},
            memory={}
        )

        # Should only include keys that exist in source or memory
        assert mapped == {"value": 42}


class TestEdgePriority:
    """Test edge priority ordering."""

    def test_get_outgoing_edges_sorted_by_priority(self):
        """get_outgoing_edges should return edges sorted by priority (highest first)."""
        edges = [
            EdgeSpec(id="e1", source="a", target="b", priority=1),
            EdgeSpec(id="e2", source="a", target="c", priority=10),
            EdgeSpec(id="e3", source="a", target="d", priority=5),
        ]

        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="a",
            nodes=[],
            edges=edges
        )

        outgoing = graph.get_outgoing_edges("a")

        # Should be sorted by priority descending
        assert outgoing[0].id == "e2"  # priority 10
        assert outgoing[1].id == "e3"  # priority 5
        assert outgoing[2].id == "e1"  # priority 1

    def test_get_incoming_edges(self):
        """get_incoming_edges should return all edges targeting a node."""
        edges = [
            EdgeSpec(id="e1", source="a", target="b"),
            EdgeSpec(id="e2", source="c", target="b"),
            EdgeSpec(id="e3", source="d", target="e"),
        ]

        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="a",
            nodes=[],
            edges=edges
        )

        incoming = graph.get_incoming_edges("b")

        assert len(incoming) == 2
        assert all(e.target == "b" for e in incoming)


class TestGraphSpecValidation:
    """Test GraphSpec validation."""

    def test_get_entry_point_returns_main_entry(self):
        """get_entry_point should return main entry_node by default."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            nodes=[]
        )

        assert graph.get_entry_point() == "start"

    def test_get_entry_point_resumes_from_pause_node(self):
        """get_entry_point should resume from pause_node if set."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            pause_nodes=["confirm"],
            entry_points={"confirm_resume": "resume_node"},
            nodes=[]
        )

        session_state = {"paused_at": "confirm"}
        assert graph.get_entry_point(session_state) == "resume_node"

    def test_get_entry_point_explicit_resume_from(self):
        """get_entry_point should respect explicit resume_from."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            entry_points={"custom": "custom_node"},
            nodes=[]
        )

        session_state = {"resume_from": "custom"}
        assert graph.get_entry_point(session_state) == "custom_node"

    def test_get_async_entry_point(self):
        """get_async_entry_point should find entry point by ID."""
        from framework.graph.edge import AsyncEntryPointSpec

        entry_points = [
            AsyncEntryPointSpec(
                id="webhook",
                name="Webhook Handler",
                entry_node="webhook_node",
                trigger_type="webhook"
            ),
            AsyncEntryPointSpec(
                id="api",
                name="API Handler",
                entry_node="api_node",
                trigger_type="api"
            ),
        ]

        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            async_entry_points=entry_points,
            nodes=[]
        )

        webhook_ep = graph.get_async_entry_point("webhook")
        assert webhook_ep.id == "webhook"
        assert webhook_ep.entry_node == "webhook_node"

    def test_has_async_entry_points(self):
        """has_async_entry_points should return True only with async entry points."""
        from framework.graph.edge import AsyncEntryPointSpec

        graph_without = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            nodes=[]
        )
        assert graph_without.has_async_entry_points() is False

        graph_with = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            async_entry_points=[
                AsyncEntryPointSpec(
                    id="webhook",
                    name="Webhook",
                    entry_node="start",
                    trigger_type="webhook"
                )
            ],
            nodes=[]
        )
        assert graph_with.has_async_entry_points() is True


class TestEdgeSpecValidation:
    """Test EdgeSpec validation and edge cases."""

    def test_edge_spec_with_extra_fields(self):
        """EdgeSpec should allow extra fields via model_config."""
        edge = EdgeSpec(
            id="test_edge",
            source="a",
            target="b",
            metadata={"custom": "value"}
        )

        assert edge.metadata == {"custom": "value"}

    def test_edge_spec_default_values(self):
        """EdgeSpec should have sensible defaults."""
        edge = EdgeSpec(
            id="test_edge",
            source="a",
            target="b",
        )

        assert edge.condition == EdgeCondition.ALWAYS
        assert edge.priority == 0
        assert edge.description == ""
        assert edge.input_mapping == {}
        assert edge.condition_expr is None

    def test_multiple_edges_from_one_node(self):
        """Graph should handle multiple outgoing edges from one node."""
        edges = [
            EdgeSpec(id="e1", source="a", target="b", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="e2", source="a", target="c", condition=EdgeCondition.ON_FAILURE),
        ]

        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="a",
            nodes=[],
            edges=edges
        )

        outgoing = graph.get_outgoing_edges("a")
        assert len(outgoing) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
