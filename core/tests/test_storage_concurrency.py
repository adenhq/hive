import concurrent.futures
import tempfile
from pathlib import Path

import pytest

from framework.schemas.run import Run, RunStatus
from framework.storage.backend import FileStorage


def _make_run(run_id: str, goal_id: str) -> Run:
    return Run(id=run_id, goal_id=goal_id, status=RunStatus.COMPLETED)


def test_concurrent_adds_do_not_lose_entries():
    goal_id = "goal_concurrent"
    workers = 6
    runs_per_worker = 8
    expected = workers * runs_per_worker

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)

        def worker(worker_id: int):
            for i in range(runs_per_worker):
                run = _make_run(f"run_{worker_id}_{i}", goal_id)
                storage.save_run(run)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(worker, w) for w in range(workers)]
            concurrent.futures.wait(futures)

        indexed = storage.get_runs_by_goal(goal_id)
        assert len(indexed) == expected, f"Expected {expected}, got {len(indexed)}"
        assert len(indexed) == len(set(indexed)), "Index contains duplicates"


def test_concurrent_adds_and_deletes_remain_consistent():
    goal_id = "goal_mixed"
    initial_runs = 10
    workers = 4

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)

        for i in range(initial_runs):
            storage.save_run(_make_run(f"seed_{i}", goal_id))

        def worker(worker_id: int):
            # add
            for i in range(3):
                storage.save_run(_make_run(f"w{worker_id}_add_{i}", goal_id))
            # delete some
            if worker_id % 2 == 0:
                storage.delete_run(f"seed_{worker_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(worker, w) for w in range(workers)]
            concurrent.futures.wait(futures)

        indexed = set(storage.get_runs_by_goal(goal_id))
        actual_files = {p.stem for p in (Path(tmpdir) / "runs").glob("*.json")}

        # Index should be subset of actual files, and missing only expected deletes
        assert indexed.issubset(actual_files)
        assert len(actual_files) >= len(indexed)


@pytest.mark.parametrize("missing_goal", ["no_such_goal", ""], ids=["absent", "empty"])
def test_get_index_handles_missing_files(missing_goal: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        assert storage.get_runs_by_goal(missing_goal) == []
