# API Reference

## Goal

```python
Goal(
    id: str,                              # Unique identifier
    name: str,                            # Human-readable name
    description: str,                     # What the agent does
    success_criteria: list[SuccessCriterion],  # Measurable success metrics
    constraints: list[Constraint],        # Boundaries and rules
    required_capabilities: list[str],     # e.g., ["llm", "tools"]
    input_schema: dict,                   # Expected input format
    output_schema: dict,                  # Expected output format
)
```

## SuccessCriterion

```python
SuccessCriterion(
    id: str,              # Unique identifier
    description: str,     # What must be true
    metric: str,          # How to measure (e.g., "accuracy", "output_equals")
    target: str,          # Threshold (e.g., ">0.9", "exact_match")
    weight: float,        # Importance (0.0-1.0)
)
```

## Constraint

```python
Constraint(
    id: str,                    # Unique identifier
    description: str,           # What the agent must NOT do
    constraint_type: str,       # "hard" (must not violate) or "soft" (prefer not to)
    category: str,              # "safety", "time", "cost", "scope", "quality"
    check: str,                 # How to verify compliance
)
```

## NodeSpec

```python
NodeSpec(
    id: str,                    # Unique identifier
    name: str,                  # Human-readable name
    description: str,           # What this node does
    node_type: str,             # "llm_generate", "llm_tool_use", "router", "function"
    input_keys: list[str],      # Keys to read from shared memory
    output_keys: list[str],     # Keys to write to shared memory
    system_prompt: str | None,  # Instructions for LLM (required for llm_*)
    tools: list[str],           # Available tools (for llm_tool_use)
    routes: dict[str, str],     # Route map (for router)
    function: str | None,       # Function name (for function)
    max_retries: int,           # Default 3
)
```

### Node Types

| Type | Description | Requires |
|------|-------------|----------|
| `llm_generate` | Text generation, parsing | `system_prompt` |
| `llm_tool_use` | Actions with tools | `system_prompt`, `tools` |
| `router` | Conditional branching | `routes` |
| `function` | Deterministic code | `function` |

## EdgeSpec

```python
EdgeSpec(
    id: str,                      # Unique identifier
    source: str,                  # Source node ID
    target: str,                  # Target node ID
    condition: EdgeCondition,     # When to traverse
    condition_expr: str | None,   # Expression for CONDITIONAL
    input_mapping: dict[str, str],# Data mapping between nodes
    priority: int,                # Higher = checked first
)
```

### EdgeCondition

| Value | When |
|-------|------|
| `ALWAYS` | After source completes (success or failure) |
| `ON_SUCCESS` | Only if source succeeds |
| `ON_FAILURE` | Only if source fails |
| `CONDITIONAL` | Based on `condition_expr` |

## GraphSpec

```python
GraphSpec(
    id: str,                    # Unique identifier
    goal_id: str,               # Associated goal
    entry_node: str,            # Starting node
    terminal_nodes: list[str],  # Ending nodes
    nodes: list[NodeSpec],      # All nodes
    edges: list[EdgeSpec],      # All edges
    memory_keys: list[str],     # All shared memory keys
    default_model: str,         # Default LLM model
    max_steps: int,             # Max execution steps
)
```

## GraphExecutor

```python
executor = GraphExecutor(
    runtime: Runtime,           # Decision logging
    llm: LLMProvider,           # LLM for nodes
    tools: list[Tool],          # Available tools
    tool_executor: Callable,    # Function to execute tools
)

result = await executor.execute(
    graph: GraphSpec,
    goal: Goal,
    input_data: dict,
)
```

### ExecutionResult

```python
ExecutionResult(
    success: bool,              # Did execution succeed?
    output: dict,               # Final output from shared memory
    error: str | None,          # Error message if failed
    steps_executed: int,        # Number of steps taken
    total_tokens: int,          # LLM tokens used
    total_latency_ms: int,      # Total execution time
    path: list[str],            # Node IDs traversed
)
```

## Tool Definition

```python
Tool(
    name: str,                  # Tool identifier
    description: str,           # What the tool does
    parameters: dict,           # JSON Schema for parameters
)
```

## ToolResult

```python
ToolResult(
    tool_use_id: str,           # ID from tool call
    content: str,               # Result (usually JSON string)
    is_error: bool,             # True if tool failed
)
```

## Imports

```python
# Core
from framework.graph import Goal, SuccessCriterion, Constraint
from framework.graph import NodeSpec, EdgeSpec, EdgeCondition
from framework.graph.edge import GraphSpec
from framework.graph import GraphExecutor

# LLM
from framework.llm import AnthropicProvider
from framework.llm.provider import Tool, ToolResult

# Runtime
from core import Runtime
```
