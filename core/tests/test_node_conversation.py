import pytest
import asyncio
from typing import Any
from framework.graph.conversation import NodeConversation, Message, ConversationStore


class MockConversationStore:
    def __init__(self):
        self.parts = {}
        self.meta = {}
        self.cursor = {}

    async def write_part(self, seq: int, data: dict) -> None:
        self.parts[seq] = data

    async def read_parts(self) -> list[dict]:
        return [self.parts[k] for k in sorted(self.parts.keys())]

    async def write_meta(self, data: dict) -> None:
        self.meta = data

    async def read_meta(self) -> dict | None:
        return self.meta or None

    async def write_cursor(self, data: dict) -> None:
        self.cursor = data

    async def read_cursor(self) -> dict | None:
        return self.cursor or None

    async def delete_parts_before(self, seq: int) -> None:
        self.parts = {k: v for k, v in self.parts.items() if k >= seq}


class TestNodeConversation:
    @pytest.mark.asyncio
    async def test_multi_turn_build_and_export(self):
        """Build conversation, export to LLM format."""
        conv = NodeConversation(system_prompt="You are helpful.")
        await conv.add_user_message("Hello")
        await conv.add_assistant_message("Hi there!")
        msgs = conv.to_llm_messages()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_token_estimation(self):
        """estimate_tokens() returns ~4 chars/token."""
        conv = NodeConversation()
        await conv.add_user_message("a" * 400)  # ~100 tokens
        # 400 chars / 4 = 100
        assert 80 <= conv.estimate_tokens() <= 120

    @pytest.mark.asyncio
    async def test_compaction_reduces_messages(self):
        """compact() replaces old messages with summary."""
        conv = NodeConversation(max_history_tokens=100, compaction_threshold=0.5)
        for i in range(20):
            await conv.add_user_message(f"Message {i} " * 5)
            await conv.add_assistant_message(f"Reply {i} " * 5)
        
        # Ensure we hit threshold
        # approx 40 msg * ~100 chars = 4000 chars -> 1000 tokens. 100 max * 0.5 = 50.
        assert conv.needs_compaction()
        
        await conv.compact("Summary of conversation so far")
        # Should have kept last 10% (4 messages) + 1 summary message
        assert len(conv.messages) < 40

    @pytest.mark.asyncio
    async def test_compaction_preserves_output_keys(self):
        """compact() preserves values for declared output_keys."""
        conv = NodeConversation(output_keys=["confirmed_meetings"])
        await conv.add_user_message("Process emails")
        await conv.add_assistant_message('{"confirmed_meetings": [{"contact": "Sarah Chen"}]}')
        
        # Add many messages to force compaction keep list to exclude the first assistant message
        for i in range(30):
            await conv.add_user_message(f"More content {i} " * 10)
            await conv.add_assistant_message(f"Processing {i} " * 10)
            
        await conv.compact("Summary")
        summary_msg = conv.messages[0]
        assert "PRESERVED VALUES" in summary_msg.content
        assert "confirmed_meetings" in summary_msg.content
        assert "Sarah Chen" in summary_msg.content

    @pytest.mark.asyncio
    async def test_write_through_persistence(self):
        """Each add_* writes to store immediately."""
        store = MockConversationStore()
        conv = NodeConversation(store=store)
        await conv.add_user_message("Hello")
        assert len(await store.read_parts()) == 1
        await conv.add_assistant_message("Hi")
        assert len(await store.read_parts()) == 2

    @pytest.mark.asyncio
    async def test_restore_from_store(self):
        """restore() rebuilds conversation from stored parts."""
        store = MockConversationStore()
        # Initialize meta manually for mock if needed, or through an initial save
        await store.write_meta({
            "system_prompt": "Test",
            "max_history_tokens": 32000,
            "compaction_threshold": 0.8,
            "output_keys": []
        })
        
        conv = NodeConversation(system_prompt="Test", store=store)
        await conv.add_user_message("Hello")
        await conv.add_assistant_message("Hi")
        
        restored = await NodeConversation.restore(store)
        assert restored is not None
        assert len(restored.messages) == 2
        assert restored.system_prompt == "Test"
        assert restored.messages[0].content == "Hello"
        assert restored.messages[1].content == "Hi"

    @pytest.mark.asyncio
    async def test_tool_result_includes_id(self):
        """add_tool_result() includes tool_call_id in LLM dict."""
        conv = NodeConversation()
        await conv.add_tool_result("tc_123", "Result text")
        msgs = conv.to_llm_messages()
        assert msgs[-1]["tool_call_id"] == "tc_123"
        assert msgs[-1]["role"] == "tool"

    @pytest.mark.asyncio
    async def test_in_memory_no_store(self):
        """All methods work without store (backward compatible)."""
        conv = NodeConversation()
        await conv.add_user_message("Hello")
        await conv.add_assistant_message("Hi")
        assert conv.turn_count == 1
        assert len(conv.to_llm_messages()) == 2
