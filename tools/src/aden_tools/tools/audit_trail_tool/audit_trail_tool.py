"""
Audit Trail Tool - Decision Timeline Generation for Compliance and Debugging.

Generates structured, queryable audit trails of all agent decisions.
Supports multiple export formats: JSON, CSV, and human-readable text.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """A single entry in the decision timeline."""
    timestamp: str
    run_id: str
    goal_id: str
    decision_id: str
    node_id: str
    intent: str
    decision_type: str
    chosen_option: str
    reasoning: str
    outcome_success: bool | None = None
    outcome_summary: str = ""
    tokens_used: int = 0
    latency_ms: int = 0

    model_config = {"extra": "allow"}


class AuditTimeline(BaseModel):
    """Complete audit timeline with metadata."""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_entries: int = 0
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    entries: list[TimelineEntry] = Field(default_factory=list)

    model_config = {"extra": "allow"}


def _load_run_from_storage(storage_path: Path, run_id: str) -> dict | None:
    """Load a run from file storage."""
    run_path = storage_path / "runs" / f"{run_id}.json"
    if not run_path.exists():
        return None
    with open(run_path, encoding="utf-8") as f:
        return json.load(f)


def _get_all_run_ids(storage_path: Path) -> list[str]:
    """Get all run IDs from storage."""
    runs_dir = storage_path / "runs"
    if not runs_dir.exists():
        return []
    return [f.stem for f in runs_dir.glob("*.json")]


def _get_run_ids_by_goal(storage_path: Path, goal_id: str) -> list[str]:
    """Get run IDs for a specific goal."""
    index_path = storage_path / "indexes" / "by_goal" / f"{goal_id}.json"
    if not index_path.exists():
        return []
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


def _extract_timeline_entries(run_data: dict) -> list[TimelineEntry]:
    """Extract timeline entries from a run."""
    entries = []
    run_id = run_data.get("id", "unknown")
    goal_id = run_data.get("goal_id", "unknown")
    
    for decision in run_data.get("decisions", []):
        # Get chosen option description
        chosen_option = ""
        chosen_id = decision.get("chosen_option_id", "")
        for opt in decision.get("options", []):
            if opt.get("id") == chosen_id:
                chosen_option = opt.get("description", "")
                break
        
        # Get outcome info
        outcome = decision.get("outcome")
        outcome_success = None
        outcome_summary = ""
        tokens_used = 0
        latency_ms = 0
        if outcome:
            outcome_success = outcome.get("success")
            outcome_summary = outcome.get("summary", "")
            tokens_used = outcome.get("tokens_used", 0)
            latency_ms = outcome.get("latency_ms", 0)
        
        entry = TimelineEntry(
            timestamp=decision.get("timestamp", ""),
            run_id=run_id,
            goal_id=goal_id,
            decision_id=decision.get("id", ""),
            node_id=decision.get("node_id", ""),
            intent=decision.get("intent", ""),
            decision_type=decision.get("decision_type", "custom"),
            chosen_option=chosen_option,
            reasoning=decision.get("reasoning", ""),
            outcome_success=outcome_success,
            outcome_summary=outcome_summary,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        entries.append(entry)
    
    return entries


def _filter_entries(
    entries: list[TimelineEntry],
    node_id: str | None = None,
    decision_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    success_only: bool = False,
    failure_only: bool = False,
) -> list[TimelineEntry]:
    """Apply filters to timeline entries."""
    filtered = entries
    
    if node_id:
        filtered = [e for e in filtered if e.node_id == node_id]
    
    if decision_type:
        filtered = [e for e in filtered if e.decision_type == decision_type]
    
    if start_date:
        filtered = [e for e in filtered if e.timestamp >= start_date]
    
    if end_date:
        filtered = [e for e in filtered if e.timestamp <= end_date]
    
    if success_only:
        filtered = [e for e in filtered if e.outcome_success is True]
    
    if failure_only:
        filtered = [e for e in filtered if e.outcome_success is False]
    
    return filtered


def _format_as_json(timeline: AuditTimeline) -> str:
    """Export timeline as JSON."""
    return timeline.model_dump_json(indent=2)


def _format_as_csv(timeline: AuditTimeline) -> str:
    """Export timeline as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "timestamp", "run_id", "goal_id", "decision_id", "node_id",
        "intent", "decision_type", "chosen_option", "reasoning",
        "outcome_success", "outcome_summary", "tokens_used", "latency_ms"
    ])
    
    # Data rows
    for entry in timeline.entries:
        writer.writerow([
            entry.timestamp,
            entry.run_id,
            entry.goal_id,
            entry.decision_id,
            entry.node_id,
            entry.intent,
            entry.decision_type,
            entry.chosen_option,
            entry.reasoning,
            entry.outcome_success,
            entry.outcome_summary,
            entry.tokens_used,
            entry.latency_ms,
        ])
    
    return output.getvalue()


def _format_as_text(timeline: AuditTimeline) -> str:
    """Export timeline as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("AUDIT TRAIL - DECISION TIMELINE")
    lines.append("=" * 80)
    lines.append(f"Generated: {timeline.generated_at}")
    lines.append(f"Total Entries: {timeline.total_entries}")
    if timeline.filters_applied:
        lines.append(f"Filters: {json.dumps(timeline.filters_applied)}")
    lines.append("-" * 80)
    lines.append("")
    
    for i, entry in enumerate(timeline.entries, 1):
        status = "✓" if entry.outcome_success else "✗" if entry.outcome_success is False else "?"
        lines.append(f"[{i}] {status} {entry.timestamp}")
        lines.append(f"    Run: {entry.run_id} | Goal: {entry.goal_id}")
        lines.append(f"    Node: {entry.node_id} | Type: {entry.decision_type}")
        lines.append(f"    Intent: {entry.intent}")
        lines.append(f"    Choice: {entry.chosen_option}")
        if entry.reasoning:
            if len(entry.reasoning) > 100:
                lines.append(f"    Reasoning: {entry.reasoning[:100]}...")
            else:
                lines.append(f"    Reasoning: {entry.reasoning}")
        if entry.outcome_summary:
            lines.append(f"    Outcome: {entry.outcome_summary}")
        if entry.tokens_used or entry.latency_ms:
            lines.append(f"    Metrics: {entry.tokens_used} tokens, {entry.latency_ms}ms")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("END OF AUDIT TRAIL")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def register_tools(mcp: FastMCP) -> None:
    """Register audit trail tools with the MCP server."""

    @mcp.tool()
    def generate_audit_timeline(
        storage_path: str,
        run_id: str | None = None,
        goal_id: str | None = None,
        node_id: str | None = None,
        decision_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        success_only: bool = False,
        failure_only: bool = False,
        export_format: str = "json",
    ) -> str:
        """
        Generate a decision timeline audit trail from agent runs.
        
        Use this tool to create audit trails for compliance, debugging,
        or analyzing agent decision patterns.
        
        Note: For large storage directories with many runs, consider using
        run_id or goal_id filters to limit memory usage.
        
        Args:
            storage_path: Path to the storage directory containing runs
            run_id: Filter to specific run (optional)
            goal_id: Filter to runs for a specific goal (optional)
            node_id: Filter to decisions from a specific node (optional)
            decision_type: Filter by decision type (optional)
            start_date: Filter decisions on or after this ISO date (optional)
            end_date: Filter decisions on or before this ISO date (optional)
            success_only: Only include successful decisions
            failure_only: Only include failed decisions
            export_format: Output format - "json", "csv", or "text" (default: json)
        
        Returns:
            The formatted audit timeline as a string
        """
        try:
            path = Path(storage_path)
            if not path.exists():
                return f"Error: Storage path does not exist: {storage_path}"
            
            # Determine which runs to process
            run_ids = []
            if run_id:
                run_ids = [run_id]
            elif goal_id:
                run_ids = _get_run_ids_by_goal(path, goal_id)
            else:
                run_ids = _get_all_run_ids(path)
            
            if not run_ids:
                return "No runs found matching the criteria."
            
            # Extract entries from all runs
            all_entries: list[TimelineEntry] = []
            for rid in run_ids:
                run_data = _load_run_from_storage(path, rid)
                if run_data:
                    entries = _extract_timeline_entries(run_data)
                    all_entries.extend(entries)
            
            # Apply filters
            filtered_entries = _filter_entries(
                all_entries,
                node_id=node_id,
                decision_type=decision_type,
                start_date=start_date,
                end_date=end_date,
                success_only=success_only,
                failure_only=failure_only,
            )
            
            # Sort by timestamp
            filtered_entries.sort(key=lambda e: e.timestamp)
            
            # Build timeline
            filters_applied = {}
            if run_id:
                filters_applied["run_id"] = run_id
            if goal_id:
                filters_applied["goal_id"] = goal_id
            if node_id:
                filters_applied["node_id"] = node_id
            if decision_type:
                filters_applied["decision_type"] = decision_type
            if start_date:
                filters_applied["start_date"] = start_date
            if end_date:
                filters_applied["end_date"] = end_date
            if success_only:
                filters_applied["success_only"] = True
            if failure_only:
                filters_applied["failure_only"] = True
            
            timeline = AuditTimeline(
                total_entries=len(filtered_entries),
                filters_applied=filters_applied,
                entries=filtered_entries,
            )
            
            # Format output
            if export_format.lower() == "csv":
                return _format_as_csv(timeline)
            elif export_format.lower() == "text":
                return _format_as_text(timeline)
            else:
                return _format_as_json(timeline)
        
        except Exception as e:
            return f"Error generating audit timeline: {str(e)}"

    @mcp.tool()
    def get_decision_details(
        storage_path: str,
        run_id: str,
        decision_id: str,
    ) -> str:
        """
        Get detailed information about a specific decision.
        
        Args:
            storage_path: Path to the storage directory
            run_id: The run containing the decision
            decision_id: The decision ID to retrieve
        
        Returns:
            JSON with full decision details including options and outcome
        """
        try:
            path = Path(storage_path)
            run_data = _load_run_from_storage(path, run_id)
            
            if not run_data:
                return f"Error: Run not found: {run_id}"
            
            for decision in run_data.get("decisions", []):
                if decision.get("id") == decision_id:
                    return json.dumps(decision, indent=2, default=str)
            
            return f"Error: Decision not found: {decision_id}"
        
        except Exception as e:
            return f"Error getting decision details: {str(e)}"

    @mcp.tool()
    def get_audit_summary(
        storage_path: str,
        goal_id: str | None = None,
    ) -> str:
        """
        Get a summary of audit trail statistics.
        
        Args:
            storage_path: Path to the storage directory
            goal_id: Optional goal ID to filter (returns all if not specified)
        
        Returns:
            JSON with audit summary statistics
        """
        try:
            path = Path(storage_path)
            if not path.exists():
                return f"Error: Storage path does not exist: {storage_path}"
            
            # Get run IDs
            if goal_id:
                run_ids = _get_run_ids_by_goal(path, goal_id)
            else:
                run_ids = _get_all_run_ids(path)
            
            # Collect statistics
            total_runs = len(run_ids)
            total_decisions = 0
            successful_decisions = 0
            failed_decisions = 0
            decision_types: dict[str, int] = {}
            nodes_used: dict[str, int] = {}
            
            for rid in run_ids:
                run_data = _load_run_from_storage(path, rid)
                if run_data:
                    for decision in run_data.get("decisions", []):
                        total_decisions += 1
                        
                        # Count by type
                        dtype = decision.get("decision_type", "custom")
                        decision_types[dtype] = decision_types.get(dtype, 0) + 1
                        
                        # Count by node
                        node = decision.get("node_id", "unknown")
                        nodes_used[node] = nodes_used.get(node, 0) + 1
                        
                        # Count outcomes
                        outcome = decision.get("outcome")
                        if outcome:
                            success = outcome.get("success")
                            if success is True:
                                successful_decisions += 1
                            elif success is False:
                                failed_decisions += 1
            
            summary = {
                "total_runs": total_runs,
                "total_decisions": total_decisions,
                "successful_decisions": successful_decisions,
                "failed_decisions": failed_decisions,
                "success_rate": (
                    successful_decisions / (successful_decisions + failed_decisions)
                    if (successful_decisions + failed_decisions) > 0
                    else 0.0
                ),
                "decision_types": decision_types,
                "nodes_used": nodes_used,
            }
            
            if goal_id:
                summary["goal_id"] = goal_id
            
            return json.dumps(summary, indent=2)
        
        except Exception as e:
            return f"Error getting audit summary: {str(e)}"
