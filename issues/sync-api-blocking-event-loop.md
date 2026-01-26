---
name: Bug Report
about: Report a bug to help us improve
title: '[Bug]: Synchronous API Call in to_summary() Blocks Event Loop'
labels: bug, performance
assignees: ''
---

## Describe the Bug

The `NodeResult.to_summary()` method makes synchronous Anthropic API calls using `anthropic.Anthropic()` inside the async execution path. This blocks the event loop on every successful node execution, causing latency spikes and preventing concurrent async operations.

The issue occurs in:
- `NodeResult.to_summary()` (lines 319-341 in core/framework/graph/node.py)

Called from:
- `GraphExecutor.execute()` (line 283 in core/framework/graph/executor.py)

## To Reproduce

Steps to reproduce the behavior:

1. Create an agent with multiple nodes
2. Execute the agent with `ANTHROPIC_API_KEY` set
3. Monitor async performance - each node completion blocks the event loop for 500-2000ms during the `to_summary()` API call
4. Any concurrent async operations will be frozen during these calls

## Expected Behavior

The `to_summary()` method should:
- Use `anthropic.AsyncAnthropic` with async/await pattern
- Not block the event loop during API calls
- Include timeout handling for slow API responses

## Environment

- OS: macOS (darwin 25.2.0)
- Python version: 3.11.0

## Configuration

Requires `ANTHROPIC_API_KEY` to be set (otherwise falls back to non-blocking simple summary).

## Logs

No error logs, but blocking behavior can be observed with async timing:
```python
# Each node completion adds 500-2000ms of blocking time
# Concurrent coroutines are frozen during this period
```

## Additional Context

The synchronous call pattern:
```python
client = anthropic.Anthropic(api_key=api_key)  # Sync client
message = client.messages.create(...)  # Blocks event loop
```

Should be converted to:
```python
client = anthropic.AsyncAnthropic(api_key=api_key)  # Async client
message = await asyncio.wait_for(
    client.messages.create(...),
    timeout=10.0
)
```
