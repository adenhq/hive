"""
Audit Trail - Decision timeline generation for debugging and observability.

This module provides tools to:
1. Track all decisions made during agent execution
2. Export decision timelines in various formats
3. Filter and analyze decision patterns
4. Support debugging and post-mortem analysis
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from framework.runtime.core import Runtime
    from framework.schemas.decision import Decision


class AuditEntryType(str, Enum):
    """Types of audit entries."""
    DECISION = "decision"
    STATE_CHANGE = "state_change"
    RUN_START = "run_start"
    RUN_END = "run_end"
    PROBLEM = "problem"


class AuditEntry(BaseModel):
    """A single entry in the audit trail."""
    timestamp: datetime = Field(default_factory=datetime.now)
    entry_type: AuditEntryType
    node_id: str = ""
    
    # For decisions
    decision_id: str | None = None
    intent: str = ""
    chosen_action: str = ""
    reasoning: str = ""
    success: bool | None = None
    
    # For state changes
    key: str | None = None
    old_value: Any = None
    new_value: Any = None
    
    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditTrail:
    """
    Generate and export decision timelines for debugging.
    
    Usage:
        runtime = Runtime(storage_path)
        # ... execute agent ...
        
        trail = AuditTrail(runtime)
        
        # Get all entries
        entries = trail.get_timeline()
        
        # Export as markdown
        print(trail.export_markdown())
        
        # Filter by node
        node_entries = trail.filter_by_node("analyzer")
        
        # Filter by outcome
        failures = trail.filter_by_outcome(success=False)
    """
    
    def __init__(self, runtime: "Runtime"):
        """
        Initialize audit trail from a runtime.
        
        Args:
            runtime: The runtime to extract audit data from
        """
        self.runtime = runtime
        self._entries: list[AuditEntry] | None = None
    
    def get_timeline(self) -> list[AuditEntry]:
        """
        Get chronological list of all audit entries.
        
        Returns:
            List of AuditEntry objects sorted by timestamp
        """
        if self._entries is not None:
            return self._entries
        
        entries: list[AuditEntry] = []
        
        # Get current run
        run = self.runtime.current_run()
        if run is None:
            return entries
        
        # Add run start entry
        entries.append(AuditEntry(
            timestamp=run.start_time,
            entry_type=AuditEntryType.RUN_START,
            intent=run.goal_description,
            metadata={
                "run_id": run.id,
                "goal_id": run.goal_id,
                "input_data": run.input_data,
            }
        ))
        
        # Add decision entries
        for decision in run.decisions:
            chosen = decision.chosen_option
            entries.append(AuditEntry(
                timestamp=decision.timestamp,
                entry_type=AuditEntryType.DECISION,
                node_id=decision.node_id,
                decision_id=decision.id,
                intent=decision.intent,
                chosen_action=chosen.description if chosen else "",
                reasoning=decision.reasoning,
                success=decision.outcome.success if decision.outcome else None,
                metadata={
                    "decision_type": decision.decision_type.value,
                    "options_count": len(decision.options),
                    "tokens_used": decision.outcome.tokens_used if decision.outcome else 0,
                    "latency_ms": decision.outcome.latency_ms if decision.outcome else 0,
                }
            ))
        
        # Add problems
        for problem in run.problems:
            entries.append(AuditEntry(
                timestamp=datetime.now(),  # Problems don't have timestamps in current schema
                entry_type=AuditEntryType.PROBLEM,
                node_id=problem.get("decision_id", ""),
                intent=problem.get("description", ""),
                metadata={
                    "severity": problem.get("severity", "unknown"),
                    "root_cause": problem.get("root_cause"),
                    "suggested_fix": problem.get("suggested_fix"),
                }
            ))
        
        # Add run end entry if run has ended
        if run.end_time:
            entries.append(AuditEntry(
                timestamp=run.end_time,
                entry_type=AuditEntryType.RUN_END,
                success=run.status.value == "completed",
                intent=run.narrative,
                metadata={
                    "status": run.status.value,
                    "output_data": run.output_data,
                    "total_tokens": run.total_tokens,
                    "total_latency_ms": run.total_latency_ms,
                }
            ))
        
        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)
        self._entries = entries
        
        return entries
    
    def filter_by_node(self, node_id: str) -> list[AuditEntry]:
        """
        Filter entries by node ID.
        
        Args:
            node_id: The node ID to filter by
            
        Returns:
            List of entries for the specified node
        """
        return [e for e in self.get_timeline() if e.node_id == node_id]
    
    def filter_by_outcome(self, success: bool) -> list[AuditEntry]:
        """
        Filter entries by success/failure.
        
        Args:
            success: True for successful entries, False for failures
            
        Returns:
            List of entries matching the outcome
        """
        return [
            e for e in self.get_timeline() 
            if e.entry_type == AuditEntryType.DECISION and e.success == success
        ]
    
    def filter_by_type(self, entry_type: AuditEntryType) -> list[AuditEntry]:
        """
        Filter entries by type.
        
        Args:
            entry_type: The entry type to filter by
            
        Returns:
            List of entries of the specified type
        """
        return [e for e in self.get_timeline() if e.entry_type == entry_type]
    
    def get_decisions_only(self) -> list[AuditEntry]:
        """Get only decision entries."""
        return self.filter_by_type(AuditEntryType.DECISION)
    
    def get_failures(self) -> list[AuditEntry]:
        """Get all failed decisions."""
        return self.filter_by_outcome(success=False)
    
    def get_summary_stats(self) -> dict[str, Any]:
        """
        Get summary statistics for the audit trail.
        
        Returns:
            Dict with statistics about decisions, success rate, etc.
        """
        entries = self.get_timeline()
        decisions = self.get_decisions_only()
        
        successful = len([d for d in decisions if d.success is True])
        failed = len([d for d in decisions if d.success is False])
        
        total_tokens = sum(
            d.metadata.get("tokens_used", 0) 
            for d in decisions
        )
        total_latency = sum(
            d.metadata.get("latency_ms", 0) 
            for d in decisions
        )
        
        nodes = set(e.node_id for e in decisions if e.node_id)
        
        return {
            "total_entries": len(entries),
            "total_decisions": len(decisions),
            "successful_decisions": successful,
            "failed_decisions": failed,
            "success_rate": successful / len(decisions) if decisions else 0,
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency,
            "nodes_involved": list(nodes),
            "node_count": len(nodes),
        }
    
    def export_json(self, indent: int = 2) -> str:
        """
        Export timeline as JSON.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string of the audit trail
        """
        entries = self.get_timeline()
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary_stats(),
            "entries": [e.model_dump(mode="json") for e in entries]
        }
        return json.dumps(data, indent=indent, default=str)
    
    def export_markdown(self) -> str:
        """
        Export timeline as readable markdown.
        
        Returns:
            Markdown string of the audit trail
        """
        entries = self.get_timeline()
        stats = self.get_summary_stats()
        
        lines = [
            "# Audit Trail",
            "",
            "## Summary",
            "",
            f"- **Total Decisions**: {stats['total_decisions']}",
            f"- **Success Rate**: {stats['success_rate']:.1%}",
            f"- **Total Tokens**: {stats['total_tokens']}",
            f"- **Total Latency**: {stats['total_latency_ms']}ms",
            f"- **Nodes Involved**: {', '.join(stats['nodes_involved']) or 'None'}",
            "",
            "## Timeline",
            "",
        ]
        
        for entry in entries:
            icon = self._get_entry_icon(entry)
            time_str = entry.timestamp.strftime("%H:%M:%S")
            
            if entry.entry_type == AuditEntryType.RUN_START:
                lines.append(f"### {icon} {time_str} - Run Started")
                lines.append(f"> {entry.intent}")
                lines.append("")
                
            elif entry.entry_type == AuditEntryType.RUN_END:
                status = "✅ Success" if entry.success else "❌ Failed"
                lines.append(f"### {icon} {time_str} - Run Ended ({status})")
                if entry.intent:
                    lines.append(f"> {entry.intent}")
                lines.append("")
                
            elif entry.entry_type == AuditEntryType.DECISION:
                status = "✓" if entry.success else "✗" if entry.success is False else "?"
                lines.append(f"### {icon} {time_str} - [{entry.node_id}] {status}")
                lines.append(f"**Intent**: {entry.intent}")
                lines.append(f"**Action**: {entry.chosen_action}")
                lines.append(f"**Reasoning**: {entry.reasoning}")
                if entry.metadata.get("tokens_used"):
                    lines.append(f"*Tokens: {entry.metadata['tokens_used']}, Latency: {entry.metadata['latency_ms']}ms*")
                lines.append("")
                
            elif entry.entry_type == AuditEntryType.PROBLEM:
                lines.append(f"### {icon} {time_str} - Problem Reported")
                lines.append(f"**Severity**: {entry.metadata.get('severity', 'unknown')}")
                lines.append(f"**Description**: {entry.intent}")
                if entry.metadata.get("root_cause"):
                    lines.append(f"**Root Cause**: {entry.metadata['root_cause']}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _get_entry_icon(self, entry: AuditEntry) -> str:
        """Get icon for entry type."""
        icons = {
            AuditEntryType.RUN_START: "🚀",
            AuditEntryType.RUN_END: "🏁",
            AuditEntryType.DECISION: "🤔",
            AuditEntryType.STATE_CHANGE: "📝",
            AuditEntryType.PROBLEM: "⚠️",
        }
        return icons.get(entry.entry_type, "•")
