#!/usr/bin/env python3
"""
Manual stress test for FileStorage/TestStorage index locking.

Spawns concurrent writer/readers against a single index file and verifies:
- reads do not crash with JSONDecodeError
- no lost updates (all expected values present)
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import random
import sys
import time
from pathlib import Path

from framework.storage.backend import FileStorage
from framework.testing.test_storage import TestStorage


def _create_storage(storage_kind: str, base_path: str):
    if storage_kind == "file":
        return FileStorage(base_path)
    if storage_kind == "test":
        return TestStorage(base_path)
    raise ValueError(f"Unknown storage kind: {storage_kind}")


def _writer_worker(
    storage_kind: str,
    base_path: str,
    index_type: str,
    key: str,
    start: int,
    count: int,
    delay_ms: int,
    queue,
):
    storage = _create_storage(storage_kind, base_path)
    try:
        for i in range(count):
            value = f"{start + i}"
            storage._add_to_index(index_type, key, value)
            if delay_ms:
                time.sleep(delay_ms / 1000.0)
        queue.put(("ok", count))
    except Exception as exc:
        queue.put(("err", f"writer error: {exc!r}"))


def _reader_worker(
    storage_kind: str,
    base_path: str,
    index_type: str,
    key: str,
    stop_event,
    delay_ms: int,
    queue,
):
    storage = _create_storage(storage_kind, base_path)
    reads = 0
    try:
        while not stop_event.is_set():
            _ = storage._get_index(index_type, key)
            reads += 1
            if delay_ms:
                time.sleep(delay_ms / 1000.0)
        queue.put(("ok", reads))
    except Exception as exc:
        queue.put(("err", f"reader error: {exc!r}"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Storage lock stress test")
    parser.add_argument(
        "--storage",
        choices=["file", "test"],
        default="file",
        help="Storage backend to test",
    )
    parser.add_argument("--writers", type=int, default=4, help="Writer process count")
    parser.add_argument("--readers", type=int, default=4, help="Reader process count")
    parser.add_argument("--values-per-writer", type=int, default=500, help="Values per writer")
    parser.add_argument("--writer-delay-ms", type=int, default=0, help="Delay per write (ms)")
    parser.add_argument("--reader-delay-ms", type=int, default=0, help="Delay per read (ms)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (0 = random)")
    parser.add_argument(
        "--base-path",
        default="",
        help="Base path for storage (default: temp dir)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.seed:
        random.seed(args.seed)
    else:
        random.seed()

    if args.base_path:
        base_path = Path(args.base_path).resolve()
        base_path.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = Path.cwd() / f".storage_lock_stress_{os.getpid()}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        base_path = tmp_dir

    index_type = "by_goal"
    key = "goal_stress"

    ctx = mp.get_context("spawn")
    writer_queue = ctx.Queue()
    reader_queue = ctx.Queue()
    stop_event = ctx.Event()

    writers = []
    readers = []

    for w in range(args.writers):
        start = w * args.values_per_writer
        proc = ctx.Process(
            target=_writer_worker,
            args=(
                args.storage,
                str(base_path),
                index_type,
                key,
                start,
                args.values_per_writer,
                args.writer_delay_ms,
                writer_queue,
            ),
        )
        writers.append(proc)

    for _ in range(args.readers):
        proc = ctx.Process(
            target=_reader_worker,
            args=(
                args.storage,
                str(base_path),
                index_type,
                key,
                stop_event,
                args.reader_delay_ms,
                reader_queue,
            ),
        )
        readers.append(proc)

    for proc in readers + writers:
        proc.start()

    writer_errors = []
    for _ in writers:
        status, payload = writer_queue.get()
        if status != "ok":
            writer_errors.append(payload)

    stop_event.set()

    reader_errors = []
    for _ in readers:
        status, payload = reader_queue.get()
        if status != "ok":
            reader_errors.append(payload)

    for proc in readers + writers:
        proc.join(timeout=10)

    if writer_errors or reader_errors:
        for err in writer_errors + reader_errors:
            print(err, file=sys.stderr)
        return 1

    storage = _create_storage(args.storage, str(base_path))
    values = storage._get_index(index_type, key)
    expected = args.writers * args.values_per_writer
    missing = expected - len(set(values))

    if missing != 0:
        print(f"ERROR: expected {expected} unique values, got {len(set(values))}", file=sys.stderr)
        return 2

    print(
        f"OK: {args.storage} | writers={args.writers} readers={args.readers} "
        f"values={expected} unique_reads={len(set(values))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
