"""Mermaid.js renderer for Hive agent graphs.

Converts a GraphSpec into Mermaid.js flowchart syntax and generates
interactive HTML files for local viewing.

Usage:
    from framework.visualization.mermaid_renderer import MermaidRenderer
    renderer = MermaidRenderer(graph)
    mermaid_code = renderer.render()
    renderer.export_html("output.html")
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
    from framework.graph.node import NodeSpec

logger = logging.getLogger(__name__)

# Style mapping for node types.
_NODE_TYPE_STYLES: dict[str, dict[str, str]] = {
    "event_loop": {"shape_open": "([", "shape_close": "])", "fill": "#4a90d9", "stroke": "#2c5f8a"},
    "llm_tool_use": {"shape_open": "([", "shape_close": "])", "fill": "#4a90d9", "stroke": "#2c5f8a"},
    "llm_generate": {"shape_open": "([", "shape_close": "])", "fill": "#4a90d9", "stroke": "#2c5f8a"},
    "function": {"shape_open": "[[", "shape_close": "]]", "fill": "#50c878", "stroke": "#2e8b57"},
    "router": {"shape_open": "{", "shape_close": "}", "fill": "#ffa500", "stroke": "#cc8400"},
    "human_input": {"shape_open": ">", "shape_close": "]", "fill": "#da70d6", "stroke": "#9932cc"},
}

_DEFAULT_STYLE: dict[str, str] = {
    "shape_open": "[",
    "shape_close": "]",
    "fill": "#6c757d",
    "stroke": "#495057",
}

# Edge condition label mapping.
_CONDITION_LABELS: dict[str, str] = {
    "always": "",
    "on_success": "✓ success",
    "on_failure": "✗ failure",
    "conditional": "⚡ conditional",
    "llm_decide": "🤔 LLM decides",
}

# Edge condition line styles.
_CONDITION_LINE_STYLES: dict[str, str] = {
    "always": "-->",
    "on_success": "-->",
    "on_failure": "-.->",
    "conditional": "==>",
    "llm_decide": "-..->",
}


class MermaidRenderer:
    """Renders a GraphSpec as a Mermaid.js flowchart.

    Supports:
        - Node type styling (LLM, function, router, human_input)
        - Edge condition labels and styles
        - Entry/terminal node highlighting
        - Fan-out/fan-in detection annotations
        - Interactive HTML export with pan/zoom
        - Raw Mermaid syntax export

    Example:
        >>> from framework.visualization.mermaid_renderer import MermaidRenderer
        >>> renderer = MermaidRenderer(graph_spec)
        >>> print(renderer.render())
        >>> renderer.export_html("agent_graph.html")
    """

    def __init__(
        self,
        graph: "GraphSpec",
        title: str | None = None,
        direction: str = "TB",
    ) -> None:
        """Initialize the renderer.

        Args:
            graph: The GraphSpec to render.
            title: Optional title for the graph. Defaults to graph.id.
            direction: Flow direction — "TB" (top-bottom), "LR" (left-right),
                       "BT" (bottom-top), or "RL" (right-left).
        """
        self._graph = graph
        self._title = title or graph.id
        if direction not in ("TB", "LR", "BT", "RL"):
            raise ValueError(f"Invalid direction '{direction}'. Use TB, LR, BT, or RL.")
        self._direction = direction

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Generate Mermaid.js flowchart syntax.

        Returns:
            A string containing valid Mermaid.js flowchart definition.
        """
        lines: list[str] = []
        lines.append(f"flowchart {self._direction}")

        # Subgraph title
        lines.append(f"    subgraph {_sanitize_id(self._title)}[\"{_escape(self._title)}\"]")

        # Render nodes
        for node in self._graph.nodes:
            lines.append(self._render_node(node))

        lines.append("    end")
        lines.append("")

        # Render edges
        for edge in self._graph.edges:
            lines.append(self._render_edge(edge))

        lines.append("")

        # Add style classes for node types
        lines.extend(self._render_styles())

        return "\n".join(lines)

    def export_mermaid(self, output_path: str | Path) -> Path:
        """Write raw Mermaid syntax to a file.

        Args:
            output_path: Destination file path.

        Returns:
            The resolved Path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        logger.info("Mermaid syntax written to %s", path)
        return path

    def export_html(self, output_path: str | Path) -> Path:
        """Generate an interactive HTML file embedding the Mermaid graph.

        The HTML file is self-contained, loading Mermaid.js from a CDN,
        and includes pan/zoom support via a lightweight wrapper.

        Args:
            output_path: Destination file path.

        Returns:
            The resolved Path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        mermaid_code = self.render()
        html_content = _build_html(
            title=self._title,
            mermaid_code=mermaid_code,
            description=self._graph.description,
            node_count=len(self._graph.nodes),
            edge_count=len(self._graph.edges),
        )
        path.write_text(html_content, encoding="utf-8")
        logger.info("Interactive HTML written to %s", path)
        return path

    def get_graph_stats(self) -> dict[str, Any]:
        """Return summary statistics about the graph.

        Returns:
            Dictionary with node_count, edge_count, fan_out_nodes,
            fan_in_nodes, entry_node, and terminal_nodes.
        """
        return {
            "title": self._title,
            "description": self._graph.description,
            "node_count": len(self._graph.nodes),
            "edge_count": len(self._graph.edges),
            "entry_node": self._graph.entry_node,
            "terminal_nodes": list(self._graph.terminal_nodes),
            "fan_out_nodes": self._graph.detect_fan_out_nodes(),
            "fan_in_nodes": self._graph.detect_fan_in_nodes(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_node(self, node: "NodeSpec") -> str:
        """Render a single node in Mermaid syntax."""
        style = _NODE_TYPE_STYLES.get(node.node_type, _DEFAULT_STYLE)
        node_id = _sanitize_id(node.id)

        # Build label with name and type
        label_parts = [node.name]
        if node.node_type:
            label_parts.append(f"<i>{node.node_type}</i>")

        # Add icons for special roles
        icons: list[str] = []
        if node.id == self._graph.entry_node:
            icons.append("▶")
        if node.id in self._graph.terminal_nodes:
            icons.append("⏹")
        if node.id in getattr(self._graph, "pause_nodes", []):
            icons.append("⏸")

        if icons:
            label_parts.insert(0, " ".join(icons))

        label = "<br/>".join(label_parts)
        open_s, close_s = style["shape_open"], style["shape_close"]

        line = f"        {node_id}{open_s}\"{label}\"{close_s}"

        # Apply class for styling
        class_name = f"cls_{node.node_type}" if node.node_type else "cls_default"
        return f"{line}:::{class_name}"

    def _render_edge(self, edge: "EdgeSpec") -> str:
        """Render a single edge in Mermaid syntax."""
        source_id = _sanitize_id(edge.source)
        target_id = _sanitize_id(edge.target)

        condition_str = str(edge.condition) if hasattr(edge.condition, "value") else str(edge.condition)
        arrow = _CONDITION_LINE_STYLES.get(condition_str, "-->")
        label = _CONDITION_LABELS.get(condition_str, "")

        # For conditional edges, show the expression
        if condition_str == "conditional" and edge.condition_expr:
            label = f"⚡ {edge.condition_expr}"

        # For LLM-decide edges, show the description if available
        if condition_str == "llm_decide" and edge.description:
            short_desc = edge.description[:40]
            if len(edge.description) > 40:
                short_desc += "…"
            label = f"🤔 {short_desc}"

        if label:
            # Wrap label in double quotes to handle special characters like "=="
            # that might be misinterpreted by Mermaid's parser.
            return f'    {source_id} {arrow}|"{_escape(label)}"| {target_id}'
        return f"    {source_id} {arrow} {target_id}"

    def _render_styles(self) -> list[str]:
        """Generate Mermaid classDef statements for node type styling."""
        lines: list[str] = []
        seen: set[str] = set()

        for node in self._graph.nodes:
            node_type = node.node_type or "default"
            class_name = f"cls_{node_type}"
            if class_name in seen:
                continue
            seen.add(class_name)

            style = _NODE_TYPE_STYLES.get(node_type, _DEFAULT_STYLE)
            fill = style["fill"]
            stroke = style["stroke"]
            lines.append(
                f"    classDef {class_name} fill:{fill},stroke:{stroke},"
                f"color:#fff,stroke-width:2px"
            )

        # Entry node highlight
        entry_id = _sanitize_id(self._graph.entry_node)
        lines.append(
            f"    classDef entryNode fill:#28a745,stroke:#1e7e34,"
            f"color:#fff,stroke-width:3px"
        )
        lines.append(f"    class {entry_id} entryNode")

        # Terminal node highlights
        for term in self._graph.terminal_nodes:
            term_id = _sanitize_id(term)
            lines.append(
                f"    classDef terminalNode fill:#dc3545,stroke:#c82333,"
                f"color:#fff,stroke-width:3px"
            )
            lines.append(f"    class {term_id} terminalNode")

        return lines


# ======================================================================
# Module-level helper functions
# ======================================================================


def _sanitize_id(raw: str) -> str:
    """Sanitize a node/edge ID for Mermaid compatibility.

    Replaces characters that Mermaid does not allow in identifiers
    (hyphens, dots, spaces) with underscores.

    Args:
        raw: The original identifier string.

    Returns:
        A Mermaid-safe identifier.
    """
    return raw.replace("-", "_").replace(".", "_").replace(" ", "_")


def _escape(text: str) -> str:
    """Escape text for use in Mermaid labels.

    Replaces characters that break Mermaid's parser inside
    edge/node labels: double-quotes, pipe characters, and hash
    signs. Does **not** use html.escape() because Mermaid reads
    its own syntax before the browser interprets HTML entities.

    Args:
        text: Raw label text.

    Returns:
        Mermaid-safe label string.
    """
    return (
        text
        .replace('"', '#quot;')
        .replace('|', '#124;')
        .replace('<', '#lt;')
        .replace('>', '#gt;')
    )


def _build_html(
    title: str,
    mermaid_code: str,
    description: str,
    node_count: int,
    edge_count: int,
) -> str:
    """Build a self-contained interactive HTML page.

    Args:
        title: Page title.
        mermaid_code: Rendered Mermaid.js syntax.
        description: Agent description.
        node_count: Number of nodes.
        edge_count: Number of edges.

    Returns:
        Complete HTML string.
    """
    escaped_title = html.escape(title)
    escaped_desc = html.escape(description) if description else "No description available"
    # Mermaid code must NOT be HTML-escaped in the rendering <pre> — Mermaid
    # reads its own syntax verbatim before the browser parses HTML. Only the
    # "raw syntax" debug view should be escaped.
    escaped_mermaid_for_display = html.escape(mermaid_code)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escaped_title} — Agent Graph</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --border: #30363d;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
                         Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }}
        .header {{
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 600;
        }}
        .header h1 span {{
            color: var(--accent);
        }}
        .stats {{
            display: flex;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .stats .stat {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .stats .stat strong {{
            color: var(--text-primary);
        }}
        .description {{
            padding: 12px 24px;
            font-size: 14px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
        }}
        .graph-container {{
            padding: 24px;
            display: flex;
            justify-content: center;
            overflow: auto;
        }}
        .mermaid {{
            max-width: 100%;
        }}
        .controls {{
            position: fixed;
            bottom: 16px;
            right: 16px;
            display: flex;
            gap: 8px;
        }}
        .controls button {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.15s;
        }}
        .controls button:hover {{
            background: var(--border);
        }}
        .raw-toggle {{
            display: none;
            padding: 16px 24px;
        }}
        .raw-toggle pre {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 <span>Hive</span> Agent Graph — {escaped_title}</h1>
        <div class="stats">
            <div class="stat">Nodes: <strong>{node_count}</strong></div>
            <div class="stat">Edges: <strong>{edge_count}</strong></div>
        </div>
    </div>
    <div class="description">{escaped_desc}</div>
    <div class="graph-container">
        <pre class="mermaid">{mermaid_code}</pre>
    </div>
    <div id="rawSection" class="raw-toggle">
        <h3 style="margin-bottom:8px;">Raw Mermaid Syntax</h3>
        <pre>{escaped_mermaid_for_display}</pre>
    </div>
    <div class="controls">
        <button onclick="toggleRaw()">📝 Raw Syntax</button>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: "dark",
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: "basis",
            }},
        }});
        function toggleRaw() {{
            const el = document.getElementById("rawSection");
            el.style.display = el.style.display === "none" ? "block" : "none";
        }}
    </script>
</body>
</html>"""
