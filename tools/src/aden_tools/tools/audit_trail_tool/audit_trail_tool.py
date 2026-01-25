"""
Audit Trail Tool - Decision timeline generation for agent runs.

This tool provides a comprehensive audit trail of agent decisions,
useful for debugging, compliance, and understanding agent behavior.

Features:
- Generate decision timelines from run data
- Filter by decision type, node, or time range
- Export in multiple formats (text, JSON, markdown)
- Analyze decision patterns and outcomes
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal
from pathlib import Path

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register audit trail tools with the MCP server."""

    @mcp.tool()
    def generate_audit_trail(
        run_data: str,
        format: Literal["text", "json", "markdown"] = "markdown",
        include_reasoning: bool = True,
        include_outcomes: bool = True,
        filter_decision_type: str | None = None,
        filter_node_id: str | None = None,
    ) -> str:
        """
        Generate an audit trail from agent run data.

        Creates a detailed timeline of all decisions made during an agent run,
        including reasoning, options considered, and outcomes. Useful for
        debugging agent behavior, compliance auditing, and performance analysis.

        Args:
            run_data: JSON string of run data (from storage.load_run())
            format: Output format - 'text' (plain), 'json' (structured), or 'markdown' (formatted)
            include_reasoning: Include the agent's reasoning for each decision
            include_outcomes: Include outcome information (success, latency, etc.)
            filter_decision_type: Only include decisions of this type (e.g., 'tool_selection')
            filter_node_id: Only include decisions from this node

        Returns:
            Formatted audit trail string in the requested format
        """
        try:
            # Parse run data
            run = json.loads(run_data)
            decisions = run.get("decisions", [])

            # Apply filters
            if filter_decision_type:
                decisions = [
                    d for d in decisions
                    if d.get("decision_type") == filter_decision_type
                ]

            if filter_node_id:
                decisions = [
                    d for d in decisions
                    if d.get("node_id") == filter_node_id
                ]

            # Sort by timestamp
            decisions = sorted(
                decisions,
                key=lambda d: d.get("timestamp", "")
            )

            # Generate output based on format
            if format == "json":
                return _format_json(run, decisions, include_reasoning, include_outcomes)
            elif format == "text":
                return _format_text(run, decisions, include_reasoning, include_outcomes)
            else:  # markdown
                return _format_markdown(run, decisions, include_reasoning, include_outcomes)

        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in run_data - {e}"
        except Exception as e:
            return f"Error generating audit trail: {e}"

    @mcp.tool()
    def analyze_decision_patterns(
        run_data: str,
    ) -> str:
        """
        Analyze decision patterns and statistics from an agent run.

        Provides insights into decision-making patterns including:
        - Decision type distribution
        - Success/failure rates by decision type
        - Average latency by decision type
        - Most active nodes
        - Common failure patterns

        Args:
            run_data: JSON string of run data (from storage.load_run())

        Returns:
            JSON string with analysis results
        """
        try:
            run = json.loads(run_data)
            decisions = run.get("decisions", [])

            # Initialize counters
            by_type: dict[str, dict[str, Any]] = {}
            by_node: dict[str, int] = {}
            total_success = 0
            total_failure = 0
            total_latency = 0
            latency_count = 0

            for decision in decisions:
                decision_type = decision.get("decision_type", "unknown")
                node_id = decision.get("node_id", "unknown")
                outcome = decision.get("outcome", {})

                # Count by type
                if decision_type not in by_type:
                    by_type[decision_type] = {
                        "count": 0,
                        "success": 0,
                        "failure": 0,
                        "total_latency_ms": 0,
                    }

                by_type[decision_type]["count"] += 1

                if outcome:
                    if outcome.get("success", False):
                        by_type[decision_type]["success"] += 1
                        total_success += 1
                    else:
                        by_type[decision_type]["failure"] += 1
                        total_failure += 1

                    latency = outcome.get("latency_ms", 0)
                    by_type[decision_type]["total_latency_ms"] += latency
                    total_latency += latency
                    latency_count += 1

                # Count by node
                by_node[node_id] = by_node.get(node_id, 0) + 1

            # Calculate averages and rates
            for dt_stats in by_type.values():
                count = dt_stats["count"]
                if count > 0:
                    dt_stats["success_rate"] = round(dt_stats["success"] / count, 3)
                    dt_stats["avg_latency_ms"] = round(
                        dt_stats["total_latency_ms"] / count, 2
                    )

            # Build analysis result
            analysis = {
                "total_decisions": len(decisions),
                "total_success": total_success,
                "total_failure": total_failure,
                "overall_success_rate": (
                    round(total_success / (total_success + total_failure), 3)
                    if (total_success + total_failure) > 0
                    else None
                ),
                "avg_latency_ms": (
                    round(total_latency / latency_count, 2)
                    if latency_count > 0
                    else None
                ),
                "by_decision_type": by_type,
                "by_node": dict(sorted(by_node.items(), key=lambda x: -x[1])),
                "run_status": run.get("status", "unknown"),
                "run_goal": run.get("goal_id", "unknown"),
            }

            return json.dumps(analysis, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in run_data: {e}"})
        except Exception as e:
            return json.dumps({"error": f"Analysis failed: {e}"})

    @mcp.tool()
    def compare_decision_outcomes(
        run_data: str,
        decision_ids: list[str] | None = None,
    ) -> str:
        """
        Compare decisions and their outcomes to identify patterns.

        Compares multiple decisions to find:
        - What options were considered vs chosen
        - Which decisions led to success vs failure
        - Correlation between confidence and outcomes

        Args:
            run_data: JSON string of run data
            decision_ids: Optional list of specific decision IDs to compare.
                          If not provided, compares all decisions.

        Returns:
            JSON string with comparison results
        """
        try:
            run = json.loads(run_data)
            decisions = run.get("decisions", [])

            if decision_ids:
                decisions = [d for d in decisions if d.get("id") in decision_ids]

            comparisons = []
            for decision in decisions:
                chosen_id = decision.get("chosen_option_id", "")
                options = decision.get("options", [])
                chosen_option = None
                alternatives = []

                for opt in options:
                    if opt.get("id") == chosen_id:
                        chosen_option = opt
                    else:
                        alternatives.append({
                            "id": opt.get("id"),
                            "description": opt.get("description"),
                            "confidence": opt.get("confidence", 0),
                        })

                outcome = decision.get("outcome", {})
                evaluation = decision.get("evaluation", {})

                comparisons.append({
                    "decision_id": decision.get("id"),
                    "timestamp": decision.get("timestamp"),
                    "node_id": decision.get("node_id"),
                    "intent": decision.get("intent"),
                    "decision_type": decision.get("decision_type"),
                    "chosen": {
                        "id": chosen_id,
                        "description": (
                            chosen_option.get("description") if chosen_option else None
                        ),
                        "confidence": (
                            chosen_option.get("confidence", 0) if chosen_option else None
                        ),
                    },
                    "alternatives_count": len(alternatives),
                    "alternatives": alternatives[:3],  # Top 3 alternatives
                    "outcome": {
                        "success": outcome.get("success", False),
                        "latency_ms": outcome.get("latency_ms", 0),
                        "summary": outcome.get("summary", ""),
                    },
                    "evaluation": {
                        "goal_aligned": evaluation.get("goal_aligned", True),
                        "quality": evaluation.get("outcome_quality", 1.0),
                        "better_option_existed": evaluation.get("better_option_existed", False),
                    },
                })

            return json.dumps({
                "decision_count": len(comparisons),
                "comparisons": comparisons,
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})
        except Exception as e:
            return json.dumps({"error": f"Comparison failed: {e}"})


def _format_json(
    run: dict,
    decisions: list[dict],
    include_reasoning: bool,
    include_outcomes: bool,
) -> str:
    """Format audit trail as JSON."""
    trail = {
        "run_id": run.get("id"),
        "goal_id": run.get("goal_id"),
        "status": run.get("status"),
        "decision_count": len(decisions),
        "timeline": [],
    }

    for decision in decisions:
        entry: dict[str, Any] = {
            "timestamp": decision.get("timestamp"),
            "decision_id": decision.get("id"),
            "node_id": decision.get("node_id"),
            "type": decision.get("decision_type"),
            "intent": decision.get("intent"),
            "chosen_option": decision.get("chosen_option_id"),
        }

        if include_reasoning:
            entry["reasoning"] = decision.get("reasoning", "")

        if include_outcomes:
            outcome = decision.get("outcome", {})
            entry["outcome"] = {
                "success": outcome.get("success", False),
                "summary": outcome.get("summary", ""),
                "latency_ms": outcome.get("latency_ms", 0),
            }

        trail["timeline"].append(entry)

    return json.dumps(trail, indent=2)


def _format_text(
    run: dict,
    decisions: list[dict],
    include_reasoning: bool,
    include_outcomes: bool,
) -> str:
    """Format audit trail as plain text."""
    lines = [
        f"AUDIT TRAIL",
        f"===========",
        f"Run ID: {run.get('id')}",
        f"Goal: {run.get('goal_id')}",
        f"Status: {run.get('status')}",
        f"Decisions: {len(decisions)}",
        f"",
        f"TIMELINE",
        f"--------",
    ]

    for i, decision in enumerate(decisions, 1):
        outcome = decision.get("outcome", {})
        success_marker = "[OK]" if outcome.get("success", False) else "[FAIL]"

        lines.append(f"")
        lines.append(f"{i}. {success_marker} {decision.get('intent', 'No intent')}")
        lines.append(f"   Node: {decision.get('node_id')}")
        lines.append(f"   Type: {decision.get('decision_type')}")
        lines.append(f"   Time: {decision.get('timestamp')}")

        if include_reasoning and decision.get("reasoning"):
            lines.append(f"   Reasoning: {decision.get('reasoning')}")

        if include_outcomes and outcome:
            lines.append(f"   Outcome: {outcome.get('summary', 'No summary')}")
            lines.append(f"   Latency: {outcome.get('latency_ms', 0)}ms")

    return "\n".join(lines)


def _format_markdown(
    run: dict,
    decisions: list[dict],
    include_reasoning: bool,
    include_outcomes: bool,
) -> str:
    """Format audit trail as markdown."""
    lines = [
        f"# Audit Trail",
        f"",
        f"| Property | Value |",
        f"|----------|-------|",
        f"| Run ID | `{run.get('id')}` |",
        f"| Goal | `{run.get('goal_id')}` |",
        f"| Status | {run.get('status')} |",
        f"| Decisions | {len(decisions)} |",
        f"",
        f"## Decision Timeline",
        f"",
    ]

    for i, decision in enumerate(decisions, 1):
        outcome = decision.get("outcome", {})
        success_emoji = "✅" if outcome.get("success", False) else "❌"

        lines.append(f"### {i}. {success_emoji} {decision.get('intent', 'No intent')}")
        lines.append(f"")
        lines.append(f"- **Node**: `{decision.get('node_id')}`")
        lines.append(f"- **Type**: `{decision.get('decision_type')}`")
        lines.append(f"- **Time**: {decision.get('timestamp')}")
        lines.append(f"- **Chosen Option**: `{decision.get('chosen_option_id')}`")

        if include_reasoning and decision.get("reasoning"):
            lines.append(f"")
            lines.append(f"> **Reasoning**: {decision.get('reasoning')}")

        if include_outcomes and outcome:
            lines.append(f"")
            lines.append(f"**Outcome**:")
            lines.append(f"- Success: {'Yes' if outcome.get('success') else 'No'}")
            lines.append(f"- Summary: {outcome.get('summary', 'N/A')}")
            lines.append(f"- Latency: {outcome.get('latency_ms', 0)}ms")

        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    return "\n".join(lines)
