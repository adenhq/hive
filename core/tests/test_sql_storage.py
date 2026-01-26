"""
Tests for SQL Storage Backend.

Tests the SQLStorage class using SQLite in-memory database
for fast, isolated testing without requiring PostgreSQL.

Requires: pip install aiosqlite
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import os

from framework.schemas.run import Run, RunSummary, RunStatus, RunMetrics, Problem
from framework.schemas.decision import Decision, Option, Outcome, DecisionType
from framework.storage.base import AsyncStorageBackend
from framework.storage.concurrent import ConcurrentStorage
from framework.storage.factory import get_storage


# === Fixtures ===

@pytest.fixture
def sample_run() -> Run:
    """Create a sample run for testing."""
    run = Run(
        id="test_run_123",
        goal_id="test_goal",
        started_at=datetime.now(),
        goal_description="Test goal description",
        input_data={"key": "value"},
    )
    
    # Add a decision
    decision = Decision(
        id="dec_0",
        intent="Test decision",
        decision_type=DecisionType.TOOL_SELECTION,
        node_id="test_node",
        options=[Option(id="opt1", description="Option 1", action_type="tool_call")],
        chosen_option_id="opt1",
        reasoning="Test reasoning",
    )
    decision.outcome = Outcome(
        success=True,
        summary="Test outcome",
        tokens_used=100,
        latency_ms=50,
    )
    run.decisions.append(decision)
    
    # Update metrics
    run.metrics.total_decisions = 1
    run.metrics.successful_decisions = 1
    run.metrics.nodes_executed = ["test_node"]
    
    return run


@pytest.fixture
def completed_run(sample_run: Run) -> Run:
    """Create a completed run for testing."""
    sample_run.complete(RunStatus.COMPLETED, "Test completed successfully")
    sample_run.output_data = {"result": "success"}
    return sample_run


# === Test ConcurrentStorage implements AsyncStorageBackend ===

class TestAsyncStorageBackendInterface:
    """Test that ConcurrentStorage properly implements AsyncStorageBackend."""
    
    def test_concurrent_storage_is_async_backend(self, tmp_path: Path):
        """ConcurrentStorage should be an instance of AsyncStorageBackend."""
        storage = ConcurrentStorage(base_path=tmp_path)
        assert isinstance(storage, AsyncStorageBackend)
    
    def test_interface_methods_exist(self, tmp_path: Path):
        """All interface methods should exist on ConcurrentStorage."""
        storage = ConcurrentStorage(base_path=tmp_path)
        
        # Lifecycle
        assert hasattr(storage, 'start')
        assert hasattr(storage, 'stop')
        
        # Run operations
        assert hasattr(storage, 'save_run')
        assert hasattr(storage, 'load_run')
        assert hasattr(storage, 'load_summary')
        assert hasattr(storage, 'delete_run')
        
        # Query operations
        assert hasattr(storage, 'get_runs_by_goal')
        assert hasattr(storage, 'get_runs_by_status')
        assert hasattr(storage, 'get_runs_by_node')
        assert hasattr(storage, 'list_all_runs')
        assert hasattr(storage, 'list_all_goals')
        
        # Utility
        assert hasattr(storage, 'get_stats')


# === Test Factory Function ===

class TestStorageFactory:
    """Test the get_storage factory function."""
    
    def test_default_returns_concurrent_storage(self, tmp_path: Path):
        """Factory should return ConcurrentStorage by default."""
        # Ensure no SQL env vars
        with patch.dict(os.environ, {}, clear=True):
            storage = get_storage(base_path=tmp_path)
            assert isinstance(storage, ConcurrentStorage)
    
    def test_file_type_returns_concurrent_storage(self, tmp_path: Path):
        """Factory should return ConcurrentStorage when STORAGE_TYPE=file."""
        with patch.dict(os.environ, {"STORAGE_TYPE": "file"}, clear=True):
            storage = get_storage(base_path=tmp_path)
            assert isinstance(storage, ConcurrentStorage)
    
    def test_sql_type_without_url_raises(self):
        """Factory should raise ValueError when STORAGE_TYPE=sql but no DATABASE_URL."""
        with patch.dict(os.environ, {"STORAGE_TYPE": "sql"}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL"):
                get_storage()
    
    def test_default_path_when_none(self):
        """Factory should use default path when base_path is None."""
        with patch.dict(os.environ, {}, clear=True):
            storage = get_storage()
            assert isinstance(storage, ConcurrentStorage)
            assert storage.base_path == Path("./storage")


# === Test ConcurrentStorage Async Operations ===

class TestConcurrentStorageAsync:
    """Test ConcurrentStorage async operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_run(self, tmp_path: Path, completed_run: Run):
        """Test saving and loading a run."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            # Save
            await storage.save_run(completed_run, immediate=True)
            
            # Load
            loaded = await storage.load_run(completed_run.id)
            
            assert loaded is not None
            assert loaded.id == completed_run.id
            assert loaded.goal_id == completed_run.goal_id
            assert loaded.status == completed_run.status
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_run(self, tmp_path: Path):
        """Loading a nonexistent run should return None."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            result = await storage.load_run("nonexistent_id")
            assert result is None
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_load_summary(self, tmp_path: Path, completed_run: Run):
        """Test loading run summary."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            summary = await storage.load_summary(completed_run.id)
            
            assert summary is not None
            assert summary.run_id == completed_run.id
            assert summary.goal_id == completed_run.goal_id
            assert summary.status == completed_run.status
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_delete_run(self, tmp_path: Path, completed_run: Run):
        """Test deleting a run."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            # Verify exists
            assert await storage.load_run(completed_run.id) is not None
            
            # Delete
            result = await storage.delete_run(completed_run.id)
            assert result is True
            
            # Verify gone
            assert await storage.load_run(completed_run.id) is None
            
            # Delete again should return False
            result = await storage.delete_run(completed_run.id)
            assert result is False
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_query_by_goal(self, tmp_path: Path, completed_run: Run):
        """Test querying runs by goal."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            run_ids = await storage.get_runs_by_goal(completed_run.goal_id)
            
            assert completed_run.id in run_ids
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_query_by_status(self, tmp_path: Path, completed_run: Run):
        """Test querying runs by status."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            run_ids = await storage.get_runs_by_status(RunStatus.COMPLETED)
            
            assert completed_run.id in run_ids
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_query_by_node(self, tmp_path: Path, completed_run: Run):
        """Test querying runs by node."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            run_ids = await storage.get_runs_by_node("test_node")
            
            assert completed_run.id in run_ids
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_list_all_runs(self, tmp_path: Path, completed_run: Run):
        """Test listing all runs."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            run_ids = await storage.list_all_runs()
            
            assert completed_run.id in run_ids
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_list_all_goals(self, tmp_path: Path, completed_run: Run):
        """Test listing all goals."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            goal_ids = await storage.list_all_goals()
            
            assert completed_run.goal_id in goal_ids
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, tmp_path: Path, completed_run: Run):
        """Test getting storage stats."""
        storage = ConcurrentStorage(base_path=tmp_path)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            stats = await storage.get_stats()
            
            assert stats["total_runs"] == 1
            assert stats["total_goals"] == 1
            assert "cache" in stats
        finally:
            await storage.stop()
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, tmp_path: Path, completed_run: Run):
        """Test that cache is used on subsequent loads."""
        storage = ConcurrentStorage(base_path=tmp_path, cache_ttl=60.0)
        await storage.start()
        
        try:
            await storage.save_run(completed_run, immediate=True)
            
            # First load populates cache
            await storage.load_run(completed_run.id)
            
            # Check cache stats
            cache_stats = storage.get_cache_stats()
            assert cache_stats["valid_entries"] >= 1
        finally:
            await storage.stop()


# === Optional: SQL Storage Tests (requires aiosqlite) ===

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite not installed")
class TestSQLStorage:
    """Test SQLStorage with SQLite in-memory database."""
    
    @pytest.fixture
    async def sql_storage(self):
        """Create SQLStorage with in-memory SQLite."""
        from framework.storage.sql_storage import SQLStorage
        
        storage = SQLStorage(
            database_url="sqlite+aiosqlite:///:memory:",
            cache_ttl=60.0,
        )
        await storage.start()
        yield storage
        await storage.stop()
    
    @pytest.mark.asyncio
    async def test_sql_storage_save_and_load(self, sql_storage, completed_run: Run):
        """Test SQLStorage save and load."""
        await sql_storage.save_run(completed_run)
        
        loaded = await sql_storage.load_run(completed_run.id)
        
        assert loaded is not None
        assert loaded.id == completed_run.id
        assert loaded.goal_id == completed_run.goal_id
    
    @pytest.mark.asyncio
    async def test_sql_storage_load_summary(self, sql_storage, completed_run: Run):
        """Test SQLStorage load summary."""
        await sql_storage.save_run(completed_run)
        
        summary = await sql_storage.load_summary(completed_run.id)
        
        assert summary is not None
        assert summary.run_id == completed_run.id
    
    @pytest.mark.asyncio
    async def test_sql_storage_delete(self, sql_storage, completed_run: Run):
        """Test SQLStorage delete."""
        await sql_storage.save_run(completed_run)
        
        result = await sql_storage.delete_run(completed_run.id)
        assert result is True
        
        loaded = await sql_storage.load_run(completed_run.id)
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_sql_storage_queries(self, sql_storage, completed_run: Run):
        """Test SQLStorage query methods."""
        await sql_storage.save_run(completed_run)
        
        # Query by goal
        runs = await sql_storage.get_runs_by_goal(completed_run.goal_id)
        assert completed_run.id in runs
        
        # Query by status
        runs = await sql_storage.get_runs_by_status(RunStatus.COMPLETED)
        assert completed_run.id in runs
        
        # Query by node
        runs = await sql_storage.get_runs_by_node("test_node")
        assert completed_run.id in runs
        
        # List all
        runs = await sql_storage.list_all_runs()
        assert completed_run.id in runs
        
        goals = await sql_storage.list_all_goals()
        assert completed_run.goal_id in goals
    
    @pytest.mark.asyncio
    async def test_sql_storage_stats(self, sql_storage, completed_run: Run):
        """Test SQLStorage stats."""
        await sql_storage.save_run(completed_run)
        
        stats = await sql_storage.get_stats()
        
        assert stats["total_runs"] == 1
        assert stats["storage_type"] == "sql"
    
    @pytest.mark.asyncio
    async def test_sql_storage_update_run(self, sql_storage, sample_run: Run):
        """Test SQLStorage update existing run."""
        # Save initial
        await sql_storage.save_run(sample_run)
        
        # Update
        sample_run.narrative = "Updated narrative"
        sample_run.complete(RunStatus.COMPLETED)
        await sql_storage.save_run(sample_run)
        
        # Load and verify
        loaded = await sql_storage.load_run(sample_run.id)
        assert loaded.narrative == "Updated narrative"
        assert loaded.status == RunStatus.COMPLETED
