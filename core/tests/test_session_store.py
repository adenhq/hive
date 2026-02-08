"""Tests for SessionStore - unified session storage with state.json."""

import re

import pytest

from framework.schemas.session_state import (
    SessionProgress,
    SessionResult,
    SessionState,
    SessionStatus,
    SessionTimestamps,
)
from framework.storage.session_store import SessionStore

# === HELPERS ===


def make_session_state(
    session_id: str = "session_20260208_120000_abc12345",
    goal_id: str = "test_goal",
    status: SessionStatus = SessionStatus.COMPLETED,
) -> SessionState:
    """Create a minimal SessionState for testing."""
    return SessionState(
        session_id=session_id,
        goal_id=goal_id,
        status=status,
        timestamps=SessionTimestamps(
            started_at="2026-02-08T12:00:00",
            updated_at="2026-02-08T12:01:00",
        ),
    )


# === TESTS ===


class TestSessionStoreInit:
    """Test SessionStore initialization."""

    def test_init_sets_paths(self, tmp_path):
        """Store should set base_path and sessions_dir."""
        store = SessionStore(tmp_path / "agent")

        assert store.base_path == tmp_path / "agent"
        assert store.sessions_dir == tmp_path / "agent" / "sessions"


class TestSessionStoreGenerateId:
    """Test session ID generation."""

    def test_generate_session_id_format(self, tmp_path):
        """Session ID should match format: session_YYYYMMDD_HHMMSS_{uuid8}."""
        store = SessionStore(tmp_path)

        session_id = store.generate_session_id()

        pattern = r"^session_\d{8}_\d{6}_[a-f0-9]{8}$"
        assert re.match(pattern, session_id), f"ID '{session_id}' doesn't match expected format"

    def test_generate_session_id_unique(self, tmp_path):
        """Each generated ID should be unique."""
        store = SessionStore(tmp_path)

        ids = {store.generate_session_id() for _ in range(100)}

        assert len(ids) == 100


class TestSessionStorePaths:
    """Test path construction methods."""

    def test_get_session_path(self, tmp_path):
        """Session path should be sessions_dir / session_id."""
        store = SessionStore(tmp_path)
        sid = "session_20260208_120000_abc12345"

        path = store.get_session_path(sid)

        assert path == tmp_path / "sessions" / sid

    def test_get_state_path(self, tmp_path):
        """State path should be session_path / state.json."""
        store = SessionStore(tmp_path)
        sid = "session_20260208_120000_abc12345"

        path = store.get_state_path(sid)

        assert path == tmp_path / "sessions" / sid / "state.json"


class TestSessionStoreWriteRead:
    """Test write_state and read_state operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_state(self, tmp_path):
        """Writing and reading state should roundtrip correctly."""
        store = SessionStore(tmp_path)
        state = make_session_state()

        await store.write_state(state.session_id, state)
        loaded = await store.read_state(state.session_id)

        assert loaded is not None
        assert loaded.session_id == state.session_id
        assert loaded.goal_id == state.goal_id
        assert loaded.status == state.status

    @pytest.mark.asyncio
    async def test_write_creates_state_json(self, tmp_path):
        """write_state should create the state.json file on disk."""
        store = SessionStore(tmp_path)
        state = make_session_state()

        await store.write_state(state.session_id, state)

        state_path = store.get_state_path(state.session_id)
        assert state_path.exists()

    @pytest.mark.asyncio
    async def test_write_creates_parent_directories(self, tmp_path):
        """write_state should create session directory if needed."""
        store = SessionStore(tmp_path)
        state = make_session_state()

        # Directory doesn't exist yet
        assert not store.sessions_dir.exists()

        await store.write_state(state.session_id, state)

        assert store.sessions_dir.exists()
        assert store.get_session_path(state.session_id).exists()

    @pytest.mark.asyncio
    async def test_read_nonexistent_returns_none(self, tmp_path):
        """Reading a session that doesn't exist should return None."""
        store = SessionStore(tmp_path)

        result = await store.read_state("nonexistent_session")

        assert result is None

    @pytest.mark.asyncio
    async def test_write_preserves_all_fields(self, tmp_path):
        """All SessionState fields should survive write/read roundtrip."""
        store = SessionStore(tmp_path)
        state = SessionState(
            session_id="session_20260208_120000_abc12345",
            goal_id="complex_goal",
            status=SessionStatus.PAUSED,
            agent_id="agent_1",
            entry_point="research",
            timestamps=SessionTimestamps(
                started_at="2026-02-08T12:00:00",
                updated_at="2026-02-08T12:05:00",
                paused_at_time="2026-02-08T12:05:00",
            ),
            progress=SessionProgress(
                current_node="research",
                paused_at="research",
                resume_from="research",
                steps_executed=5,
                total_tokens=1500,
                path=["start", "plan", "research"],
            ),
            result=SessionResult(success=None),
            memory={"key": "value", "count": 42},
            input_data={"query": "test input"},
        )

        await store.write_state(state.session_id, state)
        loaded = await store.read_state(state.session_id)

        assert loaded is not None
        assert loaded.agent_id == "agent_1"
        assert loaded.entry_point == "research"
        assert loaded.progress.steps_executed == 5
        assert loaded.progress.total_tokens == 1500
        assert loaded.progress.path == ["start", "plan", "research"]
        assert loaded.memory == {"key": "value", "count": 42}
        assert loaded.input_data == {"query": "test input"}

    @pytest.mark.asyncio
    async def test_write_overwrites_existing(self, tmp_path):
        """Writing to the same session_id should overwrite the previous state."""
        store = SessionStore(tmp_path)
        sid = "session_20260208_120000_abc12345"

        state_v1 = make_session_state(session_id=sid, status=SessionStatus.ACTIVE)
        await store.write_state(sid, state_v1)

        state_v2 = make_session_state(session_id=sid, status=SessionStatus.COMPLETED)
        await store.write_state(sid, state_v2)

        loaded = await store.read_state(sid)
        assert loaded is not None
        assert loaded.status == SessionStatus.COMPLETED


class TestSessionStoreListSessions:
    """Test list_sessions operation."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, tmp_path):
        """Listing sessions from an empty store should return empty list."""
        store = SessionStore(tmp_path)

        sessions = await store.list_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_all_sessions(self, tmp_path):
        """list_sessions without filters should return all sessions."""
        store = SessionStore(tmp_path)

        for i in range(3):
            state = make_session_state(
                session_id=f"session_20260208_12000{i}_abc1234{i}",
                goal_id=f"goal_{i}",
            )
            await store.write_state(state.session_id, state)

        sessions = await store.list_sessions()

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_status(self, tmp_path):
        """Filtering by status should return only matching sessions."""
        store = SessionStore(tmp_path)

        completed = make_session_state(
            session_id="session_20260208_120000_aaaa0000",
            status=SessionStatus.COMPLETED,
        )
        failed = make_session_state(
            session_id="session_20260208_120001_bbbb1111",
            status=SessionStatus.FAILED,
        )
        active = make_session_state(
            session_id="session_20260208_120002_cccc2222",
            status=SessionStatus.ACTIVE,
        )

        for s in [completed, failed, active]:
            await store.write_state(s.session_id, s)

        result = await store.list_sessions(status="completed")

        assert len(result) == 1
        assert result[0].session_id == completed.session_id

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_goal_id(self, tmp_path):
        """Filtering by goal_id should return only matching sessions."""
        store = SessionStore(tmp_path)

        s1 = make_session_state(
            session_id="session_20260208_120000_aaaa0000",
            goal_id="goal_a",
        )
        s2 = make_session_state(
            session_id="session_20260208_120001_bbbb1111",
            goal_id="goal_b",
        )
        s3 = make_session_state(
            session_id="session_20260208_120002_cccc2222",
            goal_id="goal_a",
        )

        for s in [s1, s2, s3]:
            await store.write_state(s.session_id, s)

        result = await store.list_sessions(goal_id="goal_a")

        assert len(result) == 2
        goal_ids = {s.session_id for s in result}
        assert goal_ids == {s1.session_id, s3.session_id}

    @pytest.mark.asyncio
    async def test_list_sessions_with_limit(self, tmp_path):
        """Limit should cap the number of returned sessions."""
        store = SessionStore(tmp_path)

        for i in range(5):
            state = make_session_state(
                session_id=f"session_20260208_12000{i}_abc1234{i}",
            )
            await store.write_state(state.session_id, state)

        result = await store.list_sessions(limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_sorted_by_updated_at(self, tmp_path):
        """Sessions should be sorted by updated_at descending (most recent first)."""
        store = SessionStore(tmp_path)

        old = SessionState(
            session_id="session_20260208_100000_old00000",
            goal_id="goal",
            status=SessionStatus.COMPLETED,
            timestamps=SessionTimestamps(
                started_at="2026-02-08T10:00:00",
                updated_at="2026-02-08T10:00:00",
            ),
        )
        new = SessionState(
            session_id="session_20260208_120000_new00000",
            goal_id="goal",
            status=SessionStatus.COMPLETED,
            timestamps=SessionTimestamps(
                started_at="2026-02-08T12:00:00",
                updated_at="2026-02-08T12:00:00",
            ),
        )

        await store.write_state(old.session_id, old)
        await store.write_state(new.session_id, new)

        sessions = await store.list_sessions()

        assert sessions[0].session_id == new.session_id
        assert sessions[1].session_id == old.session_id

    @pytest.mark.asyncio
    async def test_list_sessions_skips_dirs_without_state_json(self, tmp_path):
        """Directories without state.json should be silently skipped."""
        store = SessionStore(tmp_path)

        # Write a valid session
        state = make_session_state()
        await store.write_state(state.session_id, state)

        # Create a directory without state.json
        (store.sessions_dir / "orphan_session").mkdir(parents=True, exist_ok=True)

        sessions = await store.list_sessions()

        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_skips_corrupted_state(self, tmp_path):
        """Sessions with corrupted state.json should be skipped."""
        store = SessionStore(tmp_path)

        # Write a valid session
        state = make_session_state()
        await store.write_state(state.session_id, state)

        # Create a corrupted session
        bad_dir = store.sessions_dir / "session_bad"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "state.json").write_text("not valid json{{{")

        sessions = await store.list_sessions()

        assert len(sessions) == 1


class TestSessionStoreDelete:
    """Test delete_session operation."""

    @pytest.mark.asyncio
    async def test_delete_existing_session(self, tmp_path):
        """Deleting an existing session should return True and remove data."""
        store = SessionStore(tmp_path)
        state = make_session_state()
        await store.write_state(state.session_id, state)

        result = await store.delete_session(state.session_id)

        assert result is True
        assert not store.get_session_path(state.session_id).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, tmp_path):
        """Deleting a session that doesn't exist should return False."""
        store = SessionStore(tmp_path)

        result = await store.delete_session("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_then_read_returns_none(self, tmp_path):
        """After deletion, reading the session should return None."""
        store = SessionStore(tmp_path)
        state = make_session_state()
        await store.write_state(state.session_id, state)

        await store.delete_session(state.session_id)
        loaded = await store.read_state(state.session_id)

        assert loaded is None


class TestSessionStoreExists:
    """Test session_exists operation."""

    @pytest.mark.asyncio
    async def test_exists_true_for_written_session(self, tmp_path):
        """session_exists should return True for a written session."""
        store = SessionStore(tmp_path)
        state = make_session_state()
        await store.write_state(state.session_id, state)

        result = await store.session_exists(state.session_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false_for_nonexistent(self, tmp_path):
        """session_exists should return False for a missing session."""
        store = SessionStore(tmp_path)

        result = await store.session_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_false_after_delete(self, tmp_path):
        """session_exists should return False after deletion."""
        store = SessionStore(tmp_path)
        state = make_session_state()
        await store.write_state(state.session_id, state)

        await store.delete_session(state.session_id)
        result = await store.session_exists(state.session_id)

        assert result is False
