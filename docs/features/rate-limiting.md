# Tool Rate Limiting

## Overview

The rate limiter prevents runaway costs and resource exhaustion by limiting tool execution frequency and cost.

## Features

- **Per-minute limits** - Prevent rapid-fire tool calls
- **Per-hour limits** - Control overall usage
- **Cost tracking** - Monitor and limit spending per tool
- **Thread-safe** - Works with concurrent execution
- **Configurable** - Per-tool custom limits

## Usage

### Basic Usage
```python
from framework.runtime.rate_limiter import ToolRateLimiter

# Create rate limiter with default limits
limiter = ToolRateLimiter()

# Check if tool can be executed
allowed, reason = limiter.check_limit('web_search', estimated_cost=0.001)

if allowed:
    # Execute the tool
    result = execute_tool('web_search')
else:
    print(f"Rate limit exceeded: {reason}")
```

### Custom Configuration
```python
# Configure custom limits per tool
config = {
    'web_search': {
        'max_per_minute': 60,
        'max_per_hour': 500,
        'max_cost_per_hour': 5.0
    },
    'llm_call': {
        'max_per_minute': 100,
        'max_per_hour': 1000,
        'max_cost_per_hour': 50.0
    }
}

limiter = ToolRateLimiter(config=config)
```

### Get Statistics
```python
# Get current usage stats for a tool
stats = limiter.get_stats('web_search')

print(f"Calls last minute: {stats['calls_last_minute']}")
print(f"Calls last hour: {stats['calls_last_hour']}")
print(f"Cost last hour: ${stats['cost_last_hour']:.2f}")
```

### Reset Limits
```python
# Reset limits for a specific tool
limiter.reset('web_search')

# Reset all limits
limiter.reset()
```

## Default Limits

If not configured, tools use these defaults:

- **max_per_minute**: 100 calls
- **max_per_hour**: 1000 calls
- **max_cost_per_hour**: $50.00

## Error Handling

When a limit is exceeded, `check_limit()` returns `(False, reason)`:
```python
allowed, reason = limiter.check_limit('expensive_tool', 100.0)

if not allowed:
    # reason will be one of:
    # - "Rate limit exceeded: X/Y calls per minute"
    # - "Rate limit exceeded: X/Y calls per hour"
    # - "Cost limit exceeded: $X/$Y per hour"
    logger.warning(f"Tool blocked: {reason}")
```

## Testing

Run the test suite:
```bash
pytest core/tests/test_rate_limiter.py -v
```

## Future Enhancements

- Circuit breaker pattern for failing tools
- Exponential backoff on rate limit hits
- Persistent storage of limits across restarts
- Dashboard for monitoring tool usage
