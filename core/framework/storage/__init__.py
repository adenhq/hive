"""Storage backends for runtime data.

Available backends:
- FileStorage: Simple file-based storage (sync)
- ConcurrentStorage: Thread-safe file storage with caching (async)
- SQLStorage: PostgreSQL-backed storage (async, requires sql extras)

Factory:
- get_storage(): Creates appropriate backend based on environment
"""

from framework.storage.backend import FileStorage
from framework.storage.base import AsyncStorageBackend
from framework.storage.concurrent import ConcurrentStorage
from framework.storage.factory import get_storage

__all__ = [
    "FileStorage",
    "AsyncStorageBackend", 
    "ConcurrentStorage",
    "get_storage",
]

# SQLStorage is not exported by default to avoid import errors
# when SQL dependencies are not installed. Import directly:
#   from framework.storage.sql_storage import SQLStorage
