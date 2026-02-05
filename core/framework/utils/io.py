import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_write(path: Path, mode: str = "w", encoding: str = "utf-8"):
    """
    Atomically write to a file using a temporary file and rename.

    Creates parent directories if needed and validates write permissions
    before attempting the write operation.

    Args:
        path: Target file path
        mode: File open mode (default: "w")
        encoding: Text encoding (default: "utf-8")

    Raises:
        PermissionError: If write permission is denied
        OSError: If parent directory cannot be created or file cannot be written
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Check write permission on existing file
    if path.exists() and not os.access(path, os.W_OK):
        raise PermissionError(f"No write permission for {path}")

    # Check write permission on parent directory for new files
    if not path.exists() and not os.access(path.parent, os.W_OK):
        raise PermissionError(f"No write permission in directory {path.parent}")

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, mode, encoding=encoding) as f:
            yield f
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename - on POSIX this is atomic even if destination exists
        tmp_path.replace(path)
    except Exception:
        # Clean up temporary file on any error
        tmp_path.unlink(missing_ok=True)
        raise
