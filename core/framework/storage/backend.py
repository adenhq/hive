"""
File-based storage backend for runtime data.

Stores runs as JSON files with indexes for efficient querying.
Uses Pydantic's built-in serialization.
"""

import json
import os
from pathlib import Path

from framework.schemas.run import Run, RunStatus, RunSummary


class FileStorage:
    """
    Simple file-based storage for runs.

    Directory structure:
    {base_path}/
      runs/
        {run_id}.json           # Full run data
      indexes/
        by_goal/
          {goal_id}.json        # List of run IDs for this goal
        by_status/
          {status}.json         # List of run IDs with this status
        by_node/
          {node_id}.json        # List of run IDs that used this node
      summaries/
        {run_id}.json           # Run summary (for quick loading)
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._ensure_dirs()

    def _is_under_base(self, path: Path) -> bool:
        """
        Validate that the real path is still under the storage root.

        This mitigates TOCTOU issues where a previously-checked path is
        swapped for a symlink pointing outside the storage directory.
        """
        try:
            real = path.resolve(strict=True)
            base = self.base_path.resolve(strict=True)
        except FileNotFoundError:
            return False

        try:
            real.relative_to(base)
            return True
        except ValueError:
            return False

    def _ensure_dirs(self) -> None:
        """Create directory structure if it doesn't exist."""
        dirs = [
            self.base_path / "runs",
            self.base_path / "indexes" / "by_goal",
            self.base_path / "indexes" / "by_status",
            self.base_path / "indexes" / "by_node",
            self.base_path / "summaries",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _validate_key(self, key: str) -> None:
        """
        Validate key to prevent path traversal attacks.

        Args:
            key: The key to validate

        Raises:
            ValueError: If key contains path traversal or dangerous patterns
        """
        if not key or key.strip() == "":
            raise ValueError("Key cannot be empty")

        # Block path separators
        if "/" in key or "\\" in key:
            raise ValueError(f"Invalid key format: path separators not allowed in '{key}'")

        # Block parent directory references
        if ".." in key or key.startswith("."):
            raise ValueError(f"Invalid key format: path traversal detected in '{key}'")

        # Block absolute paths
        if key.startswith("/") or (len(key) > 1 and key[1] == ":"):
            raise ValueError(f"Invalid key format: absolute paths not allowed in '{key}'")

        # Block null bytes (Unix path injection)
        if "\x00" in key:
            raise ValueError("Invalid key format: null bytes not allowed")

        # Block other dangerous special characters
        dangerous_chars = {"<", ">", "|", "&", "$", "`", "'", '"'}
        if any(char in key for char in dangerous_chars):
            raise ValueError(f"Invalid key format: contains dangerous characters in '{key}'")

    # === RUN OPERATIONS ===

    def save_run(self, run: Run) -> None:
        """Save a run to storage."""
        # Save full run using Pydantic's model_dump_json
        run_path = self.base_path / "runs" / f"{run.id}.json"
        with open(run_path, "w", encoding="utf-8") as f:
            f.write(run.model_dump_json(indent=2))

        # Save summary
        summary = RunSummary.from_run(run)
        summary_path = self.base_path / "summaries" / f"{run.id}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))

        # Update indexes
        self._add_to_index("by_goal", run.goal_id, run.id)
        self._add_to_index("by_status", run.status.value, run.id)
        for node_id in run.metrics.nodes_executed:
            self._add_to_index("by_node", node_id, run.id)

    def load_run(self, run_id: str) -> Run | None:
        """Load a run from storage."""
        run_path = self.base_path / "runs" / f"{run_id}.json"
        if not self._is_under_base(run_path):
            return None

        try:
            with open(run_path, encoding="utf-8") as f:
                return Run.model_validate_json(f.read())
        except FileNotFoundError:
            return None

    def load_summary(self, run_id: str) -> RunSummary | None:
        """Load just the summary (faster than full run)."""
        summary_path = self.base_path / "summaries" / f"{run_id}.json"
        if self._is_under_base(summary_path):
            try:
                with open(summary_path, encoding="utf-8") as f:
                    return RunSummary.model_validate_json(f.read())
            except FileNotFoundError:
                pass

        # Fall back to computing from full run
        run = self.load_run(run_id)
        if run:
            return RunSummary.from_run(run)
        return None

    def delete_run(self, run_id: str) -> bool:
        """Delete a run from storage."""
        run_path = self.base_path / "runs" / f"{run_id}.json"
        summary_path = self.base_path / "summaries" / f"{run_id}.json"

        if not run_path.exists():
            return False

        # Load run to get index keys
        run = self.load_run(run_id)
        if run:
            self._remove_from_index("by_goal", run.goal_id, run_id)
            self._remove_from_index("by_status", run.status.value, run_id)
            for node_id in run.metrics.nodes_executed:
                self._remove_from_index("by_node", node_id, run_id)

        run_path.unlink()
        if summary_path.exists():
            summary_path.unlink()

        return True

    # === QUERY OPERATIONS ===

    def get_runs_by_goal(self, goal_id: str) -> list[str]:
        """Get all run IDs for a goal."""
        return self._get_index("by_goal", goal_id)

    def get_runs_by_status(self, status: str | RunStatus) -> list[str]:
        """Get all run IDs with a status."""
        if isinstance(status, RunStatus):
            status = status.value
        return self._get_index("by_status", status)

    def get_runs_by_node(self, node_id: str) -> list[str]:
        """Get all run IDs that executed a node."""
        return self._get_index("by_node", node_id)

    def list_all_runs(self) -> list[str]:
        """List all run IDs."""
        runs_dir = self.base_path / "runs"
        return [f.stem for f in runs_dir.glob("*.json")]

    def list_all_goals(self) -> list[str]:
        """List all goal IDs that have runs."""
        goals_dir = self.base_path / "indexes" / "by_goal"
        return [f.stem for f in goals_dir.glob("*.json")]

    # === INDEX OPERATIONS ===

    def _get_index(self, index_type: str, key: str) -> list[str]:
        """Get values from an index."""
        self._validate_key(key)  # Prevent path traversal
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        if not self._is_under_base(index_path):
            return []
        try:
            with open(index_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _add_to_index(self, index_type: str, key: str, value: str) -> None:
        """Add a value to an index."""
        self._validate_key(key)  # Prevent path traversal
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        values = self._get_index(index_type, key)  # Already validated in _get_index
        if value not in values:
            values.append(value)
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(values, f)

    def _remove_from_index(self, index_type: str, key: str, value: str) -> None:
        """Remove a value from an index."""
        self._validate_key(key)  # Prevent path traversal
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        values = self._get_index(index_type, key)  # Already validated in _get_index
        if value in values:
            values.remove(value)
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(values, f)

    # === UTILITY ===

    def get_stats(self) -> dict:
        """Get storage statistics."""
        return {
            "total_runs": len(self.list_all_runs()),
            "total_goals": len(self.list_all_goals()),
            "storage_path": str(self.base_path),
        }
