"""Tests for ConcurrentStorage cache behavior and eviction."""

import time
from pathlib import Path

import pytest

from framework.schemas.run import Run
from framework.storage.concurrent import CacheEntry, ConcurrentStorage


def _make_storage(tmp_path: Path, **kwargs: object) -> ConcurrentStorage:
    """Helper to create a ConcurrentStorage instance for tests."""
    return ConcurrentStorage(tmp_path, **kwargs)


def test_cleanup_expired_cache_removes_entries(tmp_path: Path) -> None:
    """Expired cache entries should be removed during cleanup."""
    storage = _make_storage(tmp_path, cache_ttl=0.1)

    # Create an expired entry
    cache_key = "run:test"
    storage._cache[cache_key] = CacheEntry("value", time.time() - 1.0)

    removed = storage._cleanup_expired_cache()

    assert removed == 1
    assert cache_key not in storage._cache


def test_cache_lru_max_size_enforced(tmp_path: Path) -> None:
    """Cache should evict oldest entries when max size is exceeded."""
    storage = _make_storage(tmp_path, max_cache_size=2)

    storage._set_cache("a", "A")
    storage._set_cache("b", "B")
    storage._set_cache("c", "C")  # Should evict "a"

    assert len(storage._cache) == 2
    assert "a" not in storage._cache
    assert list(storage._cache.keys()) == ["b", "c"]


@pytest.mark.asyncio
async def test_load_run_discards_expired_cache_entry(tmp_path: Path) -> None:
    """load_run should drop expired cache entries instead of returning them."""
    storage = _make_storage(tmp_path, cache_ttl=0.1)

    # Insert an expired run into the cache
    run_id = "run_expired"
    cache_key = f"run:{run_id}"
    storage._cache[cache_key] = CacheEntry(
        Run(id=run_id, goal_id="goal"),
        time.time() - 1.0,
    )

    result = await storage.load_run(run_id, use_cache=True)

    # Base storage has no run yet, so we expect a cache miss
    assert result is None
    assert cache_key not in storage._cache

