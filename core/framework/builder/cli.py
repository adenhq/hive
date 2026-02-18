import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:
    console = None

def load_graph_file(path_str: str) -> dict[str, Any]:
    """Load a graph definition from a JSON file."""
    path = Path(path_str)
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file: {path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        sys.exit(1)

def diff_graphs(graph_a: dict, graph_b: dict) -> dict[str, Any]:
    """Compare two graph dictionaries and return the differences."""
    
    # 1. Compare Nodes
    nodes_a = {n["id"]: n for n in graph_a.get("nodes", [])}
    nodes_b = {n["id"]: n for n in graph_b.get("nodes", [])}
    
    added_nodes = [n for nid, n in nodes_b.items() if nid not in nodes_a]
    removed_nodes = [n for nid, n in nodes_a.items() if nid not in nodes_b]
    
    modified_nodes = []
    for nid, node_b in nodes_b.items():
        if nid in nodes_a:
            node_a = nodes_a[nid]
            changes = []
            if node_a.get("type") != node_b.get("type"):
                changes.append(f"Type: {node_a.get('type')} -> {node_b.get('type')}")
            if node_a.get("description") != node_b.get("description"):
                changes.append("Description updated")
            if node_a.get("instructions") != node_b.get("instructions"):
                changes.append("Instructions updated")
                
            if changes:
                modified_nodes.append({"id": nid, "changes": changes})

    # 2. Compare Edges
    edges_a = {(e["source"], e["target"]): e for e in graph_a.get("edges", [])}
    edges_b = {(e["source"], e["target"]): e for e in graph_b.get("edges", [])}
    
    added_edges = [e for sig, e in edges_b.items() if sig not in edges_a]
    removed_edges = [e for sig, e in edges_a.items() if sig not in edges_b]

    return {
        "nodes": {
            "added": added_nodes,
            "removed": removed_nodes,
            "modified": modified_nodes
        },
        "edges": {
            "added": added_edges,
            "removed": removed_edges
        }
    }

def print_diff(diff: dict):
    """Print the diff report."""
    if console:
        console.print("\n[bold cyan]Hive Graph Diff[/bold cyan]")
        
        if diff["nodes"]["added"]:
            console.print("\n[green]++ Added Nodes:[/green]")
            for n in diff["nodes"]["added"]:
                console.print(f"  + [bold]{n['id']}[/bold] ({n.get('type', 'unknown')})")
        
        if diff["nodes"]["removed"]:
            console.print("\n[red]-- Removed Nodes:[/red]")
            for n in diff["nodes"]["removed"]:
                console.print(f"  - [bold]{n['id']}[/bold]")
                
        if diff["nodes"]["modified"]:
            console.print("\n[yellow]~~ Modified Nodes:[/yellow]")
            for n in diff["nodes"]["modified"]:
                console.print(f"  ~ [bold]{n['id']}[/bold]: {', '.join(n['changes'])}")

        if diff["edges"]["added"]:
            console.print("\n[green]++ Added Edges:[/green]")
            for e in diff["edges"]["added"]:
                console.print(f"  + {e['source']} -> {e['target']}")
                
        if diff["edges"]["removed"]:
            console.print("\n[red]-- Removed Edges:[/red]")
            for e in diff["edges"]["removed"]:
                console.print(f"  - {e['source']} -> {e['target']}")

        if not any([diff["nodes"]["added"], diff["nodes"]["removed"], diff["nodes"]["modified"], 
                   diff["edges"]["added"], diff["edges"]["removed"]]):
            console.print("\n[bold green]No differences found. Graphs are identical.[/bold green]")
            
    else:
        print("\n=== Hive Graph Diff ===")
        for n in diff["nodes"]["added"]:
            print(f"+ Node: {n['id']}")
        for n in diff["nodes"]["removed"]:
            print(f"- Node: {n['id']}")
        for n in diff["nodes"]["modified"]:
            print(f"~ Node: {n['id']} ({', '.join(n['changes'])})")
        for e in diff["edges"]["added"]:
            print(f"+ Edge: {e['source']} -> {e['target']}")
        for e in diff["edges"]["removed"]:
            print(f"- Edge: {e['source']} -> {e['target']}")

def diff_command(args):
    """Entry point for the diff command."""
    graph_a = load_graph_file(args.file_a)
    graph_b = load_graph_file(args.file_b)
    
    diff = diff_graphs(graph_a, graph_b)
    print_diff(diff)

def register_builder_commands(subparsers):
    """Register builder commands with the main CLI."""
    parser = subparsers.add_parser("diff", help="Compare two agent graph definitions")
    parser.add_argument("file_a", help="Path to the first graph JSON file")
    parser.add_argument("file_b", help="Path to the second graph JSON file")
    parser.set_defaults(func=diff_command)