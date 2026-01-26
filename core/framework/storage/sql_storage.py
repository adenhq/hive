"""
SQL Storage Backend - PostgreSQL-backed async storage.

Provides production-ready storage with:
- Async database operations via SQLAlchemy + asyncpg
- Connection pooling for scalability
- Read caching for performance
- Full ACID compliance

Requires:
    pip install framework[sql]
    # Or: pip install sqlalchemy[asyncio] asyncpg
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from framework.schemas.run import Run, RunSummary, RunStatus
from framework.storage.base import AsyncStorageBackend

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached value with timestamp."""
    value: Any
    timestamp: float

    def is_expired(self, ttl: float) -> bool:
        return time.time() - self.timestamp > ttl


class SQLStorage(AsyncStorageBackend):
    """
    SQL-based async storage backend using SQLAlchemy.
    
    Provides:
    - Async database operations for non-blocking I/O
    - Connection pooling for concurrent access
    - Read caching with configurable TTL
    - PostgreSQL JSONB for complex data structures
    
    Example:
        storage = SQLStorage("postgresql+asyncpg://user:pass@localhost/db")
        await storage.start()
        
        await storage.save_run(run)
        loaded_run = await storage.load_run(run_id)
        
        await storage.stop()
    
    Environment:
        Set STORAGE_TYPE=sql and DATABASE_URL to use this backend
        via the factory function.
    """
    
    def __init__(
        self,
        database_url: str,
        cache_ttl: float = 60.0,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ):
        """
        Initialize SQL storage.
        
        Args:
            database_url: SQLAlchemy async connection URL
                         (e.g., postgresql+asyncpg://user:pass@host/db)
            cache_ttl: Cache time-to-live in seconds
            pool_size: Connection pool size
            max_overflow: Max connections above pool_size
            echo: If True, log all SQL statements
        """
        self.database_url = database_url
        self._cache_ttl = cache_ttl
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._echo = echo
        
        # Lazy imports to avoid requiring SQL deps when not used
        self._engine = None
        self._session_factory = None
        
        # Caching
        self._cache: dict[str, CacheEntry] = {}
        
        # State
        self._running = False
    
    async def start(self) -> None:
        """Initialize database connection and create tables."""
        if self._running:
            return
        
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
            from framework.storage.sql_models import Base
        except ImportError as e:
            raise ImportError(
                "SQL storage requires additional dependencies. "
                "Install with: pip install framework[sql] "
                "or: pip install sqlalchemy[asyncio] asyncpg"
            ) from e
        
        self._engine = create_async_engine(
            self.database_url,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            echo=self._echo,
        )
        
        self._session_factory = async_sessionmaker(
            self._engine, 
            expire_on_commit=False,
        )
        
        # Create tables if they don't exist
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self._running = True
        logger.info(f"SQLStorage started: {self._mask_url(self.database_url)}")
    
    async def stop(self) -> None:
        """Close database connections."""
        if not self._running:
            return
        
        self._running = False
        
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
        
        logger.info("SQLStorage stopped")
    
    def _mask_url(self, url: str) -> str:
        """Mask password in database URL for logging."""
        if "@" in url and ":" in url:
            # Simple masking - replace password with ***
            parts = url.split("@")
            if len(parts) == 2:
                prefix = parts[0]
                if ":" in prefix:
                    user_part = prefix.rsplit(":", 1)[0]
                    return f"{user_part}:***@{parts[1]}"
        return url
    
    # === Run Operations ===
    
    async def save_run(self, run: Run, immediate: bool = False) -> None:
        """Save a run to the database."""
        from sqlalchemy import select
        from framework.storage.sql_models import RunModel, RunSummaryModel, RunNodeIndex
        
        async with self._session_factory() as session:
            # Check if run exists (for update vs insert)
            result = await session.execute(
                select(RunModel).where(RunModel.id == run.id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing run
                existing.goal_id = run.goal_id
                existing.status = run.status.value
                existing.started_at = run.started_at
                existing.completed_at = run.completed_at
                existing.narrative = run.narrative
                existing.goal_description = run.goal_description
                existing.input_data = run.input_data
                existing.output_data = run.output_data
                existing.decisions = [d.model_dump() for d in run.decisions]
                existing.problems = [p.model_dump() for p in run.problems]
                existing.metrics = run.metrics.model_dump()
            else:
                # Insert new run
                run_model = RunModel(
                    id=run.id,
                    goal_id=run.goal_id,
                    status=run.status.value,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    narrative=run.narrative,
                    goal_description=run.goal_description,
                    input_data=run.input_data,
                    output_data=run.output_data,
                    decisions=[d.model_dump() for d in run.decisions],
                    problems=[p.model_dump() for p in run.problems],
                    metrics=run.metrics.model_dump(),
                )
                session.add(run_model)
            
            # Update summary
            summary = RunSummary.from_run(run)
            result = await session.execute(
                select(RunSummaryModel).where(RunSummaryModel.run_id == run.id)
            )
            existing_summary = result.scalar_one_or_none()
            
            if existing_summary:
                existing_summary.goal_id = summary.goal_id
                existing_summary.status = summary.status.value
                existing_summary.duration_ms = summary.duration_ms
                existing_summary.decision_count = summary.decision_count
                existing_summary.success_rate = summary.success_rate
                existing_summary.problem_count = summary.problem_count
                existing_summary.narrative = summary.narrative
                existing_summary.key_decisions = summary.key_decisions
                existing_summary.critical_problems = summary.critical_problems
                existing_summary.warnings = summary.warnings
                existing_summary.successes = summary.successes
            else:
                summary_model = RunSummaryModel(
                    run_id=run.id,
                    goal_id=summary.goal_id,
                    status=summary.status.value,
                    duration_ms=summary.duration_ms,
                    decision_count=summary.decision_count,
                    success_rate=summary.success_rate,
                    problem_count=summary.problem_count,
                    narrative=summary.narrative,
                    key_decisions=summary.key_decisions,
                    critical_problems=summary.critical_problems,
                    warnings=summary.warnings,
                    successes=summary.successes,
                )
                session.add(summary_model)
            
            # Update node index
            if run.metrics.nodes_executed:
                # Delete existing indexes for this run
                from sqlalchemy import delete
                await session.execute(
                    delete(RunNodeIndex).where(RunNodeIndex.run_id == run.id)
                )
                
                # Insert new indexes
                for node_id in run.metrics.nodes_executed:
                    session.add(RunNodeIndex(run_id=run.id, node_id=node_id))
            
            await session.commit()
        
        # Update cache
        self._cache[f"run:{run.id}"] = CacheEntry(run, time.time())
    
    async def load_run(self, run_id: str, use_cache: bool = True) -> Run | None:
        """Load a run from the database."""
        cache_key = f"run:{run_id}"
        
        # Check cache
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired(self._cache_ttl):
                return entry.value
        
        from sqlalchemy import select
        from framework.storage.sql_models import RunModel
        from framework.schemas.decision import Decision
        from framework.schemas.run import Problem, RunMetrics
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunModel).where(RunModel.id == run_id)
            )
            row = result.scalar_one_or_none()
            
            if row is None:
                return None
            
            # Convert to Pydantic model
            run = Run(
                id=row.id,
                goal_id=row.goal_id,
                status=RunStatus(row.status),
                started_at=row.started_at,
                completed_at=row.completed_at,
                narrative=row.narrative,
                goal_description=row.goal_description,
                input_data=row.input_data or {},
                output_data=row.output_data or {},
                decisions=[Decision.model_validate(d) for d in (row.decisions or [])],
                problems=[Problem.model_validate(p) for p in (row.problems or [])],
                metrics=RunMetrics.model_validate(row.metrics or {}),
            )
        
        # Update cache
        self._cache[cache_key] = CacheEntry(run, time.time())
        
        return run
    
    async def load_summary(self, run_id: str, use_cache: bool = True) -> RunSummary | None:
        """Load just the summary (faster than full run)."""
        cache_key = f"summary:{run_id}"
        
        # Check cache
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired(self._cache_ttl):
                return entry.value
        
        from sqlalchemy import select
        from framework.storage.sql_models import RunSummaryModel
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunSummaryModel).where(RunSummaryModel.run_id == run_id)
            )
            row = result.scalar_one_or_none()
            
            if row is None:
                # Fall back to computing from full run
                run = await self.load_run(run_id, use_cache=use_cache)
                if run:
                    return RunSummary.from_run(run)
                return None
            
            summary = RunSummary(
                run_id=row.run_id,
                goal_id=row.goal_id,
                status=RunStatus(row.status),
                duration_ms=row.duration_ms,
                decision_count=row.decision_count,
                success_rate=row.success_rate,
                problem_count=row.problem_count,
                narrative=row.narrative,
                key_decisions=row.key_decisions or [],
                critical_problems=row.critical_problems or [],
                warnings=row.warnings or [],
                successes=row.successes or [],
            )
        
        # Update cache
        self._cache[cache_key] = CacheEntry(summary, time.time())
        
        return summary
    
    async def delete_run(self, run_id: str) -> bool:
        """Delete a run from the database."""
        from sqlalchemy import select, delete
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            # Check if exists first
            result = await session.execute(
                select(RunModel.id).where(RunModel.id == run_id)
            )
            if result.scalar_one_or_none() is None:
                return False
            
            # Delete (cascade will handle related tables)
            await session.execute(
                delete(RunModel).where(RunModel.id == run_id)
            )
            await session.commit()
        
        # Clear cache
        self._cache.pop(f"run:{run_id}", None)
        self._cache.pop(f"summary:{run_id}", None)
        
        return True
    
    # === Query Operations ===
    
    async def get_runs_by_goal(self, goal_id: str) -> list[str]:
        """Get all run IDs for a goal."""
        from sqlalchemy import select
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunModel.id).where(RunModel.goal_id == goal_id)
            )
            return [row[0] for row in result.fetchall()]
    
    async def get_runs_by_status(self, status: str | RunStatus) -> list[str]:
        """Get all run IDs with a status."""
        if isinstance(status, RunStatus):
            status = status.value
        
        from sqlalchemy import select
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunModel.id).where(RunModel.status == status)
            )
            return [row[0] for row in result.fetchall()]
    
    async def get_runs_by_node(self, node_id: str) -> list[str]:
        """Get all run IDs that executed a node."""
        from sqlalchemy import select
        from framework.storage.sql_models import RunNodeIndex
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunNodeIndex.run_id).where(RunNodeIndex.node_id == node_id)
            )
            return [row[0] for row in result.fetchall()]
    
    async def list_all_runs(self) -> list[str]:
        """List all run IDs."""
        from sqlalchemy import select
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            result = await session.execute(select(RunModel.id))
            return [row[0] for row in result.fetchall()]
    
    async def list_all_goals(self) -> list[str]:
        """List all goal IDs that have runs."""
        from sqlalchemy import select, distinct
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            result = await session.execute(
                select(distinct(RunModel.goal_id))
            )
            return [row[0] for row in result.fetchall()]
    
    # === Utility Methods ===
    
    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        from sqlalchemy import select, func
        from framework.storage.sql_models import RunModel
        
        async with self._session_factory() as session:
            # Count runs
            result = await session.execute(select(func.count(RunModel.id)))
            total_runs = result.scalar() or 0
            
            # Count goals
            result = await session.execute(
                select(func.count(func.distinct(RunModel.goal_id)))
            )
            total_goals = result.scalar() or 0
        
        # Cache stats
        now = time.time()
        expired = sum(
            1 for entry in self._cache.values()
            if entry.is_expired(self._cache_ttl)
        )
        
        return {
            "total_runs": total_runs,
            "total_goals": total_goals,
            "storage_type": "sql",
            "database_url": self._mask_url(self.database_url),
            "running": self._running,
            "cache": {
                "total_entries": len(self._cache),
                "expired_entries": expired,
                "valid_entries": len(self._cache) - expired,
            },
        }
    
    # === Cache Management ===
    
    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
    
    def invalidate_cache(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        self._cache.pop(key, None)
