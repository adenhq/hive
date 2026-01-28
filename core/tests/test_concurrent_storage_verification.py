import asyncio
import gc
import weakref

import pytest

from framework.storage.concurrent import ConcurrentStorage


@pytest.fixture
def storage(tmp_path):
    return ConcurrentStorage(tmp_path, max_locks=10)


@pytest.mark.asyncio
async def test_file_locks_weak_ref_behavior(storage):
    """Verify that file locks are weak referenced and garbage collected."""

    # Access a lock to create it via proper API
    lock_key = "run:test_weak_ref"

    # Use _get_lock to create/retrieve lock
    lock = await storage._get_lock(lock_key)

    assert isinstance(lock, asyncio.Lock)
    assert lock_key in storage._file_locks

    # Store a weak ref to check GC later
    weak_lock = weakref.ref(lock)

    # Delete strong reference
    del lock

    # Force garbage collection
    gc.collect()

    # Since we used _get_lock with "run:", it should be strongly referenced in _lru_tracking
    # So it should NOT be collected yet.
    assert weak_lock() is not None
    assert lock_key in storage._lru_tracking

    # Now verify eviction behavior:
    # Fill up the LRU to force eviction of our original key
    # max_locks=10. We have 1. Need 10 more to push it out.

    created_locks = []
    for i in range(15):
        key = f"run:fill_{i}"
        lock = await storage._get_lock(key)
        created_locks.append(lock)  # Keep strong ref to avoid immediate GC of new locks

    # original lock_key "run:test_weak_ref" should have been evicted from LRU
    assert lock_key not in storage._lru_tracking

    # Since we deleted our strong ref 'lock' earlier, and it's gone from LRU,
    # it should now be collectible.

    gc.collect()

    # It might take a moment or strict GC ensuring cyclic garbage works if asyncio lock has any.
    # Usually weakref callback triggers immediately.

    # Check if lock key is gone from _file_locks (WeakValueDictionary)
    # The value (lock object) should be dead.
    assert weak_lock() is None
    assert lock_key not in storage._file_locks


@pytest.mark.asyncio
async def test_lru_eviction(storage):
    """Verify strictly that LRU eviction works."""
    storage._max_locks = 5

    locks = []
    # Create 5 locks
    for i in range(5):
        key = f"run:{i}"
        lock = await storage._get_lock(key)
        locks.append(lock)

    assert len(storage._lru_tracking) == 5

    # Create 6th lock - should evict the first one (run:0)
    l5 = await storage._get_lock("run:5")
    locks.append(l5)

    assert len(storage._lru_tracking) == 5
    assert "run:0" not in storage._lru_tracking
    assert "run:5" in storage._lru_tracking

    # Verify run:0 is still in _file_locks ONLY because we hold a reference (locks[0])
    assert "run:0" in storage._file_locks

    # Release strong reference to run:0
    locks[0] = None  # Clear ref
    gc.collect()

    # Now it should be gone from WeakValueDictionary too
    assert "run:0" not in storage._file_locks
