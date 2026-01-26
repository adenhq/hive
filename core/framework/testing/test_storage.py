"""
High-reliability file-based storage backend for test data.

Features:
- Atomic Swaps: Protects test cases and results from JSON truncation.
- Stale Lock Recovery: Prevents deadlocks in concurrent testing environments.
- Self-Healing: Capability to reconstruct test indexes from source-of-truth.
"""

import json
import os
import time
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any

from framework.testing.test_case import Test, ApprovalStatus, TestType
from framework.testing.test_result import TestResult

logger = logging.getLogger(__name__)


class TestStorage:
    """
    File-based storage for tests and results with data integrity protection.

    Directory structure:
    {base_path}/
      tests/
        {goal_id}/
          {test_id}.json           # Full test data
      indexes/
        by_goal/{goal_id}.json     # List of test IDs for this goal
        by_approval/{status}.json  # Tests by approval status
        by_type/{test_type}.json   # Tests by type
        by_criteria/{criteria_id}.json  # Tests by parent criteria
      results/
        {test_id}/
          {timestamp}.json         # Test run results
          latest.json              # Most recent result
      suites/
        {goal_id}_suite.json       # Test suite metadata
    """
    __test__ = False  # Not a pytest test class

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directory structure if it doesn't exist."""
        dirs = [
            self.base_path / "tests",
            self.base_path / "indexes" / "by_goal",
            self.base_path / "indexes" / "by_approval",
            self.base_path / "indexes" / "by_type",
            self.base_path / "indexes" / "by_criteria",
            self.base_path / "results",
            self.base_path / "suites",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # === ATOMICITY & LOCKING HELPERS ===

    def _atomic_write(self, path: Path, data: str) -> None:
        """Writes data to a temp file then renames it to prevent corruption."""
        dir_path = path.parent
        dir_path.mkdir(parents=True, exist_ok=True)
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
        if pid <= 0: return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _acquire_lock(self, lock_path: Path, timeout: float = 10.0) -> bool:
        """Acquires a lock and recovers from stale locks (dead processes)."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(lock_path, "x") as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                try:
                    with open(lock_path, "r") as f:
                        content = f.read().strip()
                        if content:
                            old_pid = int(content)
                            if not self._is_pid_running(old_pid):
                                logger.warning(f"Recovering stale test lock from PID {old_pid}")
                                lock_path.unlink(missing_ok=True)
                                continue
                except (ValueError, OSError):
                    pass
                time.sleep(0.1)
        return False

    # === SELF-HEALING UTILITY ===

    def rebuild_indexes(self) -> None:
        """Reconstructs all test indexes from the source-of-truth test files."""
        logger.info("Initiating test storage index reconstruction...")
        index_root = self.base_path / "indexes"
        if index_root.exists():
            shutil.rmtree(index_root)
        self._ensure_dirs()

        test_files = list(self.base_path.glob("tests/*/*.json"))
        for test_path in test_files:
            try:
                test = Test.model_validate_json(test_path.read_text())
                self._add_to_index("by_goal", test.goal_id, test.id)
                self._add_to_index("by_approval", test.approval_status.value, test.id)
                self._add_to_index("by_type", test.test_type.value, test.id)
                self._add_to_index("by_criteria", test.parent_criteria_id, test.id)
            except Exception as e:
                logger.error(f"Skipping corrupt test file {test_path}: {e}")
        logger.info(f"Test reconstruction complete. Re-indexed {len(test_files)} tests.")

    # === TEST OPERATIONS ===

    def save_test(self, test: Test) -> None:
        """Save a test to storage atomically."""
        goal_dir = self.base_path / "tests" / test.goal_id
        test_path = goal_dir / f"{test.id}.json"
        
        self._atomic_write(test_path, test.model_dump_json(indent=2))

        self._add_to_index("by_goal", test.goal_id, test.id)
        self._add_to_index("by_approval", test.approval_status.value, test.id)
        self._add_to_index("by_type", test.test_type.value, test.id)
        self._add_to_index("by_criteria", test.parent_criteria_id, test.id)

    def load_test(self, goal_id: str, test_id: str) -> Test | None:
        """Load a test from storage."""
        test_path = self.base_path / "tests" / goal_id / f"{test_id}.json"
        if not test_path.exists():
            return None
        with open(test_path) as f:
            return Test.model_validate_json(f.read())

    def delete_test(self, goal_id: str, test_id: str) -> bool:
        """Delete a test and clean its indexes and results."""
        test_path = self.base_path / "tests" / goal_id / f"{test_id}.json"
        if not test_path.exists():
            return False

        test = self.load_test(goal_id, test_id)
        if test:
            self._remove_from_index("by_goal", test.goal_id, test_id)
            self._remove_from_index("by_approval", test.approval_status.value, test_id)
            self._remove_from_index("by_type", test.test_type.value, test_id)
            self._remove_from_index("by_criteria", test.parent_criteria_id, test_id)

        test_path.unlink(missing_ok=True)
        results_dir = self.base_path / "results" / test_id
        if results_dir.exists():
            shutil.rmtree(results_dir)
        return True

    def update_test(self, test: Test) -> None:
        """Update an existing test and handle index transitions."""
        old_test = self.load_test(test.goal_id, test.id)
        if old_test and old_test.approval_status != test.approval_status:
            self._remove_from_index("by_approval", old_test.approval_status.value, test.id)
            self._add_to_index("by_approval", test.approval_status.value, test.id)

        test.updated_at = datetime.now()
        self.save_test(test)

    # === QUERY OPERATIONS ===

    def get_tests_by_goal(self, goal_id: str) -> list[Test]:
        """Get all tests for a goal."""
        test_ids = self._get_index("by_goal", goal_id)
        tests = []
        for tid in test_ids:
            t = self.load_test(goal_id, tid)
            if t: tests.append(t)
        return tests

    def get_tests_by_approval_status(self, status: ApprovalStatus) -> list[str]:
        """Get test IDs by approval status."""
        return self._get_index("by_approval", status.value)

    def get_tests_by_type(self, test_type: TestType) -> list[str]:
        """Get test IDs by test type."""
        return self._get_index("by_type", test_type.value)

    def get_tests_by_criteria(self, criteria_id: str) -> list[str]:
        """Get test IDs for a specific criteria."""
        return self._get_index("by_criteria", criteria_id)

    def get_pending_tests(self, goal_id: str) -> list[Test]:
        """Get all pending tests for a goal."""
        tests = self.get_tests_by_goal(goal_id)
        return [t for t in tests if t.approval_status == ApprovalStatus.PENDING]

    def get_approved_tests(self, goal_id: str) -> list[Test]:
        """Get all approved tests for a goal (approved or modified)."""
        tests = self.get_tests_by_goal(goal_id)
        return [t for t in tests if t.is_approved]

    def list_all_goals(self) -> list[str]:
        """List all goal IDs that have tests."""
        return [f.stem for f in (self.base_path / "indexes" / "by_goal").glob("*.json")]

    # === RESULT OPERATIONS ===

    def save_result(self, test_id: str, result: TestResult) -> None:
        """Save a test result atomically."""
        results_dir = self.base_path / "results" / test_id
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        
        data = result.model_dump_json(indent=2)
        self._atomic_write(results_dir / f"{timestamp}.json", data)
        self._atomic_write(results_dir / "latest.json", data)

    def get_latest_result(self, test_id: str) -> TestResult | None:
        latest_path = self.base_path / "results" / test_id / "latest.json"
        if not latest_path.exists(): return None
        with open(latest_path) as f:
            return TestResult.model_validate_json(f.read())

    def get_result_history(self, test_id: str, limit: int = 10) -> list[TestResult]:
        """Get result history for a test, most recent first."""
        results_dir = self.base_path / "results" / test_id
        if not results_dir.exists(): return []

        result_files = sorted(
            [f for f in results_dir.glob("*.json") if f.name != "latest.json"],
            key=lambda x: x.name,
            reverse=True
        )[:limit]

        results = []
        for f in result_files:
            try:
                results.append(TestResult.model_validate_json(f.read_text()))
            except Exception: continue
        return results

    # === INDEX OPERATIONS ===

    def _get_index(self, index_type: str, key: str) -> list[str]:
        index_path = self.base_path / "indexes" / index_type / f"{key}.json"
        if not index_path.exists(): return []
        try:
            with open(index_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _add_to_index(self, index_type: str, key: str, value: str) -> None:
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
            raise TimeoutError(f"Concurrency Lock Timeout: {index_path}")

    def _remove_from_index(self, index_type: str, key: str, value: str) -> None:
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
        """Get storage statistics as expected by the Hive test suite."""
        goals = self.list_all_goals()
        total_tests = sum(len(self._get_index("by_goal", g)) for g in goals)
        
        return {
            "total_goals": len(goals),
            "total_tests": total_tests,
            "by_approval": {
                "pending": len(self._get_index("by_approval", "pending")),
                "approved": len(self._get_index("by_approval", "approved")),
                "modified": len(self._get_index("by_approval", "modified")),
                "rejected": len(self._get_index("by_approval", "rejected")),
            },
            "storage_path": str(self.base_path),
        }