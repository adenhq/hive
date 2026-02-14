"""flush_batch used to silently drop writes on failure which was
fun to debug.  these tests make sure it retries and logs.
"""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from framework.storage.concurrent import ConcurrentStorage


def _storage(tmp_path: Path) -> ConcurrentStorage:
    return ConcurrentStorage(tmp_path, cache_ttl=60.0, batch_interval=0.1)


class _FakeRun:
    """just needs an .id"""

    def __init__(self, rid: str):
        self.id = rid


class TestFlushBatchRetry:
    @pytest.mark.asyncio
    async def test_successful_flush_no_retry(self, tmp_path: Path):
        storage = _storage(tmp_path)
        run = _FakeRun("run_1")

        with patch.object(storage, "_save_run_locked", new_callable=AsyncMock) as mock_save:
            await storage._flush_batch([("run", run)])
            mock_save.assert_awaited_once_with(run)
            assert f"run:{run.id}" in storage._cache

    @pytest.mark.asyncio
    async def test_transient_failure_retried(self, tmp_path: Path):
        storage = _storage(tmp_path)
        run = _FakeRun("run_2")

        calls = 0

        async def flaky_save(item):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("disk full (transient)")

        with patch.object(storage, "_save_run_locked", side_effect=flaky_save):
            await storage._flush_batch([("run", run)], _max_retries=2)

        assert calls == 2
        assert f"run:{run.id}" in storage._cache

    @pytest.mark.asyncio
    async def test_permanent_failure_logged(self, tmp_path: Path, caplog):
        """if it fails all retries we should at least log the data"""
        storage = _storage(tmp_path)
        run = _FakeRun("run_3")

        async def always_fail(item):
            raise OSError("permanent disk failure")

        with (
            patch.object(storage, "_save_run_locked", side_effect=always_fail),
            caplog.at_level(logging.ERROR),
        ):
            await storage._flush_batch([("run", run)], _max_retries=2)

        assert f"run:{run.id}" not in storage._cache
        assert any("DATA DROPPED" in r.message for r in caplog.records)
        assert any("run_3" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_mixed_batch_only_failed_retried(self, tmp_path: Path):
        storage = _storage(tmp_path)
        good = _FakeRun("good")
        bad = _FakeRun("bad")

        save_count: dict[str, int] = {"good": 0, "bad": 0}

        async def selective_save(item):
            save_count[item.id] += 1
            if item.id == "bad" and save_count["bad"] < 2:
                raise OSError("transient")

        with patch.object(storage, "_save_run_locked", side_effect=selective_save):
            await storage._flush_batch([("run", good), ("run", bad)], _max_retries=2)

        assert save_count["good"] == 1  # no unnecessary retry
        assert save_count["bad"] == 2
        assert "run:good" in storage._cache
        assert "run:bad" in storage._cache

    @pytest.mark.asyncio
    async def test_empty_batch_is_noop(self, tmp_path: Path):
        storage = _storage(tmp_path)
        await storage._flush_batch([])  # should just return
