"""
High-reliability file-based storage backend for runtime data.

Features:
- Atomic Swaps: Uses write-rename pattern to prevent JSON truncation.
- Stale Lock Recovery: PID-probing to prevent deadlocks after crashes.
- Self-Healing: Capability to reconstruct indexes from source-of-truth.
"""

import json
import os
import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Any

from framework.schemas.run import Run, RunSummary, RunStatus

logger = logging.getLogger(__name__)


class FileStorage:
    """
    File-based storage for runs with data integrity protection.

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

 
    # === ATOMICITY & LOCKING HELPERS ===

    def _atomic_write(self, path: Path, data: str) -> None:
        """Writes data to a temp file then renames it to prevent corruption."""
        dir_path = path.parent
        # Create temp file in the same directory to ensure atomic rename capability
        fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())  # Force write to physical disk
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    def _is_pid_running(self, pid: int) -> bool:
        """Check if a process ID is still active on the system."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)  # Signal 0 checks existence without killing
        except OSError:
            return False
        return True

    def _acquire_lock(self, lock_path: Path, timeout: float = 10.0) -> bool:
        """Acquires a lock and recovers if the previous owner crashed (stale lock)."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Exclusive creation; fails if file exists
                with open(lock_path, "x") as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                # Detect and clear stale locks
                try:
                    with open(lock_path, "r") as f:
                        content = f.read().strip()
                        if content:
                            old_pid = int(content)
                            if not self._is_pid_running(old_pid):
                                logger.warning(f"Recovering stale lock from dead PID {old_pid}")
                                lock_path.unlink(missing_ok=True)
                                continue
                except (ValueError, OSError):
                    pass

                time.sleep(0.1)  # Backoff
        return False

    # === SELF-HEALING UTILITY ===

    def rebuild_indexes(self) -> None:
        """Reconstructs all indexes from the source-of-truth run files."""
        logger.info("Initiating storage index reconstruction...")
        index_root = self.base_path / "indexes"

        if index_root.exists():
            shutil.rmtree(index_root)
        self._ensure_dirs()

        run_files = list((self.base_path / "runs").glob("*.json"))
        for run_path in run_files:
            try:
                run = Run.model_validate_json(run_path.read_text())
                self._add_to_index("by_goal", run.goal_id, run.id)
                self._add_to_index("by_status", run.status.value, run.id)
                for node_id in run.metrics.nodes_executed:
                    self._add_to_index("by_node", node_id, run.id)
            except Exception as e:
                logger.error(f"Skipping corrupt run file {run_path}: {e}")
        logger.info(f"Integrity check complete. Re-indexed {len(run_files)} runs.")

    # === RUN OPERATIONS ===

    def save_run(self, run: Run) -> None:
        """Save a run to storage with atomic protection."""
        # Save full run using Pydantic's model_dump_json
        run_path = self.base_path / "runs" / f"{run.id}.json"
        self._atomic_write(run_path, run.model_dump_json(indent=2))

        # Save summary
        summary = RunSummary.from_run(run)
        summary_path = self.base_path / "summaries" / f"{run.id}.json"
        self._atomic_write(summary_path, summary.model_dump_json(indent=2))

        # Update indexes (with atomic locking)
        self._add_to_index("by_goal", run.goal_id, run.id)
        self._add_to_index("by_status", run.status.value, run.id)
        for node_id in run.metrics.nodes_executed:
            self._add_to_index("by_node", node_id, run.id)

    def load_run(self, run_id: str) -> Run | None:
        """Load a run from storage."""
        run_path = self.base_path / "runs" / f"{run_id}.json"
        if not run_path.exists():
            return None
        with open(run_path) as f:
            return Run.model_validate_json(f.read())

    def load_summary(self, run_id: str) -> RunSummary | None:
        """Load just the summary (faster than full run)."""
        summary_path = self.base_path / "summaries" / f"{run_id}.json"
        if not summary_path.exists():
            # Fall back to computing from full run
            run = self.load_run(run_id)
            if run:
                return RunSummary.from_run(run)
            return None

        with open(summary_path) as f:
            return RunSummary.model_validate_json(f.read())

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its index entries atomically."""
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

        run_path.unlink(missing_ok=True)
        if summary_path.exists():
            summary_path.unlink(missing_ok=True)

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
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        if not index_path.exists():
            return []
        try:
            with open(index_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _add_to_index(self, index_type: str, key: str, value: str) -> None:
        """Add a value to an index with locking and atomic write."""
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        lock_path = index_path.with_suffix(".lock")

        if self._acquire_lock(lock_path):
            try:
                values = self._get_index(index_type, key)
                if value not in values:
                    values.append(value)
                    self._atomic_write(index_path, json.dumps(values))
            finally:
                lock_path.unlink(missing_ok=True)
        else:
            raise TimeoutError(f"Deadlock prevented: Could not lock {index_path}")

    def _remove_from_index(self, index_type: str, key: str, value: str) -> None:
        """Remove a value from an index with locking and atomic write."""
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        lock_path = index_path.with_suffix(".lock")

        if index_path.exists() and self._acquire_lock(lock_path):
            try:
                values = self._get_index(index_type, key)
                if value in values:
                    values.remove(value)
                    self._atomic_write(index_path, json.dumps(values))
            finally:
                lock_path.unlink(missing_ok=True)

    # === UTILITY ===

    def get_stats(self) -> dict:
        """Get storage statistics."""
        return {
            "total_runs": len(self.list_all_runs()),
            "total_goals": len(self.list_all_goals()),
            "storage_path": str(self.base_path),
        }