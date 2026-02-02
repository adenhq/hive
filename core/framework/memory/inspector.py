"""Inspector for analyzing agent run memory and execution data."""

import json
from pathlib import Path
from typing import Any

from framework.schemas.run import Run, RunStatus, RunSummary
from framework.storage.backend import FileStorage


class MemoryInspector:
    """
    Inspector for viewing agent run data and SharedMemory state.
    
    Provides access to the final SharedMemory state (output_data) and
    run metadata from persistent storage at ~/.hive/storage/{agent}/runs/.
    """

    def __init__(self, agent_name: str, storage_path: Path | None = None):
        """
        Initialize memory inspector for an agent.
        
        Args:
            agent_name: Name of the agent (folder name in exports/ or storage/)
            storage_path: Optional custom storage path. Defaults to ~/.hive/storage/{agent_name}
        """
        self.agent_name = agent_name
        
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            home = Path.home()
            self.storage_path = home / ".hive" / "storage" / agent_name
        
        if not self.storage_path.exists():
            raise FileNotFoundError(
                f"Storage path does not exist: {self.storage_path}\n"
                f"Run the agent first to create run history: hive run exports/{agent_name} --input '{{...}}'"
            )
        
        self.storage = FileStorage(self.storage_path)
    
    def list_runs(self, status: RunStatus | None = None, limit: int | None = None) -> list[RunSummary]:
        """
        List all runs for this agent.
        
        Args:
            status: Optional filter by status (RUNNING, COMPLETED, FAILED)
            limit: Maximum number of runs to return (most recent first)
        
        Returns:
            List of RunSummary objects
        """
        if status:
            run_ids = self.storage.get_runs_by_status(status)
        else:
            run_ids = self.storage.list_all_runs()
        
        summaries = []
        for run_id in run_ids:
            summary = self.storage.load_summary(run_id)
            if summary:
                summaries.append(summary)
        
        # Sort by run_id (which includes timestamp) descending
        summaries.sort(key=lambda s: s.run_id, reverse=True)
        
        if limit:
            summaries = summaries[:limit]
        
        return summaries
    
    def get_run(self, run_id: str | None = None) -> Run | None:
        """
        Get full run data including SharedMemory state.
        
        Args:
            run_id: Run ID to fetch. If None, fetches the most recent run.
        
        Returns:
            Full Run object with output_data (SharedMemory) and metadata
        """
        if run_id is None:
            # Get most recent run
            all_runs = self.storage.list_all_runs()
            if not all_runs:
                return None
            all_runs.sort(reverse=True)  # Sort by timestamp descending
            run_id = all_runs[0]
        
        return self.storage.load_run(run_id)
    
    def get_memory_state(self, run_id: str | None = None) -> dict[str, Any] | None:
        """
        Get the final SharedMemory state (output_data) for a run.
        
        This is the key-value store that accumulated node outputs during
        graph execution. Only the final state is stored, not per-node states.
        
        Args:
            run_id: Run ID to fetch. If None, fetches the most recent run.
        
        Returns:
            Dictionary containing the SharedMemory key-value pairs
        """
        run = self.get_run(run_id)
        if run:
            return run.output_data
        return None
    
    def get_run_metadata(self, run_id: str | None = None) -> dict[str, Any] | None:
        """
        Get run metadata (status, decisions, metrics, execution path).
        
        Args:
            run_id: Run ID to fetch. If None, fetches the most recent run.
        
        Returns:
            Dictionary containing run metadata
        """
        run = self.get_run(run_id)
        if not run:
            return None
        
        return {
            "run_id": run.id,
            "goal_id": run.goal_id,
            "goal_description": run.goal_description,
            "status": run.status.value,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_ms": run.duration_ms,
            "narrative": run.narrative,
            "metrics": {
                "total_decisions": run.metrics.total_decisions,
                "successful_decisions": run.metrics.successful_decisions,
                "failed_decisions": run.metrics.failed_decisions,
                "total_tokens": run.metrics.total_tokens,
                "total_latency_ms": run.metrics.total_latency_ms,
                "nodes_executed": run.metrics.nodes_executed,
            },
            "execution_path": run.metrics.nodes_executed,
            "decision_count": len(run.decisions),
            "problem_count": len(run.problems),
        }
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about agent runs.
        
        Returns:
            Dictionary with run statistics
        """
        all_runs = self.storage.list_all_runs()
        
        if not all_runs:
            return {
                "agent": self.agent_name,
                "total_runs": 0,
                "storage_path": str(self.storage_path),
            }
        
        # Load all summaries for stats
        summaries = []
        for run_id in all_runs:
            summary = self.storage.load_summary(run_id)
            if summary:
                summaries.append(summary)
        
        # Calculate stats
        completed = len([s for s in summaries if s.status == RunStatus.COMPLETED])
        failed = len([s for s in summaries if s.status == RunStatus.FAILED])
        running = len([s for s in summaries if s.status == RunStatus.RUNNING])
        
        # Get most recent run
        summaries.sort(key=lambda s: s.run_id, reverse=True)
        most_recent = summaries[0] if summaries else None
        
        return {
            "agent": self.agent_name,
            "total_runs": len(all_runs),
            "completed": completed,
            "failed": failed,
            "running": running,
            "storage_path": str(self.storage_path),
            "most_recent_run": most_recent.run_id if most_recent else None,
            "most_recent_status": most_recent.status.value if most_recent else None,
        }
    
    def format_memory_output(self, run_id: str | None = None, json_format: bool = False) -> str:
        """
        Format memory state and metadata for display.
        
        Args:
            run_id: Run ID to format. If None, uses most recent run.
            json_format: If True, return JSON string. Otherwise, human-readable.
        
        Returns:
            Formatted string
        """
        run = self.get_run(run_id)
        if not run:
            return "No runs found. Run the agent first to create run history."
        
        output = {
            "run_id": run.id,
            "status": run.status.value,
            "duration_ms": run.duration_ms,
            "memory_state": run.output_data,
            "metadata": {
                "goal_description": run.goal_description,
                "narrative": run.narrative,
                "execution_path": run.metrics.nodes_executed,
                "total_decisions": run.metrics.total_decisions,
                "successful_decisions": run.metrics.successful_decisions,
                "failed_decisions": run.metrics.failed_decisions,
                "problem_count": len(run.problems),
            },
        }
        
        if json_format:
            return json.dumps(output, indent=2)
        
        # Human-readable format
        lines = []
        lines.append("=" * 80)
        lines.append(f"Agent Memory State - {self.agent_name}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Run ID: {run.id}")
        lines.append(f"Status: {run.status.value}")
        lines.append(f"Duration: {run.duration_ms}ms")
        lines.append("")
        lines.append("Goal:")
        lines.append(f"  {run.goal_description}")
        lines.append("")
        lines.append("Execution Path:")
        for node in run.metrics.nodes_executed:
            lines.append(f"  → {node}")
        lines.append("")
        lines.append("SharedMemory State (Final):")
        if run.output_data:
            for key, value in run.output_data.items():
                value_str = json.dumps(value) if not isinstance(value, str) else value
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                lines.append(f"  {key}: {value_str}")
        else:
            lines.append("  (empty)")
        lines.append("")
        lines.append("Metrics:")
        lines.append(f"  Decisions: {run.metrics.successful_decisions}/{run.metrics.total_decisions} successful")
        lines.append(f"  Total Tokens: {run.metrics.total_tokens:,}")
        lines.append(f"  Total Latency: {run.metrics.total_latency_ms}ms")
        lines.append(f"  Problems: {len(run.problems)}")
        lines.append("")
        if run.narrative:
            lines.append("Narrative:")
            lines.append(f"  {run.narrative}")
            lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
