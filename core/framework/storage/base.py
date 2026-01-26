"""
Abstract base class for async storage backends.

Defines the contract that all storage backends must implement,
enabling pluggable storage (file-based, SQL, etc.) with a consistent API.
"""

from abc import ABC, abstractmethod
from typing import Any

from framework.schemas.run import Run, RunSummary, RunStatus


class AsyncStorageBackend(ABC):
    """
    Abstract base class for async storage backends.
    
    All storage implementations (ConcurrentStorage, SQLStorage) must
    implement this interface to ensure API compatibility.
    
    Example:
        class MyStorage(AsyncStorageBackend):
            async def start(self) -> None:
                # Initialize resources
                ...
            
            async def save_run(self, run: Run, immediate: bool = False) -> None:
                # Save to storage
                ...
    """
    
    # === Lifecycle Methods ===
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the storage backend.
        
        Called before any operations. Implementation should:
        - Initialize connections (database, file handles)
        - Start background tasks (batch writers, etc.)
        - Create tables/directories if needed
        """
        ...
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the storage backend.
        
        Called during shutdown. Implementation should:
        - Flush pending writes
        - Close connections
        - Cancel background tasks
        """
        ...
    
    # === Run Operations ===
    
    @abstractmethod
    async def save_run(self, run: Run, immediate: bool = False) -> None:
        """
        Save a run to storage.
        
        Args:
            run: Run object to save
            immediate: If True, save immediately bypassing batching
        """
        ...
    
    @abstractmethod
    async def load_run(self, run_id: str, use_cache: bool = True) -> Run | None:
        """
        Load a run from storage.
        
        Args:
            run_id: ID of the run to load
            use_cache: Whether to use cached value if available
        
        Returns:
            Run object or None if not found
        """
        ...
    
    @abstractmethod
    async def load_summary(self, run_id: str, use_cache: bool = True) -> RunSummary | None:
        """
        Load just the run summary (faster than full run).
        
        Args:
            run_id: ID of the run
            use_cache: Whether to use cached value if available
        
        Returns:
            RunSummary object or None if not found
        """
        ...
    
    @abstractmethod
    async def delete_run(self, run_id: str) -> bool:
        """
        Delete a run from storage.
        
        Args:
            run_id: ID of the run to delete
        
        Returns:
            True if deleted, False if not found
        """
        ...
    
    # === Query Operations ===
    
    @abstractmethod
    async def get_runs_by_goal(self, goal_id: str) -> list[str]:
        """
        Get all run IDs for a specific goal.
        
        Args:
            goal_id: Goal ID to query
        
        Returns:
            List of run IDs
        """
        ...
    
    @abstractmethod
    async def get_runs_by_status(self, status: str | RunStatus) -> list[str]:
        """
        Get all run IDs with a specific status.
        
        Args:
            status: Status to query (string or RunStatus enum)
        
        Returns:
            List of run IDs
        """
        ...
    
    @abstractmethod
    async def get_runs_by_node(self, node_id: str) -> list[str]:
        """
        Get all run IDs that executed a specific node.
        
        Args:
            node_id: Node ID to query
        
        Returns:
            List of run IDs
        """
        ...
    
    @abstractmethod
    async def list_all_runs(self) -> list[str]:
        """
        List all run IDs in storage.
        
        Returns:
            List of all run IDs
        """
        ...
    
    @abstractmethod
    async def list_all_goals(self) -> list[str]:
        """
        List all goal IDs that have runs.
        
        Returns:
            List of goal IDs
        """
        ...
    
    # === Utility Methods ===
    
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dict containing storage stats (total_runs, cache info, etc.)
        """
        ...
    
    # === Optional Sync Methods (for backward compatibility) ===
    
    def save_run_sync(self, run: Run) -> None:
        """
        Synchronous save (optional, for backward compatibility).
        
        Default implementation raises NotImplementedError.
        Override if sync operations are supported.
        """
        raise NotImplementedError("Sync operations not supported by this backend")
    
    def load_run_sync(self, run_id: str) -> Run | None:
        """
        Synchronous load (optional, for backward compatibility).
        
        Default implementation raises NotImplementedError.
        Override if sync operations are supported.
        """
        raise NotImplementedError("Sync operations not supported by this backend")
