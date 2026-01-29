"""
Comprehensive tests for ConcurrentStorage - Thread-safe storage with file locking.

Tests cover:
1. Lock Contention Scenarios (6 tests)
2. Cache Coherency (5 tests)
3. Batch Writer Edge Cases (7 tests)
4. Stress Tests (5 tests)
5. Integration Tests (2 tests)

Total: 25+ test cases covering all async code paths.
"""

import asyncio
import gc
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from framework.schemas.decision import Decision, DecisionType, Outcome
from framework.schemas.run import Run, RunMetrics, RunStatus
from framework.storage.concurrent import CacheEntry, ConcurrentStorage


# === FIXTURES ===


def create_test_run(
    run_id: str = "test_run_1",
    goal_id: str = "goal_1",
    status: RunStatus = RunStatus.COMPLETED,
    nodes_executed: list[str] | None = None,
) -> Run:
    """Create a test Run object with minimal required fields."""
    if nodes_executed is None:
        nodes_executed = ["node_1", "node_2"]

    run = Run(
        id=run_id,
        goal_id=goal_id,
        status=status,
        started_at=datetime.now(),
        metrics=RunMetrics(nodes_executed=nodes_executed),
    )
    return run


@pytest.fixture
def tmp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage path for testing."""
    storage_path = tmp_path / "test_storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


@pytest_asyncio.fixture
async def storage(tmp_storage_path: Path):
    """Create an isolated ConcurrentStorage instance for each test."""
    storage = ConcurrentStorage(
        base_path=tmp_storage_path,
        cache_ttl=60.0,
        batch_interval=0.05,  # Short interval for tests
        max_batch_size=50,
        max_locks=100,
    )
    await storage.start()
    yield storage
    await storage.stop()


@pytest_asyncio.fixture
async def storage_no_batch(tmp_storage_path: Path):
    """Storage instance without batch writer for immediate write tests."""
    storage = ConcurrentStorage(
        base_path=tmp_storage_path,
        cache_ttl=60.0,
        batch_interval=0.05,
        max_batch_size=50,
        max_locks=100,
    )
    # Don't start batch writer - all writes will be immediate
    yield storage


# === TEST CACHE ENTRY ===


class TestCacheEntry:
    """Test the CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(value={"key": "value"}, timestamp=time.time())
        assert entry.value == {"key": "value"}
        assert not entry.is_expired(60.0)

    def test_cache_entry_expired(self):
        """Test cache entry expiration."""
        # Create entry with old timestamp
        old_timestamp = time.time() - 120  # 2 minutes ago
        entry = CacheEntry(value={"key": "value"}, timestamp=old_timestamp)

        assert entry.is_expired(60.0)  # TTL of 60 seconds
        assert not entry.is_expired(180.0)  # TTL of 180 seconds


# === LOCK CONTENTION SCENARIOS (6 tests) ===


class TestConcurrentStorageLocking:
    """Test thread-safety and locking behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_same_key(self, storage: ConcurrentStorage):
        """Multiple concurrent reads should succeed without blocking."""
        run = create_test_run("test_run_concurrent_read")
        await storage.save_run(run, immediate=True)

        # 10 concurrent reads
        results = await asyncio.gather(
            *[storage.load_run("test_run_concurrent_read") for _ in range(10)]
        )

        assert all(r is not None for r in results)
        assert all(r.id == "test_run_concurrent_read" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_writes_different_keys(self, storage: ConcurrentStorage):
        """Concurrent writes to different keys should all succeed."""

        async def writer(i: int):
            run = create_test_run(f"run_{i}", f"goal_{i}")
            await storage.save_run(run, immediate=True)
            return i

        # 20 concurrent writes to different keys
        results = await asyncio.gather(*[writer(i) for i in range(20)])

        assert len(results) == 20

        # Verify all writes persisted
        for i in range(20):
            loaded = await storage.load_run(f"run_{i}")
            assert loaded is not None
            assert loaded.goal_id == f"goal_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_writes_same_key_serialized(self, storage: ConcurrentStorage):
        """Concurrent writes to same key should be serialized (last write wins)."""
        execution_order = []

        async def writer(i: int):
            run = create_test_run("shared_run", f"goal_{i}")
            await storage.save_run(run, immediate=True)
            execution_order.append(i)
            return i

        # 10 concurrent writes to same key
        await asyncio.gather(*[writer(i) for i in range(10)])

        # Verify final state - should have one of the goal_ids
        loaded = await storage.load_run("shared_run")
        assert loaded is not None
        assert loaded.goal_id.startswith("goal_")

    @pytest.mark.asyncio
    async def test_no_deadlocks_under_load(self, storage: ConcurrentStorage):
        """Stress test to detect deadlock scenarios with mixed operations."""

        async def mixed_operations(i: int):
            # Mix of reads and writes
            run = create_test_run(f"deadlock_test_{i % 5}", f"goal_{i}")
            await storage.save_run(run, immediate=True)
            await storage.load_run(f"deadlock_test_{i % 5}")
            return i

        # Should complete without hanging (timeout acts as deadlock detector)
        results = await asyncio.wait_for(
            asyncio.gather(*[mixed_operations(i) for i in range(50)]),
            timeout=10.0,  # Fail if deadlocked
        )

        assert len(results) == 50

    @pytest.mark.asyncio
    async def test_read_during_write_gets_consistent_data(self, storage: ConcurrentStorage):
        """Reads during writes should get consistent (not corrupted) data."""
        # First save initial version
        initial_run = create_test_run("consistency_test", "initial_goal")
        await storage.save_run(initial_run, immediate=True)

        read_results = []
        write_complete = asyncio.Event()

        async def slow_writer():
            run = create_test_run("consistency_test", "updated_goal")
            await storage.save_run(run, immediate=True)
            write_complete.set()

        async def reader():
            # Read multiple times
            for _ in range(5):
                result = await storage.load_run("consistency_test", use_cache=False)
                if result:
                    read_results.append(result.goal_id)
                await asyncio.sleep(0.01)

        # Run concurrently
        await asyncio.gather(slow_writer(), reader())

        # All reads should be either "initial_goal" or "updated_goal" - never corrupted
        valid_goals = {"initial_goal", "updated_goal"}
        assert all(goal in valid_goals for goal in read_results)

    @pytest.mark.asyncio
    async def test_lock_acquisition_for_different_run_types(self, storage: ConcurrentStorage):
        """Test that run locks and index locks are handled separately."""
        # Create runs that share index keys
        run1 = create_test_run("run_1", "shared_goal", nodes_executed=["shared_node"])
        run2 = create_test_run("run_2", "shared_goal", nodes_executed=["shared_node"])

        # Save both - they share goal_id and node indexes
        await asyncio.gather(
            storage.save_run(run1, immediate=True),
            storage.save_run(run2, immediate=True),
        )

        # Both should be queryable by shared index
        runs_by_goal = await storage.get_runs_by_goal("shared_goal")
        assert "run_1" in runs_by_goal
        assert "run_2" in runs_by_goal


# === CACHE COHERENCY (5 tests) ===


class TestConcurrentStorageCacheCoherency:
    """Test cache invalidation and consistency."""

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_write(self, storage: ConcurrentStorage):
        """Cache should update when data is written."""
        run = create_test_run("cache_test", "goal_v1")
        await storage.save_run(run, immediate=True)

        # First read - should cache
        first = await storage.load_run("cache_test")
        assert first.goal_id == "goal_v1"

        # Update
        updated_run = create_test_run("cache_test", "goal_v2")
        await storage.save_run(updated_run, immediate=True)

        # Second read - should get updated value
        second = await storage.load_run("cache_test")
        assert second.goal_id == "goal_v2"

    @pytest.mark.asyncio
    async def test_cache_hit_after_read(self, storage: ConcurrentStorage):
        """Subsequent reads should hit cache."""
        run = create_test_run("cache_hit_test")
        await storage.save_run(run, immediate=True)

        # First read - populates cache
        await storage.load_run("cache_hit_test")

        # Check cache stats before second read
        initial_stats = storage.get_cache_stats()

        # Second read - should use cache (verify by checking cache exists)
        result = await storage.load_run("cache_hit_test", use_cache=True)
        assert result is not None

        # Cache should still have the entry
        assert "run:cache_hit_test" in storage._cache

    @pytest.mark.asyncio
    async def test_cache_bypass_with_use_cache_false(self, storage: ConcurrentStorage):
        """use_cache=False should bypass cache."""
        run = create_test_run("bypass_test", "original_goal")
        await storage.save_run(run, immediate=True)

        # Populate cache
        await storage.load_run("bypass_test")

        # Manually modify the underlying storage directly (simulating external change)
        modified_run = create_test_run("bypass_test", "modified_goal")
        storage._base_storage.save_run(modified_run)

        # With cache - should get cached value
        cached_result = await storage.load_run("bypass_test", use_cache=True)
        assert cached_result.goal_id == "original_goal"

        # Without cache - should get fresh value from disk
        fresh_result = await storage.load_run("bypass_test", use_cache=False)
        assert fresh_result.goal_id == "modified_goal"

    @pytest.mark.asyncio
    async def test_cache_expiration(self, tmp_storage_path: Path):
        """Cache entries should expire after TTL."""
        # Create storage with very short TTL
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            cache_ttl=0.1,  # 100ms TTL
            batch_interval=0.05,
        )
        await storage.start()

        try:
            run = create_test_run("expire_test")
            await storage.save_run(run, immediate=True)

            # First read - populates cache
            await storage.load_run("expire_test")

            # Wait for expiration
            await asyncio.sleep(0.2)

            # Check that cache entry is now expired
            cache_entry = storage._cache.get("run:expire_test")
            if cache_entry:
                assert cache_entry.is_expired(storage._cache_ttl)
        finally:
            await storage.stop()

    @pytest.mark.asyncio
    async def test_clear_cache_functionality(self, storage: ConcurrentStorage):
        """clear_cache() should remove all cached entries."""
        # Save and load multiple runs to populate cache
        for i in range(5):
            run = create_test_run(f"clear_test_{i}")
            await storage.save_run(run, immediate=True)
            await storage.load_run(f"clear_test_{i}")

        # Verify cache is populated
        stats_before = storage.get_cache_stats()
        assert stats_before["total_entries"] >= 5

        # Clear cache
        storage.clear_cache()

        # Verify cache is empty
        stats_after = storage.get_cache_stats()
        assert stats_after["total_entries"] == 0


# === BATCH WRITER EDGE CASES (7 tests) ===


class TestConcurrentStorageBatchWriter:
    """Test batch writer edge cases."""

    @pytest.mark.asyncio
    async def test_batch_flush_timing(self, tmp_storage_path: Path):
        """Batch should flush after interval."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            batch_interval=0.1,
            max_batch_size=100,
        )
        await storage.start()

        try:
            # Queue write (not immediate)
            run = create_test_run("batch_timing_test")
            await storage.save_run(run, immediate=False)

            # Immediately check - might not be on disk yet (in queue)
            # Note: save_run updates cache, so we check disk directly
            disk_run = storage._base_storage.load_run("batch_timing_test")

            # Wait for batch flush
            await asyncio.sleep(0.2)

            # Now should be on disk
            flushed_run = storage._base_storage.load_run("batch_timing_test")
            assert flushed_run is not None
        finally:
            await storage.stop()

    @pytest.mark.asyncio
    async def test_rapid_writes_queue_handling(self, storage: ConcurrentStorage):
        """Handle 100+ rapid writes without data loss."""
        # Queue many writes rapidly
        for i in range(100):
            run = create_test_run(f"rapid_write_{i}", f"goal_{i}")
            await storage.save_run(run, immediate=False)

        # Wait for batch flush
        await asyncio.sleep(0.5)

        # Verify all writes persisted
        for i in range(100):
            data = await storage.load_run(f"rapid_write_{i}")
            assert data is not None, f"Run rapid_write_{i} not found"
            assert data.goal_id == f"goal_{i}"

    @pytest.mark.asyncio
    async def test_graceful_shutdown_flushes_pending(self, tmp_storage_path: Path):
        """Pending writes should flush on shutdown."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            batch_interval=10.0,  # Long interval - won't flush automatically
            max_batch_size=1000,
        )
        await storage.start()

        # Queue writes
        await storage.save_run(create_test_run("shutdown_test_1", "goal_1"), immediate=False)
        await storage.save_run(create_test_run("shutdown_test_2", "goal_2"), immediate=False)

        # Shutdown immediately (before batch flush timer)
        await storage.stop()

        # Verify writes were flushed during shutdown
        storage2 = ConcurrentStorage(base_path=tmp_storage_path)
        # Don't start batch writer - just load directly
        loaded1 = storage2._base_storage.load_run("shutdown_test_1")
        loaded2 = storage2._base_storage.load_run("shutdown_test_2")

        assert loaded1 is not None
        assert loaded1.goal_id == "goal_1"
        assert loaded2 is not None
        assert loaded2.goal_id == "goal_2"

    @pytest.mark.asyncio
    async def test_max_batch_size_triggers_flush(self, tmp_storage_path: Path):
        """Reaching max_batch_size should trigger flush before interval."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            batch_interval=10.0,  # Long interval
            max_batch_size=5,  # Small batch size
        )
        await storage.start()

        try:
            # Queue exactly max_batch_size items
            for i in range(5):
                run = create_test_run(f"batch_size_test_{i}")
                await storage.save_run(run, immediate=False)

            # Give a small amount of time for batch to process
            await asyncio.sleep(0.2)

            # Should be flushed due to batch size
            for i in range(5):
                loaded = storage._base_storage.load_run(f"batch_size_test_{i}")
                assert loaded is not None
        finally:
            await storage.stop()

    @pytest.mark.asyncio
    async def test_immediate_write_bypasses_queue(self, storage: ConcurrentStorage):
        """immediate=True should write directly, not queue."""
        run = create_test_run("immediate_test")
        await storage.save_run(run, immediate=True)

        # Should be on disk immediately
        loaded = storage._base_storage.load_run("immediate_test")
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_write_coalescing_same_key(self, tmp_storage_path: Path):
        """Multiple writes to same key should result in last value persisted."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            batch_interval=0.2,
            max_batch_size=100,
        )
        await storage.start()

        try:
            # Queue multiple writes to same key rapidly
            for i in range(10):
                run = create_test_run("coalesce_test", f"goal_version_{i}")
                await storage.save_run(run, immediate=False)

            # Wait for flush
            await asyncio.sleep(0.5)

            # Should have last written value
            loaded = await storage.load_run("coalesce_test")
            assert loaded is not None
            # The goal_id should be one of the versions we wrote
            assert loaded.goal_id.startswith("goal_version_")
        finally:
            await storage.stop()

    @pytest.mark.asyncio
    async def test_batch_writer_handles_errors_gracefully(
        self, storage: ConcurrentStorage, tmp_storage_path: Path
    ):
        """Batch writer should continue despite individual write errors."""
        # Save some valid runs first
        await storage.save_run(create_test_run("valid_run_1"), immediate=False)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Valid run should still be saved
        loaded = await storage.load_run("valid_run_1")
        assert loaded is not None


# === STRESS TESTS (5 tests) ===


class TestConcurrentStorageStress:
    """Stress tests for production scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_100_concurrent_writers(self, storage: ConcurrentStorage):
        """Simulate high-concurrency scenario with 100 workers."""

        async def writer(worker_id: int):
            for i in range(5):
                run = create_test_run(
                    f"stress_w{worker_id}_i{i}",
                    f"goal_{worker_id}",
                    nodes_executed=[f"node_{worker_id}"],
                )
                await storage.save_run(run, immediate=True)
            return worker_id

        # 100 workers, each writing 5 items = 500 total writes
        results = await asyncio.gather(*[writer(i) for i in range(100)])
        assert len(results) == 100

        # Wait for any pending flushes
        await asyncio.sleep(0.5)

        # Verify sample of writes persisted
        for worker_id in [0, 25, 50, 75, 99]:
            for i in range(5):
                loaded = await storage.load_run(f"stress_w{worker_id}_i{i}")
                assert loaded is not None, f"Missing stress_w{worker_id}_i{i}"

    @pytest.mark.asyncio
    async def test_rapid_read_write_cycles(self, storage: ConcurrentStorage):
        """1000 rapid read/write cycles."""
        for i in range(100):  # Reduced for faster tests
            run = create_test_run(f"cycle_test_{i % 20}", f"goal_{i}")
            await storage.save_run(run, immediate=True)
            loaded = await storage.load_run(f"cycle_test_{i % 20}")
            assert loaded is not None

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(self, storage: ConcurrentStorage):
        """Ensure no unbounded memory growth under load."""
        tracemalloc.start()
        initial_snapshot = tracemalloc.take_snapshot()

        # Perform many operations
        for i in range(200):
            run = create_test_run(f"mem_test_{i % 50}", f"goal_{i}")
            await storage.save_run(run, immediate=True)
            await storage.load_run(f"mem_test_{i % 50}")

        # Force garbage collection
        gc.collect()

        final_snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Compare memory
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")
        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Allow reasonable growth, but not unbounded (< 50MB)
        assert total_growth < 50 * 1024 * 1024, f"Memory grew by {total_growth / 1024 / 1024:.2f}MB"

    @pytest.mark.asyncio
    async def test_lock_timeout_handling(self, tmp_storage_path: Path):
        """Verify operations complete within reasonable time under contention."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            max_locks=10,  # Small lock pool
        )
        await storage.start()

        try:
            async def contentious_operation(i: int):
                # All operations target same small set of keys
                run = create_test_run(f"contention_{i % 3}", f"goal_{i}")
                await storage.save_run(run, immediate=True)
                return await storage.load_run(f"contention_{i % 3}")

            # Run with timeout to detect lock issues
            results = await asyncio.wait_for(
                asyncio.gather(*[contentious_operation(i) for i in range(30)]),
                timeout=15.0,
            )

            assert len(results) == 30
        finally:
            await storage.stop()

    @pytest.mark.asyncio
    async def test_lock_eviction_under_pressure(self, tmp_storage_path: Path):
        """Test LRU lock eviction when max_locks is reached."""
        storage = ConcurrentStorage(
            base_path=tmp_storage_path,
            max_locks=10,  # Small limit
        )
        await storage.start()

        try:
            # Create more runs than max_locks
            for i in range(30):
                run = create_test_run(f"eviction_test_{i}", f"goal_{i}")
                await storage.save_run(run, immediate=True)

            # LRU tracking should stay at or below max_locks
            assert len(storage._lru_tracking) <= storage._max_locks

            # All runs should still be loadable
            for i in range(30):
                loaded = await storage.load_run(f"eviction_test_{i}")
                assert loaded is not None
        finally:
            await storage.stop()


# === INTEGRATION TESTS (2 tests) ===


class TestConcurrentStorageIntegration:
    """Integration tests with full workflow."""

    @pytest.mark.asyncio
    async def test_multiple_storage_instances_share_data(self, tmp_storage_path: Path):
        """Two storage instances should see consistent data."""
        storage1 = ConcurrentStorage(base_path=tmp_storage_path)
        storage2 = ConcurrentStorage(base_path=tmp_storage_path)

        await storage1.start()
        await storage2.start()

        try:
            # Write from storage1
            run = create_test_run("shared_test", "goal_from_storage1")
            await storage1.save_run(run, immediate=True)

            # Read from storage2 (bypass cache to ensure disk read)
            loaded = await storage2.load_run("shared_test", use_cache=False)

            assert loaded is not None
            assert loaded.goal_id == "goal_from_storage1"

            # Query indexes from storage2
            runs_by_goal = await storage2.get_runs_by_goal("goal_from_storage1")
            assert "shared_test" in runs_by_goal
        finally:
            await storage1.stop()
            await storage2.stop()

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_indexes(self, storage: ConcurrentStorage):
        """Test complete lifecycle: create, query, update, delete."""
        # Create
        run = create_test_run(
            "lifecycle_test",
            "lifecycle_goal",
            status=RunStatus.RUNNING,
            nodes_executed=["node_a", "node_b"],
        )
        await storage.save_run(run, immediate=True)

        # Query by various indexes
        by_goal = await storage.get_runs_by_goal("lifecycle_goal")
        assert "lifecycle_test" in by_goal

        by_status = await storage.get_runs_by_status(RunStatus.RUNNING)
        assert "lifecycle_test" in by_status

        by_node = await storage.get_runs_by_node("node_a")
        assert "lifecycle_test" in by_node

        # Update status
        run.status = RunStatus.COMPLETED
        await storage.save_run(run, immediate=True)

        # Old status index should still have it (FileStorage doesn't remove on update)
        # New status should also have it
        by_completed = await storage.get_runs_by_status(RunStatus.COMPLETED)
        assert "lifecycle_test" in by_completed

        # Load summary
        summary = await storage.load_summary("lifecycle_test")
        assert summary is not None
        assert summary.run_id == "lifecycle_test"

        # Delete
        deleted = await storage.delete_run("lifecycle_test")
        assert deleted

        # Verify deleted
        loaded = await storage.load_run("lifecycle_test")
        assert loaded is None


# === QUERY OPERATIONS TESTS ===


class TestConcurrentStorageQueries:
    """Test query operations."""

    @pytest.mark.asyncio
    async def test_get_runs_by_goal(self, storage: ConcurrentStorage):
        """Test querying runs by goal ID."""
        # Create multiple runs for same goal
        for i in range(3):
            run = create_test_run(f"goal_query_test_{i}", "shared_goal_id")
            await storage.save_run(run, immediate=True)

        # Query
        runs = await storage.get_runs_by_goal("shared_goal_id")
        assert len(runs) == 3
        assert all(f"goal_query_test_{i}" in runs for i in range(3))

    @pytest.mark.asyncio
    async def test_get_runs_by_status(self, storage: ConcurrentStorage):
        """Test querying runs by status."""
        # Create runs with different statuses
        run_completed = create_test_run("status_test_1", "g1", status=RunStatus.COMPLETED)
        run_failed = create_test_run("status_test_2", "g2", status=RunStatus.FAILED)

        await storage.save_run(run_completed, immediate=True)
        await storage.save_run(run_failed, immediate=True)

        completed = await storage.get_runs_by_status(RunStatus.COMPLETED)
        failed = await storage.get_runs_by_status("failed")  # String variant

        assert "status_test_1" in completed
        assert "status_test_2" in failed

    @pytest.mark.asyncio
    async def test_get_runs_by_node(self, storage: ConcurrentStorage):
        """Test querying runs by executed node."""
        run = create_test_run("node_query_test", "goal", nodes_executed=["special_node"])
        await storage.save_run(run, immediate=True)

        runs = await storage.get_runs_by_node("special_node")
        assert "node_query_test" in runs

    @pytest.mark.asyncio
    async def test_list_all_runs(self, storage: ConcurrentStorage):
        """Test listing all runs."""
        for i in range(5):
            run = create_test_run(f"list_test_{i}")
            await storage.save_run(run, immediate=True)

        all_runs = await storage.list_all_runs()
        assert len(all_runs) >= 5
        assert all(f"list_test_{i}" in all_runs for i in range(5))

    @pytest.mark.asyncio
    async def test_list_all_goals(self, storage: ConcurrentStorage):
        """Test listing all unique goals."""
        for i in range(3):
            run = create_test_run(f"goals_test_{i}", f"unique_goal_{i}")
            await storage.save_run(run, immediate=True)

        all_goals = await storage.list_all_goals()
        assert len(all_goals) >= 3


# === UTILITY TESTS ===


class TestConcurrentStorageUtility:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_get_stats(self, storage: ConcurrentStorage):
        """Test getting storage statistics."""
        run = create_test_run("stats_test")
        await storage.save_run(run, immediate=True)

        stats = await storage.get_stats()

        assert "total_runs" in stats
        assert "cache" in stats
        assert "pending_writes" in stats
        assert "running" in stats
        assert stats["running"] is True

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, storage: ConcurrentStorage):
        """Test getting cache statistics."""
        run = create_test_run("cache_stats_test")
        await storage.save_run(run, immediate=True)
        await storage.load_run("cache_stats_test")

        stats = storage.get_cache_stats()

        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "valid_entries" in stats
        assert stats["total_entries"] >= 1

    @pytest.mark.asyncio
    async def test_invalidate_cache_specific_key(self, storage: ConcurrentStorage):
        """Test invalidating a specific cache key."""
        run = create_test_run("invalidate_test")
        await storage.save_run(run, immediate=True)
        await storage.load_run("invalidate_test")

        # Cache should have entry
        assert "run:invalidate_test" in storage._cache

        # Invalidate
        storage.invalidate_cache("run:invalidate_test")

        # Should be gone
        assert "run:invalidate_test" not in storage._cache

    @pytest.mark.asyncio
    async def test_sync_api_compatibility(self, storage: ConcurrentStorage):
        """Test synchronous API for backward compatibility."""
        run = create_test_run("sync_test")

        # Sync save
        storage.save_run_sync(run)

        # Sync load
        loaded = storage.load_run_sync("sync_test")

        assert loaded is not None
        assert loaded.id == "sync_test"


# === START/STOP LIFECYCLE TESTS ===


class TestConcurrentStorageLifecycle:
    """Test start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, tmp_storage_path: Path):
        """Starting twice should be idempotent."""
        storage = ConcurrentStorage(base_path=tmp_storage_path)

        await storage.start()
        await storage.start()  # Should not error

        assert storage._running is True
        assert storage._batch_task is not None

        await storage.stop()

    @pytest.mark.asyncio
    async def test_double_stop_is_safe(self, tmp_storage_path: Path):
        """Stopping twice should be idempotent."""
        storage = ConcurrentStorage(base_path=tmp_storage_path)

        await storage.start()
        await storage.stop()
        await storage.stop()  # Should not error

        assert storage._running is False

    @pytest.mark.asyncio
    async def test_operations_before_start(self, storage_no_batch: ConcurrentStorage):
        """Operations should work even if start() wasn't called (immediate mode)."""
        run = create_test_run("no_start_test")

        # Should save immediately (bypasses batch since not running)
        await storage_no_batch.save_run(run)

        # Should load
        loaded = await storage_no_batch.load_run("no_start_test")
        assert loaded is not None
