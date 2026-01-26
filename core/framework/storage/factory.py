"""
Storage factory - Creates the appropriate storage backend.

Provides a unified factory function that returns the correct
storage implementation based on environment configuration.

Environment Variables:
    STORAGE_TYPE: 'file' (default) or 'sql'
    DATABASE_URL: Connection string for SQL storage

Usage:
    storage = get_storage()  # Uses env vars
    await storage.start()
    
    # Or with explicit config
    storage = get_storage(base_path="./data")
"""

import os
import logging
from pathlib import Path
from typing import Any

from framework.storage.base import AsyncStorageBackend
from framework.storage.concurrent import ConcurrentStorage

logger = logging.getLogger(__name__)


def get_storage(
    base_path: str | Path | None = None,
    cache_ttl: float = 60.0,
    batch_interval: float = 0.1,
    max_batch_size: int = 100,
    **kwargs: Any,
) -> AsyncStorageBackend:
    """
    Factory function to get the appropriate storage backend.
    
    Checks environment variables to determine which backend to use:
    - STORAGE_TYPE='file' (default): Uses ConcurrentStorage (file-based)
    - STORAGE_TYPE='sql': Uses SQLStorage (PostgreSQL)
    
    Args:
        base_path: Base path for file storage (ignored for SQL)
        cache_ttl: Cache time-to-live in seconds
        batch_interval: Batch flush interval (file storage only)
        max_batch_size: Max batch size (file storage only)
        **kwargs: Additional arguments for specific backends
            - pool_size: SQL connection pool size (default: 5)
            - max_overflow: SQL max overflow connections (default: 10)
            - echo: SQL echo mode for debugging (default: False)
    
    Returns:
        Configured AsyncStorageBackend instance
    
    Raises:
        ValueError: If STORAGE_TYPE='sql' but DATABASE_URL is not set
    
    Example:
        # Default (file storage)
        storage = get_storage(base_path="./data")
        
        # SQL storage via environment
        # export STORAGE_TYPE=sql
        # export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
        storage = get_storage()
        
        # Explicit SQL storage
        from framework.storage.sql_storage import SQLStorage
        storage = SQLStorage(database_url="postgresql+asyncpg://...")
    """
    storage_type = os.environ.get("STORAGE_TYPE", "file").lower()
    
    if storage_type == "sql":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable required when STORAGE_TYPE='sql'. "
                "Set DATABASE_URL to a valid SQLAlchemy async connection string, e.g.: "
                "postgresql+asyncpg://user:password@localhost:5432/database"
            )
        
        # Lazy import to avoid requiring SQL deps when not used
        from framework.storage.sql_storage import SQLStorage
        
        storage = SQLStorage(
            database_url=database_url,
            cache_ttl=cache_ttl,
            pool_size=kwargs.get("pool_size", 5),
            max_overflow=kwargs.get("max_overflow", 10),
            echo=kwargs.get("echo", False),
        )
        logger.info(f"Created SQLStorage backend")
        return storage
    
    # Default to file storage
    if base_path is None:
        base_path = Path("./storage")
    
    storage = ConcurrentStorage(
        base_path=base_path,
        cache_ttl=cache_ttl,
        batch_interval=batch_interval,
        max_batch_size=max_batch_size,
    )
    logger.info(f"Created ConcurrentStorage backend at {base_path}")
    return storage
