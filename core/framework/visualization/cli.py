"""CLI commands for the ``hive visualize`` feature.

Registers the ``visualize`` subcommand that generates Mermaid.js flowcharts
from exported agent graphs.

Usage examples:
    hive visualize exports/my_agent
    hive visualize exports/my_agent --format html --output graph.html
    hive visualize exports/my_agent --format mermaid --output graph.mmd
    hive visualize exports/my_agent --direction LR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def register_visualize_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    """Register the ``visualize`` subcommand with the main CLI.

    Args:
        subparsers: The subparser group from the main argument parser.
    """
    vis_parser = subparsers.add_parser(
        "visualize",
        help="Generate Mermaid.js graph of an agent",
        description=(
            "Visualize an agent's execution graph as a Mermaid.js flowchart. "
            "Outputs raw Mermaid syntax to stdout by default, or exports "
            "an interactive HTML file."
        ),
    )
    vis_parser.add_argument(
        "agent_path",
        type=str,
        help="Path to agent folder (containing agent.py or agent.json)",
    )
    vis_parser.add_argument(
        "--format",
        "-F",
        choices=["mermaid", "html", "json"],
        default="mermaid",
        help=(
            "Output format: 'mermaid' (raw syntax, default), "
            "'html' (interactive viewer), or 'json' (graph stats)"
        ),
    )
    vis_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
    )
    vis_parser.add_argument(
        "--direction",
        "-d",
        choices=["TB", "LR", "BT", "RL"],
        default="TB",
        help="Graph layout direction (default: TB = top-to-bottom)",
    )
    vis_parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Custom title for the graph (defaults to agent id)",
    )
    vis_parser.set_defaults(func=cmd_visualize)


def _load_graph_only(agent_path: Path) -> "GraphSpec":
    """Load a GraphSpec from an agent folder without credential validation.

    This extracts only the graph topology (nodes, edges, entry/terminal
    nodes) from an agent module or agent.json. Unlike AgentRunner.load(),
    it does **not** spin up MCP servers or validate API keys — visualization
    only needs the static structure.

    Args:
        agent_path: Path to the agent folder.

    Returns:
        The loaded GraphSpec.

    Raises:
        FileNotFoundError: If no agent.py or agent.json is found.
        ValueError: If required attributes are missing from agent.py.
    """
    from framework.graph.edge import GraphSpec
    from framework.runner.runner import AgentRunner, load_agent_export

    agent_py = agent_path / "agent.py"
    agent_json = agent_path / "agent.json"

    if agent_py.exists():
        # Import the module and extract graph attributes directly.
        agent_module = AgentRunner._import_agent_module(agent_path)

        goal = getattr(agent_module, "goal", None)
        nodes = getattr(agent_module, "nodes", None)
        edges = getattr(agent_module, "edges", None)

        if goal is None or nodes is None or edges is None:
            raise ValueError(
                f"Agent at {agent_path} must define 'goal', 'nodes', "
                f"and 'edges' in agent.py"
            )

        return GraphSpec(
            id=f"{agent_path.name}-graph",
            goal_id=goal.id,
            version="1.0.0",
            entry_node=getattr(agent_module, "entry_node", nodes[0].id),
            entry_points=getattr(agent_module, "entry_points", {}),
            async_entry_points=getattr(agent_module, "async_entry_points", []),
            terminal_nodes=getattr(agent_module, "terminal_nodes", []),
            pause_nodes=getattr(agent_module, "pause_nodes", []),
            nodes=nodes,
            edges=edges,
            description=getattr(goal, "description", ""),
        )

    if agent_json.exists():
        graph, _ = load_agent_export(agent_json.read_text())
        return graph

    raise FileNotFoundError(
        f"No agent.py or agent.json found in {agent_path}"
    )


def cmd_visualize(args: argparse.Namespace) -> int:
    """Execute the ``hive visualize`` command.

    Loads the agent graph structure (without credential validation) and
    renders it in the requested format.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    from framework.visualization.mermaid_renderer import MermaidRenderer

    agent_path = Path(args.agent_path)
    if not agent_path.exists():
        print(f"Error: Agent path '{agent_path}' does not exist.", file=sys.stderr)
        return 1

    # Load the graph structure only — no API keys or MCP servers needed.
    try:
        graph = _load_graph_only(agent_path)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error loading agent graph: {exc}", file=sys.stderr)
        return 1

    renderer = MermaidRenderer(
        graph=graph,
        title=args.title,
        direction=args.direction,
    )

    output_format: str = args.format

    if output_format == "mermaid":
        content = renderer.render()
        if args.output:
            renderer.export_mermaid(args.output)
            print(f"✓ Mermaid syntax written to {args.output}")
        else:
            print(content)

    elif output_format == "html":
        output_path = args.output or f"{agent_path.name}_graph.html"
        renderer.export_html(output_path)
        print(f"✓ Interactive HTML written to {output_path}")
        print(f"  Open in browser: file://{Path(output_path).resolve()}")

    elif output_format == "json":
        stats = renderer.get_graph_stats()
        content = json.dumps(stats, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
            print(f"✓ Graph stats written to {args.output}")
        else:
            print(content)

    return 0
