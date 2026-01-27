# Audit Trail Tool

Generate decision timelines from agent runs for analysis and debugging.

## Description

The Audit Trail Tool queries runtime storage to generate a chronological timeline of all decisions made during an agent run, including their outcomes, options considered, and context. This helps with debugging agent behavior and understanding decision-making patterns.

## Arguments

### `generate_audit_trail`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `run_id` | str | Yes | - | The ID of the run to generate audit trail for |
| `storage_path` | str | Yes | - | Path to the runtime storage directory |
| `format` | str | No | `"json"` | Output format: `"json"` (structured) or `"markdown"` (human-readable) |
| `include_outcomes` | bool | No | `True` | Whether to include outcome details for each decision |
| `include_options` | bool | No | `True` | Whether to include all options that were considered |

### `list_runs`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `storage_path` | str | Yes | - | Path to the runtime storage directory |
| `goal_id` | str | No | `None` | Optional filter by goal ID |
| `limit` | int | No | `20` | Maximum number of runs to return |

## Usage Examples

### Generate JSON Audit Trail

```python
result = generate_audit_trail(
    run_id="run_123",
    storage_path="/path/to/storage",
    format="json",
    include_outcomes=True,
    include_options=True
)
```

### Generate Markdown Audit Trail

```python
result = generate_audit_trail(
    run_id="run_123",
    storage_path="/path/to/storage",
    format="markdown"
)
# Access markdown: result["markdown"]
```

### List Available Runs

```python
runs = list_runs(
    storage_path="/path/to/storage",
    goal_id="goal_001",  # Optional filter
    limit=10
)
```

## Return Format

### `generate_audit_trail` (JSON format)

```json
{
  "run_id": "run_123",
  "goal_id": "goal_001",
  "status": "completed",
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": "2025-01-15T10:05:00Z",
  "total_decisions": 5,
  "format": "json",
  "timeline": [
    {
      "timestamp": "2025-01-15T10:00:05Z",
      "decision_id": "dec_001",
      "node_id": "search_node",
      "decision_type": "tool_selection",
      "intent": "Search for customer information",
      "reasoning": "Need to find customer details",
      "chosen_option_id": "opt_web_search",
      "chosen_option": {
        "id": "opt_web_search",
        "description": "Use web search API",
        "action_type": "tool_call"
      },
      "total_options": 2,
      "outcome": {
        "success": true,
        "summary": "Found 3 results",
        "tokens_used": 150,
        "latency_ms": 1200
      }
    }
  ]
}
```

### `list_runs`

```json
{
  "storage_path": "/path/to/storage",
  "total_runs": 15,
  "runs": [
    {
      "run_id": "run_123",
      "goal_id": "goal_001",
      "status": "completed",
      "started_at": "2025-01-15T10:00:00Z",
      "completed_at": "2025-01-15T10:05:00Z",
      "total_decisions": 5
    }
  ]
}
```

## Error Handling

Returns error dicts for common issues:
- `Storage path does not exist: <path>` - Invalid storage path
- `Run not found: <run_id>` - Run ID doesn't exist
- `Invalid JSON in run file: <error>` - Corrupted run file
- `Failed to generate audit trail: <error>` - Other errors

## Use Cases

1. **Debugging**: Understand why an agent made specific decisions
2. **Analysis**: Identify patterns in decision-making
3. **Documentation**: Generate reports of agent behavior
4. **Optimization**: Find decision points that could be improved

## Related

- Runtime storage format: `core/framework/storage/`
- Decision schema: `core/framework/schemas/decision.py`
- Run schema: `core/framework/schemas/run.py`
