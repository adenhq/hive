# Memori — Persistent Memory for Hive Agents ([Issue #4118](https://github.com/Samir-atra/hive_fork/issues/4118))

Memori provides a "Memory Fabric" for Hive agents, allowing them to store facts, preferences, and long-term context that persists across different execution loops and user sessions.

## 🔑 Authentication

Add your Memori API key to the `.env` file:

```bash
# Memori.ai API Key (https://memorilabs.ai/docs)
MEMORI_API_KEY=your_memori_api_key
```

## 🛠 Tools Reference

### 1. `memori_add`
Store a new fact or user preference.
- **Parameters**: `content` (string), `user_id` (string, optional), `metadata` (dict, optional).
- **Usage**: Use this when an agent learns something important (e.g., "The user works in fintech").

### 2. `memori_recall`
Retrieve memories relevant to a query using semantic search.
- **Parameters**: `query` (string), `user_id` (string, optional), `limit` (int, default: 5).
- **Usage**: Use this at the start of a task to gather relevant context.

### 3. `memori_delete`
Delete a memory by its unique ID.
- **Parameters**: `memory_id` (string).

### 4. `memori_health_check`
Verify the status of the Memori connection.

## 🤖 Reference Workflow

### Personalization Agent
```python
# 1. Recall past context
history = memori_recall(query="preferred programming language", user_id="user_v1")

# 2. Use history in prompt
# ... agent processes ...

# 3. Add new information
memori_add(content="User switched from Java to Python for their latest project", user_id="user_v1")
```

## 🧪 Error Handling
- **401 (Unauthorized)**: Verify your `MEMORI_API_KEY`.
- **429 (Rate Limit)**: Exponential backoff is recommended for high-volume memory writes.
- **404 (Not Found)**: Target memory ID does not exist.
