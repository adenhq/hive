import multiprocessing as mp
import time

import pytest

from framework.storage.backend import FileStorage
from framework.storage.file_lock import file_lock
from framework.testing.test_storage import TestStorage


def _create_storage(storage_kind: str, base_path: str):
    if storage_kind == "file":
        return FileStorage(base_path)
    if storage_kind == "test":
        return TestStorage(base_path)
    raise ValueError(f"Unknown storage kind: {storage_kind}")


def _get_index_worker(storage_kind: str, base_path: str, index_type: str, key: str, queue):
    storage = _create_storage(storage_kind, base_path)
    try:
        values = storage._get_index(index_type, key)
        queue.put(("ok", values))
    except Exception as exc:  # pragma: no cover - only used for debug signaling
        queue.put(("err", repr(exc)))


def _add_index_worker(
    storage_kind: str,
    base_path: str,
    index_type: str,
    key: str,
    value: str,
    queue,
):
    storage = _create_storage(storage_kind, base_path)
    try:
        storage._add_to_index(index_type, key, value)
        queue.put(("ok", None))
    except Exception as exc:  # pragma: no cover - only used for debug signaling
        queue.put(("err", repr(exc)))


@pytest.mark.parametrize("storage_kind", ["file", "test"])
def test_get_index_blocks_while_lock_held(storage_kind, tmp_path):
    storage = _create_storage(storage_kind, str(tmp_path))
    index_type = "by_goal"
    key = "goal_1"
    storage._add_to_index(index_type, key, "value_1")

    index_path = tmp_path / "indexes" / index_type / f"{key}.json"
    lock_path = index_path.with_suffix(index_path.suffix + ".lock")

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(
        target=_get_index_worker,
        args=(storage_kind, str(tmp_path), index_type, key, queue),
    )

    with file_lock(lock_path):
        proc.start()
        time.sleep(0.2)
        assert queue.empty(), "read completed while lock was held"

    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        pytest.fail("reader process did not finish after lock release")

    status, payload = queue.get(timeout=2)
    assert status == "ok", payload
    assert payload == ["value_1"]


@pytest.mark.parametrize("storage_kind", ["file", "test"])
def test_add_index_blocks_while_lock_held(storage_kind, tmp_path):
    storage = _create_storage(storage_kind, str(tmp_path))
    index_type = "by_goal"
    key = "goal_2"

    index_path = tmp_path / "indexes" / index_type / f"{key}.json"
    lock_path = index_path.with_suffix(index_path.suffix + ".lock")

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(
        target=_add_index_worker,
        args=(storage_kind, str(tmp_path), index_type, key, "value_2", queue),
    )

    with file_lock(lock_path):
        proc.start()
        time.sleep(0.2)
        assert queue.empty(), "write completed while lock was held"

    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        pytest.fail("writer process did not finish after lock release")

    status, payload = queue.get(timeout=2)
    assert status == "ok", payload
    assert storage._get_index(index_type, key) == ["value_2"]
