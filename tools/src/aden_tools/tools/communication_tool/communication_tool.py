"""
Communication Tool - Chat logging and conversation management for agent development.

Logs conversations between users, Claude, and agents to support testing and improvement
of agent building workflows. Stores chat history with timestamps, context, and metadata.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP


# Storage configuration
CHAT_STORAGE_DIR = Path.home() / ".aden" / "chat_logs"
CHAT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ChatLogger:
    """Manages chat logging and storage for agent development conversations."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or CHAT_STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log_message(self, session_id: str, sender: str, message: str,
                   message_type: str = "text", metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a chat message to storage.

        Args:
            session_id: Unique identifier for the conversation session
            sender: Who sent the message ('user', 'claude', 'agent', etc.)
            message: The actual message content
            message_type: Type of message ('text', 'tool_call', 'tool_result', etc.)
            metadata: Additional context data

        Returns:
            Message ID for the logged message
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        chat_entry = {
            "id": message_id,
            "timestamp": timestamp,
            "session_id": session_id,
            "sender": sender,
            "message": message,
            "message_type": message_type,
            "metadata": metadata or {}
        }

        # Save to session file
        session_file = self.base_dir / f"{session_id}.jsonl"
        with open(session_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(chat_entry, ensure_ascii=False) + '\n')

        return message_id

    def get_session_messages(self, session_id: str,
                           sender_filter: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve messages from a conversation session.

        Args:
            session_id: Session ID to retrieve
            sender_filter: Optional filter by sender ('user', 'claude', 'agent')
            limit: Maximum number of messages to return

        Returns:
            List of chat messages
        """
        session_file = self.base_dir / f"{session_id}.jsonl"
        if not session_file.exists():
            return []

        messages = []
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line.strip())
                    if sender_filter is None or msg['sender'] == sender_filter:
                        messages.append(msg)

        # Sort by timestamp and apply limit
        messages.sort(key=lambda x: x['timestamp'])
        if limit:
            messages = messages[-limit:]

        return messages

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a summary of a conversation session.

        Args:
            session_id: Session ID to summarize

        Returns:
            Summary statistics and metadata
        """
        messages = self.get_session_messages(session_id)
        if not messages:
            return {"session_id": session_id, "message_count": 0}

        # Calculate statistics
        sender_counts = {}
        message_types = {}
        start_time = messages[0]['timestamp']
        end_time = messages[-1]['timestamp']

        for msg in messages:
            sender = msg['sender']
            msg_type = msg['message_type']

            sender_counts[sender] = sender_counts.get(sender, 0) + 1
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

        return {
            "session_id": session_id,
            "message_count": len(messages),
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 60,
            "sender_breakdown": sender_counts,
            "message_type_breakdown": message_types,
            "participants": list(sender_counts.keys())
        }

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all available conversation sessions with summaries.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        sessions = []
        for session_file in self.base_dir.glob("*.jsonl"):
            session_id = session_file.stem
            summary = self.get_session_summary(session_id)
            sessions.append(summary)

        # Sort by most recent activity
        sessions.sort(key=lambda x: x.get('end_time', ''), reverse=True)
        return sessions[:limit]

    def search_messages(self, query: str, session_id: Optional[str] = None,
                       sender_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for messages containing specific text.

        Args:
            query: Text to search for
            session_id: Optional session to search in
            sender_filter: Optional sender filter

        Returns:
            List of matching messages
        """
        results = []

        # Determine which sessions to search
        if session_id:
            sessions_to_search = [session_id]
        else:
            sessions_to_search = [f.stem for f in self.base_dir.glob("*.jsonl")]

        for sid in sessions_to_search:
            messages = self.get_session_messages(sid, sender_filter)
            for msg in messages:
                if query.lower() in msg['message'].lower():
                    results.append(msg)

        # Sort by timestamp
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results

    def export_session(self, session_id: str, format: str = "json") -> str:
        """
        Export a conversation session in various formats.

        Args:
            session_id: Session to export
            format: Export format ('json', 'markdown', 'text')

        Returns:
            Formatted conversation export
        """
        messages = self.get_session_messages(session_id)
        if not messages:
            return f"No messages found for session {session_id}"

        if format == "json":
            return json.dumps(messages, indent=2, ensure_ascii=False)

        elif format == "markdown":
            output = [f"# Conversation Session: {session_id}\n"]
            for msg in messages:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
                output.append(f"**{msg['sender'].title()}** ({timestamp}):")
                output.append(f"{msg['message']}\n")
            return "\n".join(output)

        elif format == "text":
            output = [f"Conversation Session: {session_id}\n"]
            for msg in messages:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                output.append(f"[{timestamp}] {msg['sender'].title()}: {msg['message']}")
            return "\n".join(output)

        else:
            return f"Unsupported format: {format}"


# Global chat logger instance
_chat_logger = ChatLogger()


def register_tools(mcp: FastMCP) -> None:
    """Register communication tools with the MCP server."""

    @mcp.tool()
    def log_chat_message(session_id: str, sender: str, message: str,
                        message_type: str = "text",
                        metadata: Optional[str] = None) -> str:
        """
        Log a chat message to the conversation history.

        Use this tool to record conversations between users, Claude, and agents
        for testing and improvement purposes.

        Args:
            session_id: Unique identifier for the conversation session
            sender: Who sent the message ('user', 'claude', 'agent', etc.)
            message: The actual message content
            message_type: Type of message ('text', 'tool_call', 'tool_result', 'error', etc.)
            metadata: Optional JSON string with additional context data

        Returns:
            Message ID of the logged message
        """
        try:
            # Parse metadata if provided
            metadata_dict = None
            if metadata:
                try:
                    metadata_dict = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata_dict = {"raw_metadata": metadata}

            message_id = _chat_logger.log_message(
                session_id=session_id,
                sender=sender,
                message=message,
                message_type=message_type,
                metadata=metadata_dict
            )

            return f"Message logged with ID: {message_id}"

        except Exception as e:
            return f"Error logging message: {str(e)}"

    @mcp.tool()
    def get_chat_history(session_id: str, sender_filter: Optional[str] = None,
                        limit: Optional[int] = None) -> str:
        """
        Retrieve chat history from a conversation session.

        Use this to review past conversations for agent testing and improvement.

        Args:
            session_id: Session ID to retrieve messages from
            sender_filter: Optional filter by sender ('user', 'claude', 'agent')
            limit: Maximum number of recent messages to return

        Returns:
            JSON string of chat messages
        """
        try:
            messages = _chat_logger.get_session_messages(
                session_id=session_id,
                sender_filter=sender_filter,
                limit=limit
            )

            return json.dumps({
                "session_id": session_id,
                "message_count": len(messages),
                "messages": messages
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error retrieving chat history: {str(e)}"

    @mcp.tool()
    def analyze_conversation(session_id: str) -> str:
        """
        Analyze a conversation session for patterns and insights.

        Useful for understanding agent behavior and identifying areas for improvement.

        Args:
            session_id: Session ID to analyze

        Returns:
            JSON string with conversation analysis
        """
        try:
            summary = _chat_logger.get_session_summary(session_id)

            # Add additional analysis
            messages = _chat_logger.get_session_messages(session_id)
            analysis = {
                "summary": summary,
                "insights": []
            }

            # Basic pattern analysis
            if summary["message_count"] > 0:
                # Check for error patterns
                error_messages = [m for m in messages if m.get("message_type") == "error"]
                if error_messages:
                    analysis["insights"].append(f"Found {len(error_messages)} error messages")

                # Check conversation balance
                participants = summary.get("participants", [])
                if len(participants) >= 2:
                    analysis["insights"].append(f"Active conversation between: {', '.join(participants)}")

                # Check for tool usage
                tool_calls = [m for m in messages if m.get("message_type") == "tool_call"]
                if tool_calls:
                    analysis["insights"].append(f"Agent made {len(tool_calls)} tool calls")

            return json.dumps(analysis, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error analyzing conversation: {str(e)}"

    @mcp.tool()
    def search_chat_history(query: str, session_id: Optional[str] = None,
                          sender_filter: Optional[str] = None) -> str:
        """
        Search through chat history for specific content.

        Useful for finding specific discussions or error patterns during agent testing.

        Args:
            query: Text to search for in messages
            session_id: Optional specific session to search in
            sender_filter: Optional filter by message sender

        Returns:
            JSON string of matching messages
        """
        try:
            results = _chat_logger.search_messages(
                query=query,
                session_id=session_id,
                sender_filter=sender_filter
            )

            return json.dumps({
                "query": query,
                "result_count": len(results),
                "results": results
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error searching chat history: {str(e)}"

    @mcp.tool()
    def export_conversation(session_id: str, format: str = "markdown") -> str:
        """
        Export a conversation session in various formats.

        Useful for documentation, sharing findings, or detailed analysis.

        Args:
            session_id: Session ID to export
            format: Export format ('json', 'markdown', 'text')

        Returns:
            Formatted conversation export
        """
        try:
            return _chat_logger.export_session(session_id, format)
        except Exception as e:
            return f"Error exporting conversation: {str(e)}"

    @mcp.tool()
    def list_conversation_sessions(limit: int = 20) -> str:
        """
        List all available conversation sessions.

        Use this to see what conversations are available for analysis.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            JSON string of available sessions with summaries
        """
        try:
            sessions = _chat_logger.list_sessions(limit=limit)
            return json.dumps({
                "session_count": len(sessions),
                "sessions": sessions
            }, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error listing sessions: {str(e)}"
