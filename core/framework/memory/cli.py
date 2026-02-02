"""CLI commands for memory inspection."""

import argparse
import json
import sys
from pathlib import Path

from framework.memory.inspector import MemoryInspector
from framework.schemas.run import RunStatus


def register_memory_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register memory inspection commands with the main CLI."""

    # memory command with subcommands
    memory_parser = subparsers.add_parser(
        "memory",
        help="Inspect agent memory and run data",
        description="View SharedMemory state and execution data from agent runs.",
    )
    
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    
    # memory inspect <agent> [run_id]
    inspect_parser = memory_subparsers.add_parser(
        "inspect",
        help="Inspect memory state for a specific run",
        description="View the final SharedMemory state and metadata for an agent run.",
    )
    inspect_parser.add_argument(
        "agent",
        type=str,
        help="Agent name (folder name in exports/ or storage path)",
    )
    inspect_parser.add_argument(
        "run_id",
        type=str,
        nargs="?",
        help="Run ID to inspect (defaults to most recent run)",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    inspect_parser.add_argument(
        "--storage-path",
        type=str,
        help="Custom storage path (default: ~/.hive/storage/{agent})",
    )
    inspect_parser.set_defaults(func=cmd_memory_inspect)
    
    # memory list <agent>
    list_parser = memory_subparsers.add_parser(
        "list",
        help="List all runs for an agent",
        description="Show all run history for an agent with summaries.",
    )
    list_parser.add_argument(
        "agent",
        type=str,
        help="Agent name (folder name in exports/ or storage path)",
    )
    list_parser.add_argument(
        "--status",
        type=str,
        choices=["running", "completed", "failed"],
        help="Filter by run status",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of runs to show (most recent first)",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    list_parser.add_argument(
        "--storage-path",
        type=str,
        help="Custom storage path (default: ~/.hive/storage/{agent})",
    )
    list_parser.set_defaults(func=cmd_memory_list)
    
    # memory stats <agent>
    stats_parser = memory_subparsers.add_parser(
        "stats",
        help="Show statistics for an agent",
        description="Display run statistics and storage information.",
    )
    stats_parser.add_argument(
        "agent",
        type=str,
        help="Agent name (folder name in exports/ or storage path)",
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    stats_parser.add_argument(
        "--storage-path",
        type=str,
        help="Custom storage path (default: ~/.hive/storage/{agent})",
    )
    stats_parser.set_defaults(func=cmd_memory_stats)


def cmd_memory_inspect(args: argparse.Namespace) -> int:
    """Inspect memory state for a specific run."""
    try:
        storage_path = Path(args.storage_path) if args.storage_path else None
        inspector = MemoryInspector(args.agent, storage_path)
        
        output = inspector.format_memory_output(args.run_id, json_format=args.json)
        print(output)
        
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error inspecting memory: {e}", file=sys.stderr)
        return 1


def cmd_memory_list(args: argparse.Namespace) -> int:
    """List all runs for an agent."""
    try:
        storage_path = Path(args.storage_path) if args.storage_path else None
        inspector = MemoryInspector(args.agent, storage_path)
        
        # Parse status filter
        status_filter = None
        if args.status:
            status_map = {
                "running": RunStatus.RUNNING,
                "completed": RunStatus.COMPLETED,
                "failed": RunStatus.FAILED,
            }
            status_filter = status_map[args.status]
        
        summaries = inspector.list_runs(status=status_filter, limit=args.limit)
        
        if not summaries:
            print(f"No runs found for agent: {args.agent}")
            return 0
        
        if args.json:
            output = []
            for summary in summaries:
                output.append({
                    "run_id": summary.run_id,
                    "goal_id": summary.goal_id,
                    "status": summary.status.value,
                    "duration_ms": summary.duration_ms,
                    "decision_count": summary.decision_count,
                    "success_rate": summary.success_rate,
                    "problem_count": summary.problem_count,
                    "narrative": summary.narrative,
                })
            print(json.dumps(output, indent=2))
        else:
            print("=" * 100)
            print(f"Run History - {args.agent}")
            print("=" * 100)
            print()
            
            for summary in summaries:
                status_symbol = {
                    RunStatus.COMPLETED: "✓",
                    RunStatus.FAILED: "✗",
                    RunStatus.RUNNING: "⟳",
                }
                symbol = status_symbol.get(summary.status, "?")
                
                print(f"{symbol} {summary.run_id}")
                print(f"  Status: {summary.status.value}")
                print(f"  Duration: {summary.duration_ms}ms")
                print(f"  Decisions: {summary.decision_count} ({summary.success_rate:.1%} successful)")
                if summary.problem_count > 0:
                    print(f"  Problems: {summary.problem_count}")
                if summary.narrative:
                    narrative_short = summary.narrative[:80] + "..." if len(summary.narrative) > 80 else summary.narrative
                    print(f"  Narrative: {narrative_short}")
                print()
            
            print("=" * 100)
            print(f"Total runs: {len(summaries)}")
            if args.status:
                print(f"Filter: {args.status}")
            if args.limit:
                print(f"(Showing most recent {args.limit})")
            print()
        
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error listing runs: {e}", file=sys.stderr)
        return 1


def cmd_memory_stats(args: argparse.Namespace) -> int:
    """Show statistics for an agent."""
    try:
        storage_path = Path(args.storage_path) if args.storage_path else None
        inspector = MemoryInspector(args.agent, storage_path)
        
        stats = inspector.get_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("=" * 70)
            print(f"Agent Statistics - {stats['agent']}")
            print("=" * 70)
            print()
            print(f"Total Runs: {stats['total_runs']}")
            print(f"  Completed: {stats['completed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Running: {stats['running']}")
            print()
            if stats['most_recent_run']:
                print(f"Most Recent Run: {stats['most_recent_run']}")
                print(f"  Status: {stats['most_recent_status']}")
            print()
            print(f"Storage Path: {stats['storage_path']}")
            print()
            print("=" * 70)
            print("Usage:")
            print("=" * 70)
            print()
            print(f"  # Inspect most recent run:")
            print(f"  hive memory inspect {args.agent}")
            print()
            print(f"  # Inspect specific run:")
            print(f"  hive memory inspect {args.agent} <run_id>")
            print()
            print(f"  # List all runs:")
            print(f"  hive memory list {args.agent}")
            print()
        
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error getting stats: {e}", file=sys.stderr)
        return 1
