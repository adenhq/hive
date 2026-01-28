import asyncio
import shutil
import tempfile
import time

from framework.schemas.run import Run
from framework.storage.concurrent import ConcurrentStorage


async def measure_ops(storage: ConcurrentStorage, num_ops: int, concurrency: int):
    """Run concurrent save/load operations."""

    async def worker(worker_id):
        timings = []
        for i in range(num_ops // concurrency):
            run_id = f"bench_{worker_id}_{i}"
            run = Run(id=run_id, goal_id="bench", input_data={"test": i})

            start = time.perf_counter()
            await storage.save_run(run)
            save_dur = time.perf_counter() - start

            start = time.perf_counter()
            await storage.load_run(run_id)
            load_dur = time.perf_counter() - start

            timings.append(save_dur + load_dur)
        return timings

    start_total = time.perf_counter()
    tasks = [worker(i) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)
    total_dur = time.perf_counter() - start_total

    flat_timings = [t for r in results for t in r]
    avg_latency = sum(flat_timings) / len(flat_timings)
    ops_sec = num_ops / total_dur

    return ops_sec, avg_latency


async def main():
    tmp_dir = tempfile.mkdtemp()
    try:
        print(f"Benchmarking ConcurrentStorage in {tmp_dir}")
        storage = ConcurrentStorage(tmp_dir, batch_interval=0.05)
        await storage.start()

        # Warmup
        await measure_ops(storage, 100, 10)

        print("\nRunning Benchmark (1000 ops, 50 concurrency)...")
        ops, lat = await measure_ops(storage, 1000, 50)
        print(f"Throughput: {ops:.2f} OPS")
        print(f"Avg Latency: {lat * 1000:.2f} ms")

        await storage.stop()
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    asyncio.run(main())
