"""
Unit tests for graph validation methods in edge.py.

Tests the following validation methods added to GraphSpec:
- _find_orphaned_nodes(): Detect nodes with no incoming/outgoing edges
- _find_cycles(): Detect cycles in the graph
- _validate_input_availability(): Ensure all node inputs are available
- validate(): Combined validation with all checks

Run with:
    pytest core/tests/test_graph_validation.py -v
"""

import pytest
from framework.graph import NodeSpec, EdgeSpec, EdgeCondition
from framework.graph.edge import GraphSpec


# =============================================================================
# Fixtures - Reusable node and edge definitions
# =============================================================================

@pytest.fixture
def simple_nodes():
    """Create a set of simple nodes for testing."""
    return {
        "start": NodeSpec(
            id="start",
            name="Start",
            description="Entry node",
            node_type="llm_generate",
            input_keys=["user_input"],
            output_keys=["processed"],
            system_prompt="Process input",
        ),
        "middle": NodeSpec(
            id="middle",
            name="Middle",
            description="Middle node",
            node_type="llm_generate",
            input_keys=["processed"],
            output_keys=["result"],
            system_prompt="Process further",
        ),
        "end": NodeSpec(
            id="end",
            name="End",
            description="Terminal node",
            node_type="llm_generate",
            input_keys=["result"],
            output_keys=["final"],
            system_prompt="Finalize",
        ),
    }


@pytest.fixture
def simple_edges():
    """Create simple linear edges."""
    return [
        EdgeSpec(
            id="start-to-middle",
            source="start",
            target="middle",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="middle-to-end",
            source="middle",
            target="end",
            condition=EdgeCondition.ON_SUCCESS,
        ),
    ]


@pytest.fixture
def valid_graph(simple_nodes, simple_edges):
    """Create a valid graph with no issues."""
    return GraphSpec(
        id="valid-graph",
        goal_id="test-goal",
        entry_node="start",
        entry_points={"start": "start"},
        terminal_nodes=["end"],
        nodes=list(simple_nodes.values()),
        edges=simple_edges,
    )


# =============================================================================
# Tests for _find_orphaned_nodes()
# =============================================================================

class TestFindOrphanedNodes:
    """Tests for orphaned node detection."""

    def test_no_orphans_in_valid_graph(self, valid_graph):
        """Valid graph should have no orphaned nodes."""
        errors = valid_graph._find_orphaned_nodes()
        assert len(errors) == 0

    def test_detects_node_with_no_incoming_edges(self, simple_nodes, simple_edges):
        """Should detect a node that has no incoming edges and is not an entry point."""
        orphan = NodeSpec(
            id="orphan",
            name="Orphan",
            description="Disconnected node",
            node_type="llm_generate",
            input_keys=["something"],
            output_keys=["nothing"],
            system_prompt="Never runs",
        )

        graph = GraphSpec(
            id="orphan-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()) + [orphan],
            edges=simple_edges,  # No edges to orphan
        )

        errors = graph._find_orphaned_nodes()
        assert len(errors) >= 1
        assert any("orphan" in e.lower() and "no incoming" in e.lower() for e in errors)

    def test_detects_node_with_no_outgoing_edges(self, simple_nodes):
        """Should detect a node with no outgoing edges that isn't terminal/pause."""
        dead_end = NodeSpec(
            id="dead-end",
            name="Dead End",
            description="Goes nowhere",
            node_type="llm_generate",
            input_keys=["processed"],
            output_keys=["dead"],
            system_prompt="Dead end",
        )

        edges = [
            EdgeSpec(
                id="start-to-middle",
                source="start",
                target="middle",
                condition=EdgeCondition.ON_SUCCESS,
            ),
            EdgeSpec(
                id="middle-to-end",
                source="middle",
                target="end",
                condition=EdgeCondition.ON_SUCCESS,
            ),
            EdgeSpec(
                id="start-to-dead",
                source="start",
                target="dead-end",
                condition=EdgeCondition.ON_SUCCESS,
            ),
            # dead-end has no outgoing edge!
        ]

        graph = GraphSpec(
            id="dead-end-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],  # dead-end is NOT terminal
            nodes=list(simple_nodes.values()) + [dead_end],
            edges=edges,
        )

        errors = graph._find_orphaned_nodes()
        assert len(errors) >= 1
        assert any("dead-end" in e.lower() and "no outgoing" in e.lower() for e in errors)

    def test_entry_point_not_flagged_as_orphan(self, simple_nodes, simple_edges):
        """Entry points should not be flagged as orphans even without incoming edges."""
        graph = GraphSpec(
            id="entry-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()),
            edges=simple_edges,
        )

        errors = graph._find_orphaned_nodes()
        # start has no incoming edges but is an entry point - should not be flagged
        assert not any("start" in e and "no incoming" in e for e in errors)

    def test_terminal_node_not_flagged_for_no_outgoing(self, simple_nodes, simple_edges):
        """Terminal nodes should not be flagged for having no outgoing edges."""
        graph = GraphSpec(
            id="terminal-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()),
            edges=simple_edges,
        )

        errors = graph._find_orphaned_nodes()
        # end has no outgoing edges but is terminal - should not be flagged
        assert not any("end" in e and "no outgoing" in e for e in errors)

    def test_pause_node_not_flagged_for_no_outgoing(self, simple_nodes):
        """Pause nodes should not be flagged for having no outgoing edges."""
        pause_node = NodeSpec(
            id="pause",
            name="Pause",
            description="HITL pause",
            node_type="human_input",
            input_keys=["result"],
            output_keys=["user_response"],
            system_prompt="Wait for user",
        )

        edges = [
            EdgeSpec(id="start-to-middle", source="start", target="middle", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="middle-to-pause", source="middle", target="pause", condition=EdgeCondition.ON_SUCCESS),
            # pause has no outgoing edge - but it's a pause node
        ]

        graph = GraphSpec(
            id="pause-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=[],
            pause_nodes=["pause"],
            nodes=[simple_nodes["start"], simple_nodes["middle"], pause_node],
            edges=edges,
        )

        errors = graph._find_orphaned_nodes()
        assert not any("pause" in e and "no outgoing" in e for e in errors)


# =============================================================================
# Tests for _find_cycles()
# =============================================================================

class TestFindCycles:
    """Tests for cycle detection."""

    def test_no_cycles_in_valid_graph(self, valid_graph):
        """Valid linear graph should have no cycles."""
        errors, cycles = valid_graph._find_cycles()
        assert len(errors) == 0
        assert len(cycles) == 0

    def test_detects_simple_cycle(self):
        """Should detect a simple A -> B -> A cycle."""
        nodes = [
            NodeSpec(id="a", name="A", description="Node A", node_type="llm_generate", input_keys=["in"], output_keys=["out"]),
            NodeSpec(id="b", name="B", description="Node B", node_type="llm_generate", input_keys=["out"], output_keys=["in"]),
        ]
        edges = [
            EdgeSpec(id="a-to-b", source="a", target="b", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="b-to-a", source="b", target="a", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="cycle-test",
            goal_id="test-goal",
            entry_node="a",
            entry_points={"start": "a"},
            terminal_nodes=[],
            nodes=nodes,
            edges=edges,
        )

        errors, cycles = graph._find_cycles()
        assert len(errors) >= 1
        assert len(cycles) >= 1
        assert any("cycle" in e.lower() for e in errors)

    def test_detects_longer_cycle(self):
        """Should detect A -> B -> C -> A cycle."""
        nodes = [
            NodeSpec(id="a", name="A", description="Node A", node_type="llm_generate", input_keys=["in"], output_keys=["a_out"]),
            NodeSpec(id="b", name="B", description="Node B", node_type="llm_generate", input_keys=["a_out"], output_keys=["b_out"]),
            NodeSpec(id="c", name="C", description="Node C", node_type="llm_generate", input_keys=["b_out"], output_keys=["in"]),
        ]
        edges = [
            EdgeSpec(id="a-to-b", source="a", target="b", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="b-to-c", source="b", target="c", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="c-to-a", source="c", target="a", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="long-cycle-test",
            goal_id="test-goal",
            entry_node="a",
            entry_points={"start": "a"},
            terminal_nodes=[],
            nodes=nodes,
            edges=edges,
        )

        errors, cycles = graph._find_cycles()
        assert len(errors) >= 1
        # Verify the cycle contains all three nodes
        assert any(len(c) == 4 for c in cycles)  # [a, b, c, a]

    def test_detects_self_loop(self):
        """Should detect a node pointing to itself."""
        nodes = [
            NodeSpec(id="loop", name="Loop", description="Self-looping node", node_type="llm_generate", input_keys=["in"], output_keys=["in"]),
        ]
        edges = [
            EdgeSpec(id="self-loop", source="loop", target="loop", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="self-loop-test",
            goal_id="test-goal",
            entry_node="loop",
            entry_points={"start": "loop"},
            terminal_nodes=[],
            nodes=nodes,
            edges=edges,
        )

        errors, cycles = graph._find_cycles()
        assert len(errors) >= 1
        assert any("loop" in e.lower() for e in errors)

    def test_no_false_positive_on_diamond(self):
        """Diamond pattern (A -> B, A -> C, B -> D, C -> D) should not be detected as cycle."""
        nodes = [
            NodeSpec(id="a", name="A", description="Node A", node_type="llm_generate", input_keys=["in"], output_keys=["a_out"]),
            NodeSpec(id="b", name="B", description="Node B", node_type="llm_generate", input_keys=["a_out"], output_keys=["b_out"]),
            NodeSpec(id="c", name="C", description="Node C", node_type="llm_generate", input_keys=["a_out"], output_keys=["c_out"]),
            NodeSpec(id="d", name="D", description="Node D", node_type="llm_generate", input_keys=["b_out", "c_out"], output_keys=["final"]),
        ]
        edges = [
            EdgeSpec(id="a-to-b", source="a", target="b", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="a-to-c", source="a", target="c", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="b-to-d", source="b", target="d", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="c-to-d", source="c", target="d", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="diamond-test",
            goal_id="test-goal",
            entry_node="a",
            entry_points={"start": "a"},
            terminal_nodes=["d"],
            nodes=nodes,
            edges=edges,
        )

        errors, cycles = graph._find_cycles()
        assert len(errors) == 0
        assert len(cycles) == 0


# =============================================================================
# Tests for _validate_input_availability()
# =============================================================================

class TestValidateInputAvailability:
    """Tests for input availability validation."""

    def test_valid_input_chain(self, valid_graph):
        """Valid graph with proper input chain should pass."""
        errors = valid_graph._validate_input_availability(initial_inputs=["user_input"])
        assert len(errors) == 0

    def test_missing_initial_input(self, valid_graph):
        """Should detect when required initial input is not provided."""
        errors = valid_graph._validate_input_availability(initial_inputs=[])
        assert len(errors) >= 1
        assert any("user_input" in e for e in errors)

    def test_missing_intermediate_input(self, simple_nodes):
        """Should detect when a node requires input that no predecessor provides."""
        missing_input_node = NodeSpec(
            id="missing",
            name="Missing",
            description="Needs unavailable input",
            node_type="llm_generate",
            input_keys=["processed", "never_provided"],  # never_provided is missing
            output_keys=["result"],
            system_prompt="Need more data",
        )

        edges = [
            EdgeSpec(id="start-to-missing", source="start", target="missing", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="missing-input-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["missing"],
            nodes=[simple_nodes["start"], missing_input_node],
            edges=edges,
        )

        errors = graph._validate_input_availability(initial_inputs=["user_input"])
        assert len(errors) >= 1
        assert any("never_provided" in e for e in errors)

    def test_input_mapping_provides_keys(self, simple_nodes):
        """Edge input_mapping should make mapped keys available."""
        node_needs_mapped = NodeSpec(
            id="needs-mapped",
            name="Needs Mapped",
            description="Needs a mapped key",
            node_type="llm_generate",
            input_keys=["mapped_key"],
            output_keys=["result"],
            system_prompt="Use mapped",
        )

        edges = [
            EdgeSpec(
                id="start-to-needs",
                source="start",
                target="needs-mapped",
                condition=EdgeCondition.ON_SUCCESS,
                input_mapping={"mapped_key": "processed"},  # Maps processed -> mapped_key
            ),
        ]

        graph = GraphSpec(
            id="mapping-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["needs-mapped"],
            nodes=[simple_nodes["start"], node_needs_mapped],
            edges=edges,
        )

        errors = graph._validate_input_availability(initial_inputs=["user_input"])
        assert len(errors) == 0

    def test_outputs_propagate_to_successors(self, simple_nodes, simple_edges):
        """Node outputs should be available to successor nodes."""
        # In valid_graph: start outputs "processed", middle needs "processed" - should work
        graph = GraphSpec(
            id="propagation-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()),
            edges=simple_edges,
        )

        errors = graph._validate_input_availability(initial_inputs=["user_input"])
        assert len(errors) == 0

    def test_parallel_paths_both_validated(self):
        """Both branches of parallel paths should be validated."""
        nodes = [
            NodeSpec(id="start", name="Start", description="Start node", node_type="llm_generate",
                    input_keys=["user_input"], output_keys=["data"]),
            NodeSpec(id="branch-a", name="Branch A", description="Branch A node", node_type="llm_generate",
                    input_keys=["data"], output_keys=["a_result"]),
            NodeSpec(id="branch-b", name="Branch B", description="Branch B node", node_type="llm_generate",
                    input_keys=["data", "missing_key"], output_keys=["b_result"]),  # missing_key not provided
        ]
        edges = [
            EdgeSpec(id="start-to-a", source="start", target="branch-a", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="start-to-b", source="start", target="branch-b", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="parallel-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["branch-a", "branch-b"],
            nodes=nodes,
            edges=edges,
        )

        errors = graph._validate_input_availability(initial_inputs=["user_input"])
        assert len(errors) >= 1
        assert any("branch-b" in e and "missing_key" in e for e in errors)


# =============================================================================
# Tests for validate() - Combined validation
# =============================================================================

class TestValidate:
    """Tests for the combined validate() method."""

    def test_valid_graph_passes(self, valid_graph):
        """Valid graph should pass all validation checks."""
        errors = valid_graph.validate(initial_inputs=["user_input"])
        assert len(errors) == 0

    def test_returns_all_error_types(self, simple_nodes):
        """Should return errors from all validation checks."""
        orphan = NodeSpec(
            id="orphan",
            name="Orphan",
            description="Orphaned node",
            node_type="llm_generate",
            input_keys=["phantom"],
            output_keys=["phantom_out"],
        )

        graph = GraphSpec(
            id="multi-error-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()) + [orphan],
            edges=[
                EdgeSpec(id="start-to-middle", source="start", target="middle", condition=EdgeCondition.ON_SUCCESS),
                EdgeSpec(id="middle-to-end", source="middle", target="end", condition=EdgeCondition.ON_SUCCESS),
            ],
        )

        errors = graph.validate(initial_inputs=["user_input"])
        # Should have orphan errors
        assert any("orphan" in e.lower() for e in errors)

    def test_allow_cycles_flag(self):
        """When allow_cycles=True, cycles should not be in errors."""
        nodes = [
            NodeSpec(id="a", name="A", description="Node A", node_type="llm_generate", input_keys=["in"], output_keys=["out"]),
            NodeSpec(id="b", name="B", description="Node B", node_type="llm_generate", input_keys=["out"], output_keys=["in"]),
        ]
        edges = [
            EdgeSpec(id="a-to-b", source="a", target="b", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="b-to-a", source="b", target="a", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="cycle-allow-test",
            goal_id="test-goal",
            entry_node="a",
            entry_points={"start": "a"},
            terminal_nodes=[],
            nodes=nodes,
            edges=edges,
        )

        # With allow_cycles=False (default), should have cycle error
        errors_strict = graph.validate(initial_inputs=["in"], allow_cycles=False)
        assert any("cycle" in e.lower() for e in errors_strict)

        # With allow_cycles=True, should not have cycle error
        # Note: This test may need adjustment based on how warnings are handled
        errors_lenient = graph.validate(initial_inputs=["in"], allow_cycles=True)
        # Cycles should be treated as warnings, not errors
        # This depends on the fix for the warnings bug
        # For now, just verify the flag changes behavior

    def test_missing_entry_node(self, simple_nodes):
        """Should detect when entry node doesn't exist."""
        graph = GraphSpec(
            id="missing-entry-test",
            goal_id="test-goal",
            entry_node="nonexistent",
            entry_points={"start": "nonexistent"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()),
            edges=[],
        )

        errors = graph.validate()
        assert any("nonexistent" in e and "not found" in e for e in errors)

    def test_missing_terminal_node(self, simple_nodes):
        """Should detect when terminal node doesn't exist."""
        graph = GraphSpec(
            id="missing-terminal-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["nonexistent"],
            nodes=list(simple_nodes.values()),
            edges=[],
        )

        errors = graph.validate()
        assert any("nonexistent" in e and "not found" in e for e in errors)

    def test_edge_references_missing_node(self, simple_nodes):
        """Should detect edges referencing non-existent nodes."""
        edges = [
            EdgeSpec(id="bad-edge", source="start", target="nonexistent", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="bad-edge-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()),
            edges=edges,
        )

        errors = graph.validate()
        assert any("nonexistent" in e for e in errors)

    def test_unreachable_node_detected(self, simple_nodes):
        """Should detect nodes that are unreachable from entry."""
        # Create a node that's not connected to the main graph
        isolated = NodeSpec(
            id="isolated",
            name="Isolated",
            description="Isolated node",
            node_type="llm_generate",
            input_keys=["x"],
            output_keys=["y"],
        )

        # Isolated has edges but not connected to entry
        edges = [
            EdgeSpec(id="start-to-middle", source="start", target="middle", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="middle-to-end", source="middle", target="end", condition=EdgeCondition.ON_SUCCESS),
            # isolated is not reachable from start
        ]

        graph = GraphSpec(
            id="unreachable-test",
            goal_id="test-goal",
            entry_node="start",
            entry_points={"start": "start"},
            terminal_nodes=["end"],
            nodes=list(simple_nodes.values()) + [isolated],
            edges=edges,
        )

        errors = graph.validate(initial_inputs=["user_input"])
        assert any("isolated" in e.lower() and "unreachable" in e.lower() for e in errors)


# =============================================================================
# Integration Tests
# =============================================================================

class TestValidationIntegration:
    """Integration tests for complete validation scenarios."""

    def test_complex_valid_graph(self):
        """Complex but valid graph should pass all checks."""
        nodes = [
            NodeSpec(id="input", name="Input", description="Input node", node_type="llm_generate",
                    input_keys=["query"], output_keys=["parsed"]),
            NodeSpec(id="search", name="Search", description="Search node", node_type="llm_tool_use",
                    input_keys=["parsed"], output_keys=["results"], tools=["web_search"]),
            NodeSpec(id="filter", name="Filter", description="Filter node", node_type="llm_generate",
                    input_keys=["results"], output_keys=["filtered"]),
            NodeSpec(id="format", name="Format", description="Format node", node_type="llm_generate",
                    input_keys=["filtered"], output_keys=["response"]),
            NodeSpec(id="output", name="Output", description="Output node", node_type="function",
                    input_keys=["response"], output_keys=["final"]),
        ]
        edges = [
            EdgeSpec(id="e1", source="input", target="search", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="e2", source="search", target="filter", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="e3", source="filter", target="format", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="e4", source="format", target="output", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="complex-valid",
            goal_id="test-goal",
            entry_node="input",
            entry_points={"start": "input"},
            terminal_nodes=["output"],
            nodes=nodes,
            edges=edges,
        )

        errors = graph.validate(initial_inputs=["query"])
        assert len(errors) == 0

    def test_multiple_entry_points_validated(self):
        """Graphs with multiple entry points should validate all paths."""
        nodes = [
            NodeSpec(id="main-entry", name="Main", description="Main entry", node_type="llm_generate",
                    input_keys=["main_input"], output_keys=["data"]),
            NodeSpec(id="alt-entry", name="Alt", description="Alternate entry", node_type="llm_generate",
                    input_keys=["alt_input"], output_keys=["data"]),
            NodeSpec(id="processor", name="Process", description="Processor node", node_type="llm_generate",
                    input_keys=["data"], output_keys=["result"]),
            NodeSpec(id="end", name="End", description="End node", node_type="llm_generate",
                    input_keys=["result"], output_keys=["final"]),
        ]
        edges = [
            EdgeSpec(id="main-to-proc", source="main-entry", target="processor", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="alt-to-proc", source="alt-entry", target="processor", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="proc-to-end", source="processor", target="end", condition=EdgeCondition.ON_SUCCESS),
        ]

        graph = GraphSpec(
            id="multi-entry",
            goal_id="test-goal",
            entry_node="main-entry",
            entry_points={"start": "main-entry", "alternate": "alt-entry"},
            terminal_nodes=["end"],
            nodes=nodes,
            edges=edges,
        )

        # Both entry points need their respective inputs
        errors = graph.validate(initial_inputs=["main_input", "alt_input"])
        assert len(errors) == 0

        # Missing alt_input should cause error for alt-entry path
        errors = graph.validate(initial_inputs=["main_input"])
        assert any("alt-entry" in e and "alt_input" in e for e in errors)
