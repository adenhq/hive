# Developer Guide

This guide covers everything you need to know to develop with the high-performance Aden Hive Framework (v0.2.0).

> **Version 0.2.0 Update**: The framework has been significantly upgraded with async execution, caching, and production-grade resilience. See the [Migration Guide](#migration-guide) if upgrading from v0.1.0.

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Initial Setup](#initial-setup)
3. [Architecture & Performance](#architecture--performance)
4. [Building Agents](#building-agents)
5. [Testing Agents](#testing-agents)
6. [Migration Guide](#migration-guide)
7. [Common Tasks](#common-tasks)

---

## Repository Overview

Aden Hive is a Python-based system for building goal-driven, self-improving AI agents.

| Package       | Directory  | Description                             | Tech Stack   |
| ------------- | ---------- | --------------------------------------- | ------------ |
| **framework** | `/core`    | Core runtime, graph executor, protocols | Python 3.11+ |
| **tools**     | `/tools`   | 19 MCP tools for agent capabilities     | Python 3.11+ |
| **exports**   | `/exports` | Agent packages and examples             | Python 3.11+ |

### Key Principles

- **Goal-Driven**: Define objectives, framework generates agent graphs
- **High-Performance**: Fully async, parallel execution, cached decisions
- **Production-Ready**: Rate limiting, circuit breakers, structured logging
- **Self-Improving**: Agents adapt and evolve based on failures

---

## Initial Setup

### Prerequisites

- **Python 3.11+**
- **pip**
- **Redis** (optional, recommended for caching)
- **PostgreSQL** (optional, recommended for production storage)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/adenhq/hive.git
cd hive

# 2. Run automated Python setup
./scripts/setup-python.sh
```

### Environment Variables

```bash
# LLM APIs
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."

# Storage & Caching (Optional)
export REDIS_URL="redis://localhost:6379"
export POSTGRES_URL="postgresql://user:pass@localhost/hive"
```

---

## Architecture & Performance

The framework uses a modern, high-performance architecture optimized for throughput and reliability.

### Core Components

1. **Async Runtime**: Non-blocking execution loop
2. **Parallel Executor**: Runs independent graph nodes concurrently
3. **Storage Layer**: Tiered storage (Hot/Redis → Warm/Postgres → Cold/S3)
4. **Caching Layer**: L1 (Memory) + L2 (Redis) for LLM calls and objects
5. **Resilience**: Token-bucket rate limiting and state-machine circuit breakers

### Performance Tuning

The framework comes tuned for production, but you can customize:

```python
from framework.runtime.core import Runtime
from framework.cache import get_cache

# Initialize optimized runtime
runtime = Runtime(
    storage_path="/data",
    storage_backend="redis",  # Use Redis for high throughput
    storage_kwargs={"redis_url": "redis://localhost:6379"}
)

# Configure global cache
await get_cache(
    redis_url="redis://localhost:6379",
    l1_maxsize=1000,
    l1_ttl=300
)
```

### Parallel Execution

Agents automatically execute nodes in parallel when dependencies allow:

```python
from framework.graph import ParallelGraphExecutor

executor = ParallelGraphExecutor(
    runtime=runtime,
    llm=llm,
    max_concurrent=10  # Run up to 10 nodes at once
)

result = await executor.execute(graph, goal, input_data)
```

---

## Building Agents

### Async Agent Development

All agents are now fully async. When building custom nodes:

```python
from framework.graph.node import NodeProtocol, NodeResult, NodeContext

class CustomNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Async I/O is non-blocking
        data = await ctx.memory.read("some_key")
        
        # Record decision asynchronously
        decision_id = await ctx.runtime.decide(
            intent="Process data",
            options=[...],
            chosen="process",
            reasoning="..."
        )
        
        return NodeResult(success=True, output={"result": "done"})
```

### Using Tools

Tools are executed in the thread pool to avoid blocking the event loop:

```python
# In your node
result = await ctx.tool_executor(
    tool_name="web_search",
    arguments={"query": "python async"}
)
```

---

## Testing Agents

### Parallel Testing

Test suites run in parallel by default using `pytest-xdist`:

```bash
# Run tests with 4 workers
python -m pytest -n 4 exports/my_agent/tests/
```

### Mocking for Performance

Use the `mock_mode` to test logic without LLM calls (instant feedback):

```python
runner = AgentRunner(..., mock_mode=True)
result = await runner.run(...)
```

---

## Migration Guide

### Migrating from v0.1.0 to v0.2.0

1. **Async/Await**: Update all generic node implementations to be `async def`.
   ```python
   # Old
   def execute(self, ctx): ...
   
   # New
   async def execute(self, ctx): ...
   ```

2. **Runtime Calls**: Await all runtime methods.
   ```python
   # Old
   runtime.decide(...)
   
   # New
   await runtime.decide(...)
   ```

3. **Storage**: `FileStorage` is now `AsyncFileStorage`.
   ```python
   # Old
   storage = FileStorage("path")
   
   # New
   storage = StorageFactory.create("file", base_path="path")
   ```

---

## Common Tasks

### Adding a New Dependency

```bash
cd core
pip install package_name
# Add to pyproject.toml dependencies
```

### Optimization Checklist

- [ ] Use `orjson` for JSON serialization (built-in)
- [ ] Enable Redis caching for production
- [ ] Set appropriate `max_concurrent` limits in `ParallelGraphExecutor`
- [ ] Configure `RateLimiter` to match your API tier

---

_Happy coding!_ 🐝
