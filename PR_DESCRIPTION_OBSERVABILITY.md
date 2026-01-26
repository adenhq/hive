# PR Title: Observability & Metrics (G-Phad Pack Batch 3)

## Description
This PR implements the final batch of "G-Phad" improvements, focusing on observability and metrics. It enables agents to track their own performance and allows developers to inspect run history programmatically.

## Key Changes

### 1. Runtime Metrics
- **Metrics Tracking**: Added a `metrics` dictionary to the `Runtime` class to track custom metrics (e.g., `total_tokens`, `total_latency_ms`, `llm_calls`).
- **Automatic Tracking**: Updated `LLMNode` to automatically track token usage, latency, and call counts for every execution.
- **Output Integration**: Metrics are now included in the final run output and stored in the run JSON file.

### 2. Observability Tool
- **New Tool**: Added `observability_tool` with three capabilities:
    - `list_recent_runs`: Lists the most recent agent runs with status and metrics.
    - `get_run_details`: Retrieves full details of a specific run.
    - `analyze_run_metrics`: Computes derived metrics (e.g., average latency, tool usage frequency) for a run.
- **Self-Reflection**: Agents can now use this tool to "reflect" on their past performance or the performance of other agents.

## Testing
- Verified metrics are correctly tracked and saved in run files.
- Verified `observability_tool` correctly lists and retrieves run data.
- Verified derived metrics calculation.
