"""
Audit Trail Tool - Generate decision timelines from agent runs.

This tool queries runtime storage to generate a timeline of decisions and outcomes
for a given run, helping with debugging and understanding agent behavior.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register audit trail tools with the MCP server."""

    @mcp.tool()
    def generate_audit_trail(
        run_id: str,
        storage_path: str,
        format: str = "json",
        include_outcomes: bool = True,
        include_options: bool = True,
    ) -> dict:
        """
        Generate an audit trail (decision timeline) for a specific agent run.

        Returns a chronological timeline of all decisions made during the run,
        including their outcomes, options considered, and context.

        Args:
            run_id: The ID of the run to generate audit trail for
            storage_path: Path to the runtime storage directory
            format: Output format - "json" (structured) or "markdown" (human-readable)
            include_outcomes: Whether to include outcome details for each decision
            include_options: Whether to include all options that were considered

        Returns:
            Dict with audit trail data or error dict
        """
        try:
            storage_path_obj = Path(storage_path)
            if not storage_path_obj.exists():
                return {"error": f"Storage path does not exist: {storage_path}"}

            # Load the run data
            run_file = storage_path_obj / "runs" / f"{run_id}.json"
            if not run_file.exists():
                return {"error": f"Run not found: {run_id}"}

            with open(run_file, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            # Extract decisions
            decisions = run_data.get("decisions", [])
            if not decisions:
                return {
                    "run_id": run_id,
                    "message": "No decisions found for this run",
                    "timeline": [],
                }

            # Build timeline
            timeline = []
            for decision in decisions:
                decision_id = decision.get("id", "unknown")
                decision_type = decision.get("decision_type", "custom")
                intent = decision.get("intent", "")
                reasoning = decision.get("reasoning", "")
                timestamp = decision.get("timestamp")
                node_id = decision.get("node_id", "unknown")
                chosen_option_id = decision.get("chosen_option_id", "")

                # Get chosen option details
                options = decision.get("options", [])
                chosen_option = None
                if include_options:
                    for opt in options:
                        if opt.get("id") == chosen_option_id:
                            chosen_option = opt
                            break

                # Get outcome if available
                outcome = None
                if include_outcomes:
                    outcomes = run_data.get("outcomes", {})
                    outcome = outcomes.get(decision_id)

                timeline_entry = {
                    "timestamp": timestamp,
                    "decision_id": decision_id,
                    "node_id": node_id,
                    "decision_type": decision_type,
                    "intent": intent,
                    "reasoning": reasoning,
                    "chosen_option_id": chosen_option_id,
                }

                if include_options and chosen_option:
                    timeline_entry["chosen_option"] = {
                        "id": chosen_option.get("id"),
                        "description": chosen_option.get("description"),
                        "action_type": chosen_option.get("action_type"),
                    }
                    if len(options) > 1:
                        timeline_entry["total_options"] = len(options)
                        timeline_entry["other_options"] = [
                            {"id": opt.get("id"), "description": opt.get("description")}
                            for opt in options
                            if opt.get("id") != chosen_option_id
                        ]

                if include_outcomes and outcome:
                    timeline_entry["outcome"] = {
                        "success": outcome.get("success", False),
                        "summary": outcome.get("summary", ""),
                        "error": outcome.get("error"),
                        "tokens_used": outcome.get("tokens_used", 0),
                        "latency_ms": outcome.get("latency_ms", 0),
                    }

                timeline.append(timeline_entry)

            # Sort by timestamp
            timeline.sort(key=lambda x: x.get("timestamp", ""))

            # Format output
            if format == "markdown":
                markdown = _format_markdown_timeline(run_data, timeline)
                return {
                    "run_id": run_id,
                    "format": "markdown",
                    "timeline": timeline,
                    "markdown": markdown,
                }

            return {
                "run_id": run_id,
                "goal_id": run_data.get("goal_id", ""),
                "status": run_data.get("status", "unknown"),
                "started_at": run_data.get("started_at"),
                "completed_at": run_data.get("completed_at"),
                "total_decisions": len(timeline),
                "format": "json",
                "timeline": timeline,
            }

        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in run file: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to generate audit trail: {str(e)}"}

    @mcp.tool()
    def list_runs(
        storage_path: str,
        goal_id: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        List available runs in the storage directory.

        Useful for finding run IDs to generate audit trails for.

        Args:
            storage_path: Path to the runtime storage directory
            goal_id: Optional filter by goal ID
            limit: Maximum number of runs to return

        Returns:
            Dict with list of runs and their metadata
        """
        try:
            storage_path_obj = Path(storage_path)
            runs_dir = storage_path_obj / "runs"
            if not runs_dir.exists():
                return {"error": f"Runs directory does not exist: {runs_dir}"}

            runs = []
            for run_file in runs_dir.glob("*.json"):
                try:
                    with open(run_file, "r", encoding="utf-8") as f:
                        run_data = json.load(f)

                    # Filter by goal_id if provided
                    if goal_id and run_data.get("goal_id") != goal_id:
                        continue

                    runs.append({
                        "run_id": run_data.get("id", run_file.stem),
                        "goal_id": run_data.get("goal_id", ""),
                        "status": run_data.get("status", "unknown"),
                        "started_at": run_data.get("started_at"),
                        "completed_at": run_data.get("completed_at"),
                        "total_decisions": len(run_data.get("decisions", [])),
                    })
                except Exception:
                    # Skip invalid files
                    continue

            # Sort by started_at (most recent first)
            runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)

            return {
                "storage_path": str(storage_path),
                "total_runs": len(runs),
                "runs": runs[:limit],
            }

        except Exception as e:
            return {"error": f"Failed to list runs: {str(e)}"}


def _format_markdown_timeline(run_data: dict, timeline: list[dict]) -> str:
    """Format timeline as markdown for human-readable output."""
    lines = []
    lines.append(f"# Audit Trail: Run {run_data.get('id', 'unknown')}")
    lines.append("")
    lines.append(f"**Goal ID:** {run_data.get('goal_id', 'unknown')}")
    lines.append(f"**Status:** {run_data.get('status', 'unknown')}")
    lines.append(f"**Started:** {run_data.get('started_at', 'unknown')}")
    lines.append(f"**Completed:** {run_data.get('completed_at', 'N/A')}")
    lines.append(f"**Total Decisions:** {len(timeline)}")
    lines.append("")
    lines.append("## Decision Timeline")
    lines.append("")

    for i, entry in enumerate(timeline, 1):
        lines.append(f"### Decision {i}: {entry.get('decision_id', 'unknown')}")
        lines.append("")
        lines.append(f"- **Timestamp:** {entry.get('timestamp', 'unknown')}")
        lines.append(f"- **Node:** {entry.get('node_id', 'unknown')}")
        lines.append(f"- **Type:** {entry.get('decision_type', 'custom')}")
        lines.append(f"- **Intent:** {entry.get('intent', 'N/A')}")
        lines.append(f"- **Reasoning:** {entry.get('reasoning', 'N/A')}")
        lines.append("")

        if entry.get("chosen_option"):
            opt = entry["chosen_option"]
            lines.append(f"**Chosen Option:** {opt.get('description', 'N/A')}")
            if entry.get("total_options", 1) > 1:
                lines.append(f"({entry['total_options']} options considered)")
            lines.append("")

        if entry.get("outcome"):
            outcome = entry["outcome"]
            status = "✅ Success" if outcome.get("success") else "❌ Failed"
            lines.append(f"**Outcome:** {status}")
            if outcome.get("summary"):
                lines.append(f"- Summary: {outcome['summary']}")
            if outcome.get("error"):
                lines.append(f"- Error: {outcome['error']}")
            if outcome.get("tokens_used", 0) > 0:
                lines.append(f"- Tokens: {outcome['tokens_used']}")
            if outcome.get("latency_ms", 0) > 0:
                lines.append(f"- Latency: {outcome['latency_ms']}ms")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
