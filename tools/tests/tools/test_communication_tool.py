"""Tests for Communication Tool (chat logging and conversation management)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import communication tool directly to avoid dependency issues with other tools
communication_tool_path = Path(__file__).parent.parent.parent / "src" / "aden_tools" / "tools" / "communication_tool"
sys.path.insert(0, str(communication_tool_path.parent))

# Import the module directly
import importlib.util
spec = importlib.util.spec_from_file_location("communication_tool", communication_tool_path / "communication_tool.py")
communication_tool = importlib.util.module_from_spec(spec)
sys.modules["communication_tool"] = communication_tool
spec.loader.exec_module(communication_tool)

register_tools = communication_tool.register_tools
ChatLogger = communication_tool.ChatLogger
from fastmcp import FastMCP


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary directory for chat storage."""
    storage_dir = tmp_path / "chat_logs"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def chat_logger(temp_storage_dir):
    """Create a ChatLogger instance with temporary storage."""
    return ChatLogger(temp_storage_dir)


@pytest.fixture
def communication_tools(mcp: FastMCP):
    """Register and return communication tools."""
    register_tools(mcp)
    return mcp._tool_manager._tools


class TestChatLogger:
    """Tests for the ChatLogger class."""

    def test_log_message_basic(self, chat_logger, temp_storage_dir):
        """Test basic message logging."""
        session_id = "test-session-001"
        message_id = chat_logger.log_message(
            session_id=session_id,
            sender="user",
            message="Hello, world!"
        )

        assert message_id is not None
        assert len(message_id) > 0

        # Check file was created
        session_file = temp_storage_dir / f"{session_id}.jsonl"
        assert session_file.exists()

        # Check file contents
        with open(session_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1

            data = json.loads(lines[0])
            assert data["session_id"] == session_id
            assert data["sender"] == "user"
            assert data["message"] == "Hello, world!"
            assert data["message_type"] == "text"
            assert "timestamp" in data
            assert "id" in data

    def test_log_message_with_metadata(self, chat_logger):
        """Test logging message with metadata."""
        session_id = "test-session-002"
        metadata = {"skill": "building-agents", "version": "1.0"}

        chat_logger.log_message(
            session_id=session_id,
            sender="claude",
            message="I'll help you build an agent",
            message_type="response",
            metadata=metadata
        )

        messages = chat_logger.get_session_messages(session_id)
        assert len(messages) == 1
        assert messages[0]["metadata"] == metadata
        assert messages[0]["message_type"] == "response"

    def test_get_session_messages(self, chat_logger):
        """Test retrieving messages from a session."""
        session_id = "test-session-003"

        # Log multiple messages
        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi there!")
        chat_logger.log_message(session_id, "user", "Build an agent")

        messages = chat_logger.get_session_messages(session_id)
        assert len(messages) == 3
        assert messages[0]["sender"] == "user"
        assert messages[0]["message"] == "Hello"
        assert messages[1]["sender"] == "claude"
        assert messages[1]["message"] == "Hi there!"
        assert messages[2]["sender"] == "user"
        assert messages[2]["message"] == "Build an agent"

    def test_get_session_messages_with_filter(self, chat_logger):
        """Test filtering messages by sender."""
        session_id = "test-session-004"

        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi!")
        chat_logger.log_message(session_id, "user", "Thanks")

        user_messages = chat_logger.get_session_messages(session_id, sender_filter="user")
        assert len(user_messages) == 2
        assert all(msg["sender"] == "user" for msg in user_messages)

    def test_get_session_messages_with_limit(self, chat_logger):
        """Test limiting number of returned messages."""
        session_id = "test-session-005"

        for i in range(5):
            chat_logger.log_message(session_id, "user", f"Message {i}")

        messages = chat_logger.get_session_messages(session_id, limit=3)
        assert len(messages) == 3
        # Should return most recent messages
        assert messages[-1]["message"] == "Message 4"

    def test_get_session_summary(self, chat_logger):
        """Test generating session summary."""
        session_id = "test-session-006"

        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi!")
        chat_logger.log_message(session_id, "agent", "Working...")

        summary = chat_logger.get_session_summary(session_id)

        assert summary["session_id"] == session_id
        assert summary["message_count"] == 3
        assert summary["participants"] == ["user", "claude", "agent"]
        assert summary["sender_breakdown"]["user"] == 1
        assert summary["sender_breakdown"]["claude"] == 1
        assert summary["sender_breakdown"]["agent"] == 1
        assert "start_time" in summary
        assert "end_time" in summary
        assert "duration_minutes" in summary

    def test_list_sessions(self, chat_logger):
        """Test listing available sessions."""
        # Create multiple sessions
        chat_logger.log_message("session-1", "user", "Hello 1")
        chat_logger.log_message("session-2", "user", "Hello 2")
        chat_logger.log_message("session-1", "claude", "Response 1")

        sessions = chat_logger.list_sessions()
        assert len(sessions) >= 2

        session_ids = [s["session_id"] for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids

    def test_search_messages(self, chat_logger):
        """Test searching messages by content."""
        session_id = "test-session-007"

        chat_logger.log_message(session_id, "user", "I want to build a sales agent")
        chat_logger.log_message(session_id, "claude", "Great! Let's build a sales agent")
        chat_logger.log_message(session_id, "user", "Show me the marketing agent")

        results = chat_logger.search_messages("sales")
        assert len(results) == 2
        assert all("sales" in msg["message"].lower() for msg in results)

    def test_export_session_json(self, chat_logger):
        """Test exporting session as JSON."""
        session_id = "test-session-008"

        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi!")

        export = chat_logger.export_session(session_id, "json")
        data = json.loads(export)

        assert len(data) == 2
        assert data[0]["sender"] == "user"
        assert data[0]["message"] == "Hello"
        assert data[1]["sender"] == "claude"
        assert data[1]["message"] == "Hi!"

    def test_export_session_markdown(self, chat_logger):
        """Test exporting session as Markdown."""
        session_id = "test-session-009"

        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi!")

        export = chat_logger.export_session(session_id, "markdown")

        assert "# Conversation Session:" in export
        assert "**User**" in export
        assert "**Claude**" in export
        assert "Hello" in export
        assert "Hi!" in export

    def test_export_session_text(self, chat_logger):
        """Test exporting session as plain text."""
        session_id = "test-session-010"

        chat_logger.log_message(session_id, "user", "Hello")
        chat_logger.log_message(session_id, "claude", "Hi!")

        export = chat_logger.export_session(session_id, "text")

        assert "Conversation Session:" in export
        assert "User:" in export
        assert "Claude:" in export
        assert "Hello" in export
        assert "Hi!" in export


class TestCommunicationTools:
    """Tests for the communication MCP tools."""

    def test_log_chat_message_tool(self, communication_tools):
        """Test the log_chat_message tool."""
        tool = communication_tools["log_chat_message"].fn

        result = tool(
            session_id="tool-test-001",
            sender="user",
            message="Test message"
        )

        assert "Message logged with ID:" in result

    def test_get_chat_history_tool(self, communication_tools):
        """Test the get_chat_history tool."""
        log_tool = communication_tools["log_chat_message"].fn
        history_tool = communication_tools["get_chat_history"].fn

        # Log a message first
        log_tool(
            session_id="tool-test-002",
            sender="user",
            message="Test message"
        )

        # Get history
        result = history_tool(session_id="tool-test-002")
        data = json.loads(result)

        assert data["session_id"] == "tool-test-002"
        assert data["message_count"] == 1
        assert len(data["messages"]) == 1
        assert data["messages"][0]["sender"] == "user"
        assert data["messages"][0]["message"] == "Test message"

    def test_analyze_conversation_tool(self, communication_tools):
        """Test the analyze_conversation tool."""
        log_tool = communication_tools["log_chat_message"].fn
        analyze_tool = communication_tools["analyze_conversation"].fn

        # Log some messages
        log_tool(session_id="tool-test-003", sender="user", message="Hello")
        log_tool(session_id="tool-test-003", sender="claude", message="Hi!")
        log_tool(session_id="tool-test-003", sender="agent", message="Working...")

        # Analyze
        result = analyze_tool(session_id="tool-test-003")
        data = json.loads(result)

        assert "summary" in data
        assert data["summary"]["message_count"] == 3
        assert data["summary"]["participants"] == ["user", "claude", "agent"]

    def test_search_chat_history_tool(self, communication_tools):
        """Test the search_chat_history tool."""
        log_tool = communication_tools["log_chat_message"].fn
        search_tool = communication_tools["search_chat_history"].fn

        # Log messages
        log_tool(session_id="tool-test-004", sender="user", message="Build a sales agent")
        log_tool(session_id="tool-test-004", sender="claude", message="Great idea!")

        # Search
        result = search_tool(query="sales")
        data = json.loads(result)

        assert data["query"] == "sales"
        assert data["result_count"] >= 1
        assert any("sales" in msg["message"].lower() for msg in data["results"])

    def test_export_conversation_tool(self, communication_tools):
        """Test the export_conversation tool."""
        log_tool = communication_tools["log_chat_message"].fn
        export_tool = communication_tools["export_conversation"].fn

        # Log a message
        log_tool(session_id="tool-test-005", sender="user", message="Hello")

        # Export as markdown
        result = export_tool(session_id="tool-test-005", format="markdown")

        assert "# Conversation Session:" in result
        assert "**User**" in result
        assert "Hello" in result

    def test_list_conversation_sessions_tool(self, communication_tools):
        """Test the list_conversation_sessions tool."""
        list_tool = communication_tools["list_conversation_sessions"].fn

        result = list_tool(limit=10)
        data = json.loads(result)

        assert "session_count" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_tools_error_handling(self, communication_tools):
        """Test error handling in tools."""
        history_tool = communication_tools["get_chat_history"].fn

        # Try to get history for non-existent session
        result = history_tool(session_id="non-existent-session")

        # Should return empty result, not crash
        data = json.loads(result)
        assert data["message_count"] == 0
        assert data["messages"] == []