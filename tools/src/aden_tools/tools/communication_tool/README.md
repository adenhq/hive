# Communication Tool

Chat logging and conversation management tool for agent development and testing.

## Overview

The Communication Tool enables logging, storage, and analysis of conversations between users, Claude, and agents. This is essential for:

- **Agent Testing**: Track conversations to understand agent behavior
- **Improvement Analysis**: Identify patterns in successful/failed interactions
- **Debugging**: Review conversation history to diagnose issues
- **Documentation**: Export conversations for sharing and analysis

## Features

- **Chat Logging**: Record messages with timestamps, senders, and metadata
- **Session Management**: Organize conversations by unique session IDs
- **Search & Filter**: Find specific messages or conversation patterns
- **Export Formats**: Export conversations as JSON, Markdown, or plain text
- **Analytics**: Generate insights about conversation patterns

## Storage

Conversations are stored locally in `~/.aden/chat_logs/` as JSON Lines files:
- Each session gets its own `.jsonl` file
- Messages include timestamps, sender info, and metadata
- Files are append-only for reliability

## Usage Examples

### Log a Chat Message
```python
# Log a user message
log_chat_message(
    session_id="agent-test-001",
    sender="user",
    message="Build a sales agent for cold outreach"
)

# Log Claude's response
log_chat_message(
    session_id="agent-test-001",
    sender="claude",
    message="I'll help you build a sales agent...",
    metadata='{"skill": "building-agents-construction"}'
)

# Log agent execution
log_chat_message(
    session_id="agent-test-001",
    sender="agent",
    message="Agent completed: sent 50 emails",
    message_type="tool_result"
)
```

### Retrieve Chat History
```python
# Get recent messages from a session
history = get_chat_history(
    session_id="agent-test-001",
    limit=10
)

# Get only user messages
user_messages = get_chat_history(
    session_id="agent-test-001",
    sender_filter="user"
)
```

### Analyze Conversations
```python
# Get session analytics
analysis = analyze_conversation("agent-test-001")
# Returns: participant counts, message types, error patterns, etc.
```

### Search Messages
```python
# Find messages containing "error"
errors = search_chat_history("error", session_id="agent-test-001")

# Search all sessions for "sales"
sales_mentions = search_chat_history("sales")
```

### Export Conversations
```python
# Export as markdown for documentation
export = export_conversation("agent-test-001", format="markdown")

# Export as JSON for analysis
data = export_conversation("agent-test-001", format="json")
```

## Integration with Agent Building

This tool is designed to support the agent building workflow:

1. **During Construction**: Log conversations between Claude and users
2. **Testing Phase**: Record agent behavior and user feedback
3. **Analysis**: Identify successful patterns and improvement areas
4. **Iteration**: Use insights to evolve agent design

## Message Types

- `text`: Regular chat messages
- `tool_call`: When agents use tools
- `tool_result`: Tool execution results
- `error`: Error messages and failures
- `system`: System notifications

## Metadata Support

Messages can include structured metadata:

```json
{
  "skill": "building-agents-construction",
  "agent_version": "1.0",
  "success": true,
  "execution_time": 45.2
}
```

## Security & Privacy

- **Local Storage**: All data stored locally, no external transmission
- **User Control**: Users can delete conversation logs anytime
- **No Sensitive Data**: Tool doesn't log API keys or credentials
- **Opt-in**: Only logs when explicitly called

## File Structure

```
~/.aden/chat_logs/
├── session-001.jsonl    # Individual session logs
├── session-002.jsonl
└── ...
```

Each line is a JSON object:
```json
{
  "id": "msg-uuid",
  "timestamp": "2024-01-15T10:30:00",
  "session_id": "agent-test-001",
  "sender": "user",
  "message": "Build a sales agent",
  "message_type": "text",
  "metadata": {}
}
```