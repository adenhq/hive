"""Tests for FileConversationStore - file-per-part conversation storage."""

import json

import pytest

from framework.storage.conversation_store import FileConversationStore


class TestFileConversationStoreInit:
    """Test FileConversationStore initialization."""

    def test_init_with_path(self, tmp_path):
        """Store should accept a Path and set base/parts directories."""
        store = FileConversationStore(tmp_path / "conv")
        assert store._base == tmp_path / "conv"
        assert store._parts_dir == tmp_path / "conv" / "parts"

    def test_init_with_string_path(self, tmp_path):
        """Store should accept a string path."""
        store = FileConversationStore(str(tmp_path / "conv"))
        assert store._base == tmp_path / "conv"


class TestFileConversationStoreParts:
    """Test write_part and read_parts operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_single_part(self, tmp_path):
        """Writing a part and reading it back should return the same data."""
        store = FileConversationStore(tmp_path / "conv")
        data = {"role": "user", "content": "hello"}

        await store.write_part(0, data)
        parts = await store.read_parts()

        assert len(parts) == 1
        assert parts[0] == data

    @pytest.mark.asyncio
    async def test_write_and_read_multiple_parts(self, tmp_path):
        """Multiple parts should be returned in sequence order."""
        store = FileConversationStore(tmp_path / "conv")
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you?"},
        ]

        for i, msg in enumerate(messages):
            await store.write_part(i, msg)

        parts = await store.read_parts()

        assert len(parts) == 3
        assert parts == messages

    @pytest.mark.asyncio
    async def test_read_parts_empty_store(self, tmp_path):
        """Reading from an empty store should return an empty list."""
        store = FileConversationStore(tmp_path / "conv")

        parts = await store.read_parts()

        assert parts == []

    @pytest.mark.asyncio
    async def test_write_part_creates_numbered_file(self, tmp_path):
        """Parts should be stored as zero-padded numbered JSON files."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"content": "first"})
        await store.write_part(5, {"content": "fifth"})

        assert (tmp_path / "conv" / "parts" / "0000000000.json").exists()
        assert (tmp_path / "conv" / "parts" / "0000000005.json").exists()

    @pytest.mark.asyncio
    async def test_parts_ordering_with_gaps(self, tmp_path):
        """Parts with non-sequential numbers should still be read in order."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(10, {"seq": 10})
        await store.write_part(2, {"seq": 2})
        await store.write_part(5, {"seq": 5})

        parts = await store.read_parts()

        assert len(parts) == 3
        assert parts[0] == {"seq": 2}
        assert parts[1] == {"seq": 5}
        assert parts[2] == {"seq": 10}

    @pytest.mark.asyncio
    async def test_read_parts_skips_corrupted_json(self, tmp_path):
        """Corrupted JSON files should be skipped, not cause errors."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"content": "valid"})

        # Write a corrupted file
        parts_dir = tmp_path / "conv" / "parts"
        corrupted = parts_dir / "0000000001.json"
        corrupted.write_text("not valid json{{{")

        await store.write_part(2, {"content": "also valid"})

        parts = await store.read_parts()

        assert len(parts) == 2
        assert parts[0] == {"content": "valid"}
        assert parts[1] == {"content": "also valid"}


class TestFileConversationStoreMeta:
    """Test meta read/write operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_meta(self, tmp_path):
        """Writing and reading meta should roundtrip correctly."""
        store = FileConversationStore(tmp_path / "conv")
        meta = {"model": "claude-3", "temperature": 0.7}

        await store.write_meta(meta)
        loaded = await store.read_meta()

        assert loaded == meta

    @pytest.mark.asyncio
    async def test_read_meta_nonexistent(self, tmp_path):
        """Reading meta when no file exists should return None."""
        store = FileConversationStore(tmp_path / "conv")

        result = await store.read_meta()

        assert result is None

    @pytest.mark.asyncio
    async def test_meta_creates_json_file(self, tmp_path):
        """Meta should be stored as meta.json in the base directory."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_meta({"key": "value"})

        meta_path = tmp_path / "conv" / "meta.json"
        assert meta_path.exists()

        with open(meta_path) as f:
            data = json.load(f)
        assert data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_read_meta_corrupted_returns_none(self, tmp_path):
        """Corrupted meta.json should return None."""
        store = FileConversationStore(tmp_path / "conv")
        meta_path = tmp_path / "conv" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text("not json!!!")

        result = await store.read_meta()

        assert result is None


class TestFileConversationStoreCursor:
    """Test cursor read/write operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_cursor(self, tmp_path):
        """Writing and reading cursor should roundtrip correctly."""
        store = FileConversationStore(tmp_path / "conv")
        cursor = {"position": 42, "last_seq": 10}

        await store.write_cursor(cursor)
        loaded = await store.read_cursor()

        assert loaded == cursor

    @pytest.mark.asyncio
    async def test_read_cursor_nonexistent(self, tmp_path):
        """Reading cursor when no file exists should return None."""
        store = FileConversationStore(tmp_path / "conv")

        result = await store.read_cursor()

        assert result is None


class TestFileConversationStoreDeleteParts:
    """Test delete_parts_before operation."""

    @pytest.mark.asyncio
    async def test_delete_parts_before(self, tmp_path):
        """Parts before the given sequence should be deleted."""
        store = FileConversationStore(tmp_path / "conv")
        for i in range(5):
            await store.write_part(i, {"seq": i})

        await store.delete_parts_before(3)

        parts = await store.read_parts()
        assert len(parts) == 2
        assert parts[0] == {"seq": 3}
        assert parts[1] == {"seq": 4}

    @pytest.mark.asyncio
    async def test_delete_parts_before_empty_store(self, tmp_path):
        """Deleting from an empty store should not raise."""
        store = FileConversationStore(tmp_path / "conv")

        await store.delete_parts_before(5)  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_parts_before_zero(self, tmp_path):
        """Deleting before 0 should remove nothing."""
        store = FileConversationStore(tmp_path / "conv")
        for i in range(3):
            await store.write_part(i, {"seq": i})

        await store.delete_parts_before(0)

        parts = await store.read_parts()
        assert len(parts) == 3


class TestFileConversationStoreLifecycle:
    """Test close and destroy operations."""

    @pytest.mark.asyncio
    async def test_close_is_noop(self, tmp_path):
        """Close should complete without error."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"data": "test"})

        await store.close()  # Should not raise

        # Data should still be accessible after close
        parts = await store.read_parts()
        assert len(parts) == 1

    @pytest.mark.asyncio
    async def test_destroy_removes_all_data(self, tmp_path):
        """Destroy should remove the entire base directory."""
        base = tmp_path / "conv"
        store = FileConversationStore(base)
        await store.write_part(0, {"data": "test"})
        await store.write_meta({"key": "value"})
        await store.write_cursor({"pos": 0})

        assert base.exists()

        await store.destroy()

        assert not base.exists()

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_is_safe(self, tmp_path):
        """Destroying a store that was never written to should not raise."""
        store = FileConversationStore(tmp_path / "nonexistent")

        await store.destroy()  # Should not raise
