"""Tests for the visualization module (Mermaid.js renderer).

Covers:
    - MermaidRenderer.render() output correctness
    - Node type styling and shape rendering
    - Edge condition labels and arrow styles
    - Entry/terminal node highlighting
    - Fan-out and fan-in detection
    - HTML export
    - Mermaid file export
    - Graph stats
    - Edge cases (empty graphs, single node, etc.)
    - CLI argument parsing and command execution
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.node import NodeSpec
from framework.visualization.mermaid_renderer import (
    MermaidRenderer,
    _build_html,
    _escape,
    _sanitize_id,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def simple_graph() -> GraphSpec:
    """A minimal two-node graph for basic tests."""
    nodes = [
        NodeSpec(
            id="start",
            name="Start Node",
            description="Entry point",
            node_type="event_loop",
        ),
        NodeSpec(
            id="end",
            name="End Node",
            description="Terminal point",
            node_type="function",
        ),
    ]
    edges = [
        EdgeSpec(
            id="start-to-end",
            source="start",
            target="end",
            condition=EdgeCondition.ON_SUCCESS,
        ),
    ]
    return GraphSpec(
        id="test-graph",
        goal_id="test-goal",
        entry_node="start",
        terminal_nodes=["end"],
        nodes=nodes,
        edges=edges,
        description="A simple test graph",
    )


@pytest.fixture
def complex_graph() -> GraphSpec:
    """A multi-node graph with various edge conditions and node types."""
    nodes = [
        NodeSpec(id="input", name="Input Parser", description="Parse input", node_type="function"),
        NodeSpec(id="router", name="Decision Router", description="Route decisions", node_type="router"),
        NodeSpec(id="llm-proc", name="LLM Processor", description="Process with LLM", node_type="event_loop"),
        NodeSpec(id="fallback", name="Fallback Handler", description="Handle failures", node_type="function"),
        NodeSpec(id="output", name="Output Formatter", description="Format output", node_type="function"),
    ]
    edges = [
        EdgeSpec(id="e1", source="input", target="router", condition=EdgeCondition.ALWAYS),
        EdgeSpec(id="e2", source="router", target="llm-proc", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e3", source="router", target="fallback", condition=EdgeCondition.ON_FAILURE),
        EdgeSpec(
            id="e4",
            source="llm-proc",
            target="output",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output.confidence > 0.8",
        ),
        EdgeSpec(
            id="e5",
            source="llm-proc",
            target="fallback",
            condition=EdgeCondition.LLM_DECIDE,
            description="Only route to fallback if LLM deems quality insufficient",
        ),
    ]
    return GraphSpec(
        id="complex-graph",
        goal_id="complex-goal",
        entry_node="input",
        terminal_nodes=["output", "fallback"],
        nodes=nodes,
        edges=edges,
        description="A complex multi-path graph",
    )


@pytest.fixture
def fan_out_graph() -> GraphSpec:
    """A graph with fan-out (parallel branches)."""
    nodes = [
        NodeSpec(id="start", name="Start", description="Start", node_type="function"),
        NodeSpec(id="branch-a", name="Branch A", description="Branch A", node_type="event_loop"),
        NodeSpec(id="branch-b", name="Branch B", description="Branch B", node_type="event_loop"),
        NodeSpec(id="merge", name="Merge", description="Merge results", node_type="function"),
    ]
    edges = [
        EdgeSpec(id="e1", source="start", target="branch-a", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e2", source="start", target="branch-b", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e3", source="branch-a", target="merge", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e4", source="branch-b", target="merge", condition=EdgeCondition.ON_SUCCESS),
    ]
    return GraphSpec(
        id="fan-out-graph",
        goal_id="fan-out-goal",
        entry_node="start",
        terminal_nodes=["merge"],
        nodes=nodes,
        edges=edges,
    )


# ------------------------------------------------------------------
# Helper function tests
# ------------------------------------------------------------------


class TestSanitizeId:
    """Tests for the _sanitize_id helper."""

    def test_hyphens_replaced(self):
        """Hyphens should be replaced with underscores."""
        assert _sanitize_id("my-node") == "my_node"

    def test_dots_replaced(self):
        """Dots should be replaced with underscores."""
        assert _sanitize_id("my.node") == "my_node"

    def test_spaces_replaced(self):
        """Spaces should be replaced with underscores."""
        assert _sanitize_id("my node") == "my_node"

    def test_combined_replacements(self):
        """Multiple special characters should all be replaced."""
        assert _sanitize_id("my-node.v2 test") == "my_node_v2_test"

    def test_clean_id_unchanged(self):
        """IDs without special characters should pass through unchanged."""
        assert _sanitize_id("my_node") == "my_node"


class TestEscape:
    """Tests for the _escape helper."""

    def test_double_quotes_escaped(self):
        """Double quotes should be escaped for Mermaid."""
        assert _escape('"test"') == '#quot;test#quot;'

    def test_pipe_escaped(self):
        """Pipe characters should be escaped for Mermaid."""
        assert _escape("a|b") == "a#124;b"

    def test_angle_brackets_escaped(self):
        """Angle brackets should be escaped for Mermaid."""
        assert _escape("<script>") == "#lt;script#gt;"

    def test_plain_text_unchanged(self):
        """Plain text should pass through unchanged."""
        assert _escape("hello") == "hello"

    def test_single_quotes_unchanged(self):
        """Single quotes should pass through unchanged (Mermaid handles them)."""
        assert _escape("it's") == "it's"


# ------------------------------------------------------------------
# MermaidRenderer tests
# ------------------------------------------------------------------


class TestMermaidRendererInit:
    """Tests for MermaidRenderer initialization."""

    def test_default_title_from_graph(self, simple_graph):
        """Title defaults to graph.id when not specified."""
        renderer = MermaidRenderer(simple_graph)
        assert renderer._title == "test-graph"

    def test_custom_title(self, simple_graph):
        """Custom title overrides graph.id."""
        renderer = MermaidRenderer(simple_graph, title="My Custom Title")
        assert renderer._title == "My Custom Title"

    def test_default_direction(self, simple_graph):
        """Direction defaults to TB (top-to-bottom)."""
        renderer = MermaidRenderer(simple_graph)
        assert renderer._direction == "TB"

    def test_valid_directions(self, simple_graph):
        """All valid directions should be accepted."""
        for direction in ("TB", "LR", "BT", "RL"):
            renderer = MermaidRenderer(simple_graph, direction=direction)
            assert renderer._direction == direction

    def test_invalid_direction_raises(self, simple_graph):
        """Invalid direction should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            MermaidRenderer(simple_graph, direction="XX")


class TestMermaidRendererRender:
    """Tests for MermaidRenderer.render() output."""

    def test_starts_with_flowchart(self, simple_graph):
        """Output should start with a flowchart declaration."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert result.startswith("flowchart TB")

    def test_contains_subgraph(self, simple_graph):
        """Output should contain a subgraph wrapper."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "subgraph" in result
        assert "end" in result

    def test_contains_all_nodes(self, simple_graph):
        """All node IDs should appear in the output."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "start" in result
        assert "end" in result

    def test_contains_node_names(self, simple_graph):
        """Node display names should appear in the output."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "Start Node" in result
        assert "End Node" in result

    def test_contains_edges(self, simple_graph):
        """Edges should appear in the output."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        # The edge connects start -> end
        assert "start" in result
        assert "end" in result
        assert "-->" in result

    def test_entry_node_marked(self, simple_graph):
        """Entry node should have the ▶ marker."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "▶" in result

    def test_terminal_node_marked(self, simple_graph):
        """Terminal nodes should have the ⏹ marker."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "⏹" in result

    def test_node_type_class(self, simple_graph):
        """Nodes should have class annotations for styling."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "cls_event_loop" in result
        assert "cls_function" in result

    def test_entry_node_style(self, simple_graph):
        """Entry node should get the entryNode class."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "entryNode" in result

    def test_terminal_node_style(self, simple_graph):
        """Terminal nodes should get the terminalNode class."""
        renderer = MermaidRenderer(simple_graph)
        result = renderer.render()
        assert "terminalNode" in result

    def test_direction_lr(self, simple_graph):
        """LR direction should appear in the output."""
        renderer = MermaidRenderer(simple_graph, direction="LR")
        result = renderer.render()
        assert result.startswith("flowchart LR")


class TestComplexGraph:
    """Tests for complex graph rendering with various edge conditions."""

    def test_conditional_edge_label(self, complex_graph):
        """Conditional edges should show the expression in quotes."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        # Expect quoted label
        assert '"output.confidence > 0.8"' in result or 'output.confidence' in result

    def test_failure_edge_style(self, complex_graph):
        """Failure edges should use dotted arrow style."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        assert '-.->|"' in result

    def test_llm_decide_label(self, complex_graph):
        """LLM-decide edges should show 🤔 and description in quotes."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        assert '"🤔' in result

    def test_success_edge_label(self, complex_graph):
        """Success edges should show the ✓ label in quotes."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        assert '"✓ success"' in result

    def test_all_nodes_present(self, complex_graph):
        """All nodes should appear in complex graph output."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        for node in complex_graph.nodes:
            assert _sanitize_id(node.id) in result

    def test_all_edges_present(self, complex_graph):
        """All edges should connect the correct nodes."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        for edge in complex_graph.edges:
            assert _sanitize_id(edge.source) in result
            assert _sanitize_id(edge.target) in result

    def test_router_node_shape(self, complex_graph):
        """Router nodes should use diamond/rhombus shape."""
        renderer = MermaidRenderer(complex_graph)
        result = renderer.render()
        # Router uses { } shape
        assert "router{" in result or 'router{"' in result


class TestFanOutGraph:
    """Tests for fan-out/fan-in graph rendering."""

    def test_fan_out_detected(self, fan_out_graph):
        """Fan-out nodes should be detected in stats."""
        renderer = MermaidRenderer(fan_out_graph)
        stats = renderer.get_graph_stats()
        assert len(stats["fan_out_nodes"]) > 0

    def test_fan_in_detected(self, fan_out_graph):
        """Fan-in nodes should be detected in stats."""
        renderer = MermaidRenderer(fan_out_graph)
        stats = renderer.get_graph_stats()
        assert len(stats["fan_in_nodes"]) > 0

    def test_parallel_branches_rendered(self, fan_out_graph):
        """Both parallel branches should appear in the output."""
        renderer = MermaidRenderer(fan_out_graph)
        result = renderer.render()
        assert "branch_a" in result
        assert "branch_b" in result


# ------------------------------------------------------------------
# Export tests
# ------------------------------------------------------------------


class TestExportMermaid:
    """Tests for Mermaid file export."""

    def test_export_creates_file(self, simple_graph):
        """export_mermaid should create the output file."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.mmd"
            result_path = renderer.export_mermaid(output)
            assert result_path.exists()
            content = result_path.read_text()
            assert "flowchart TB" in content

    def test_export_creates_parent_dirs(self, simple_graph):
        """export_mermaid should create parent directories."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "nested" / "dir" / "test.mmd"
            result_path = renderer.export_mermaid(output)
            assert result_path.exists()


class TestExportHtml:
    """Tests for interactive HTML export."""

    def test_export_creates_file(self, simple_graph):
        """export_html should create the output file."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.html"
            result_path = renderer.export_html(output)
            assert result_path.exists()

    def test_html_contains_mermaid_script(self, simple_graph):
        """HTML output should include the Mermaid.js CDN script tag."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.html"
            renderer.export_html(output)
            content = output.read_text()
            assert "mermaid" in content
            assert "<script" in content

    def test_html_contains_graph(self, simple_graph):
        """HTML output should contain the rendered graph."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.html"
            renderer.export_html(output)
            content = output.read_text()
            assert "flowchart" in content

    def test_html_contains_title(self, simple_graph):
        """HTML output should contain the graph title."""
        renderer = MermaidRenderer(simple_graph, title="My Agent")
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.html"
            renderer.export_html(output)
            content = output.read_text()
            assert "My Agent" in content

    def test_html_dark_theme(self, simple_graph):
        """HTML output should use dark theme styling."""
        renderer = MermaidRenderer(simple_graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.html"
            renderer.export_html(output)
            content = output.read_text()
            assert "dark" in content


# ------------------------------------------------------------------
# Graph stats tests
# ------------------------------------------------------------------


class TestGetGraphStats:
    """Tests for get_graph_stats()."""

    def test_node_count(self, simple_graph):
        """Stats should report correct node count."""
        renderer = MermaidRenderer(simple_graph)
        stats = renderer.get_graph_stats()
        assert stats["node_count"] == 2

    def test_edge_count(self, simple_graph):
        """Stats should report correct edge count."""
        renderer = MermaidRenderer(simple_graph)
        stats = renderer.get_graph_stats()
        assert stats["edge_count"] == 1

    def test_entry_node(self, simple_graph):
        """Stats should report the entry node."""
        renderer = MermaidRenderer(simple_graph)
        stats = renderer.get_graph_stats()
        assert stats["entry_node"] == "start"

    def test_terminal_nodes(self, simple_graph):
        """Stats should report terminal nodes."""
        renderer = MermaidRenderer(simple_graph)
        stats = renderer.get_graph_stats()
        assert stats["terminal_nodes"] == ["end"]

    def test_title(self, simple_graph):
        """Stats should report the graph title."""
        renderer = MermaidRenderer(simple_graph, title="Custom Title")
        stats = renderer.get_graph_stats()
        assert stats["title"] == "Custom Title"

    def test_description(self, simple_graph):
        """Stats should report the graph description."""
        renderer = MermaidRenderer(simple_graph)
        stats = renderer.get_graph_stats()
        assert stats["description"] == "A simple test graph"


# ------------------------------------------------------------------
# _build_html tests
# ------------------------------------------------------------------


class TestBuildHtml:
    """Tests for the _build_html helper."""

    def test_valid_html(self):
        """Generated HTML should be valid."""
        result = _build_html(
            title="Test",
            mermaid_code="flowchart TB\n  A --> B",
            description="A test",
            node_count=2,
            edge_count=1,
        )
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_escapes_title(self):
        """Titles with HTML entities should be escaped."""
        result = _build_html(
            title="<script>alert('xss')</script>",
            mermaid_code="flowchart TB",
            description="",
            node_count=0,
            edge_count=0,
        )
        assert "<script>alert" not in result
        assert "&lt;script&gt;" in result

    def test_node_edge_counts(self):
        """Stats should appear in the HTML."""
        result = _build_html(
            title="Test",
            mermaid_code="flowchart TB",
            description="",
            node_count=5,
            edge_count=3,
        )
        assert "5" in result
        assert "3" in result


# ------------------------------------------------------------------
# Edge case tests
# ------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_single_node_no_edges(self):
        """A single node with no edges should render without errors."""
        graph = GraphSpec(
            id="single-node",
            goal_id="g1",
            entry_node="only",
            terminal_nodes=["only"],
            nodes=[NodeSpec(id="only", name="Only Node", description="The only node")],
            edges=[],
        )
        renderer = MermaidRenderer(graph)
        result = renderer.render()
        assert "only" in result
        assert "flowchart TB" in result

    def test_node_id_with_special_chars(self):
        """Node IDs with hyphens and dots should be sanitized."""
        graph = GraphSpec(
            id="special-chars",
            goal_id="g1",
            entry_node="my-node.v2",
            terminal_nodes=["my-node.v2"],
            nodes=[NodeSpec(id="my-node.v2", name="Special", description="Special chars")],
            edges=[],
        )
        renderer = MermaidRenderer(graph)
        result = renderer.render()
        assert "my_node_v2" in result

    def test_empty_description_graph(self):
        """Graph with no description should still render."""
        graph = GraphSpec(
            id="no-desc",
            goal_id="g1",
            entry_node="a",
            nodes=[NodeSpec(id="a", name="A", description="Node A")],
            edges=[],
        )
        renderer = MermaidRenderer(graph)
        stats = renderer.get_graph_stats()
        assert stats["description"] == ""


# ------------------------------------------------------------------
# CLI tests
# ------------------------------------------------------------------


class TestVisualizeCli:
    """Tests for the visualize CLI command argument parsing."""

    def test_register_commands(self):
        """register_visualize_commands should add the 'visualize' parser."""
        import argparse

        from framework.visualization.cli import register_visualize_commands

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_visualize_commands(subparsers)

        # Should parse without error
        args = parser.parse_args(["visualize", "exports/test-agent"])
        assert args.command == "visualize"
        assert args.agent_path == "exports/test-agent"
        assert args.format == "mermaid"
        assert args.direction == "TB"
        assert args.output is None

    def test_format_html_option(self):
        """--format html should be accepted."""
        import argparse

        from framework.visualization.cli import register_visualize_commands

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_visualize_commands(subparsers)

        args = parser.parse_args(["visualize", "exports/test", "--format", "html"])
        assert args.format == "html"

    def test_direction_lr_option(self):
        """--direction LR should be accepted."""
        import argparse

        from framework.visualization.cli import register_visualize_commands

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_visualize_commands(subparsers)

        args = parser.parse_args(["visualize", "exports/test", "--direction", "LR"])
        assert args.direction == "LR"

    def test_output_option(self):
        """--output should set the output path."""
        import argparse

        from framework.visualization.cli import register_visualize_commands

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_visualize_commands(subparsers)

        args = parser.parse_args(["visualize", "exports/test", "-o", "graph.html"])
        assert args.output == "graph.html"

    def test_title_option(self):
        """--title should set a custom title."""
        import argparse

        from framework.visualization.cli import register_visualize_commands

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_visualize_commands(subparsers)

        args = parser.parse_args(["visualize", "exports/test", "--title", "My Agent"])
        assert args.title == "My Agent"
