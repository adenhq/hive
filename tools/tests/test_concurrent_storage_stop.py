import asyncio
import pytest
from framework.storage.concurrent import ConcurrentStorage
from framework.schemas.run import Run

@pytest.mark.asyncio
async def test_stop_flushes_pending(tmp_path):
    """Test that ConcurrentStorage.stop() flushes all pending writes."""
    storage = ConcurrentStorage(base_path=tmp_path)
    await storage.start()

    # Add runs to the queue
    run1 = Run(id="run1", goal_id="goal1")
    run2 = Run(id="run2", goal_id="goal2")
    await storage.save_run(run1)
    await storage.save_run(run2)

    await storage.stop()

    # Check runs are persisted
    loaded_run1 = await storage.load_run("run1", use_cache=False)
    loaded_run2 = await storage.load_run("run2", use_cache=False)
    assert loaded_run1 is not None, "Run1 was not flushed"
    assert loaded_run2 is not None, "Run2 was not flushed"

    # Queue should be empty
    assert storage._write_queue.empty(), "Write queue is not empty after stop"

@pytest.mark.asyncio
async def test_stop_empty_queue(tmp_path):
    """Stopping with an empty queue should not raise errors and batch task is cleared."""
    storage = ConcurrentStorage(base_path=tmp_path)
    await storage.start()
    await storage.stop()

    assert storage._write_queue.empty(), "Queue should still be empty"
    assert storage._batch_task is None, "_batch_task should be None after stop"

@pytest.mark.asyncio
async def test_stop_while_writes_in_progress(tmp_path):
    """Test stopping while writes are being added asynchronously."""
    storage = ConcurrentStorage(base_path=tmp_path)
    await storage.start()

    async def add_runs():
        for i in range(5):
            run = Run(id=f"run{i}", goal_id=f"goal{i}")
            await storage.save_run(run)
            await asyncio.sleep(0.05)  # simulate delay in writing

    # Schedule adding runs
    add_task = asyncio.create_task(add_runs())

    # Stop storage while runs are being added
    await asyncio.sleep(0.1)
    await storage.stop()

    # Ensure all runs were flushed
    for i in range(5):
        loaded = await storage.load_run(f"run{i}", use_cache=False)
        assert loaded is not None, f"Run{i} was not flushed"

    # Queue empty and batch task cleared
    assert storage._write_queue.empty(), "Queue not empty after stop"
    assert storage._batch_task is None, "_batch_task not None after stop"

@pytest.mark.asyncio
async def test_stop_during_heavy_concurrent_writes(tmp_path):
    """
    Stress test: multiple writes happen concurrently while stop() is called.
    Ensures no runs are lost and the queue is fully flushed.
    """
    storage = ConcurrentStorage(base_path=tmp_path)
    await storage.start()

    async def add_runs_concurrently(start: int, end: int):
        for i in range(start, end):
            run = Run(id=f"run{i}", goal_id=f"goal{i}")
            await storage.save_run(run)
            await asyncio.sleep(0.01)  # simulate staggered writes

    # Schedule multiple concurrent writers
    writers = [asyncio.create_task(add_runs_concurrently(i*10, (i+1)*10)) for i in range(5)]

    # Stop storage while writes are happening
    await asyncio.sleep(0.05)
    await storage.stop()

    # Wait for all writer tasks to finish
    await asyncio.gather(*writers, return_exceptions=True)

    # Check all runs were flushed
    for i in range(50):
        loaded = await storage.load_run(f"run{i}", use_cache=False)
        assert loaded is not None, f"Run{i} was not flushed"

    # Ensure queue is empty and batch task cleared
    assert storage._write_queue.empty(), "Queue not empty after stop"
    assert storage._batch_task is None, "_batch_task not None after stop"
