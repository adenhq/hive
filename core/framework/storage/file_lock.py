"""
Shared file-locking and atomic JSON write utilities.

Used to keep index reads/writes consistent across processes.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

if os.name == "nt":
    import msvcrt

    def _lock_file(file_obj) -> None:
        file_obj.seek(0)
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock_file(file_obj) -> None:
        file_obj.seek(0)
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock_file(file_obj) -> None:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)

    def _unlock_file(file_obj) -> None:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+") as lock_file:
        if os.name == "nt":
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write("0")
                lock_file.flush()
        _lock_file(lock_file)
        try:
            yield
        finally:
            _unlock_file(lock_file)


def atomic_write_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
