# Audit Trail Tool

Generate decision timelines and analyze agent behavior from run data.

## Overview

The Audit Trail Tool provides comprehensive visibility into agent decision-making processes. It's designed for:

- **Debugging**: Understand why an agent made specific decisions
- **Compliance**: Generate audit logs for regulatory requirements
- **Analysis**: Identify patterns in agent behavior and performance
- **Optimization**: Find bottlenecks and areas for improvement

## Tools

### `generate_audit_trail`

Generate a formatted timeline of all decisions made during an agent run.

**Parameters:**
- `run_data` (string, required): JSON string of run data from storage
- `format` (string): Output format - `text`, `json`, or `markdown` (default: `markdown`)
- `include_reasoning` (bool): Include agent's reasoning (default: `true`)
- `include_outcomes` (bool): Include outcome information (default: `true`)
- `filter_decision_type` (string): Filter by decision type (e.g., `tool_selection`)
- `filter_node_id` (string): Filter by node ID

**Example:**
```python
result = generate_audit_trail(
    run_data=storage.load_run("run_123").model_dump_json(),
    format="markdown",
    include_reasoning=True,
)
```

### `analyze_decision_patterns`

Analyze decision patterns and statistics from a run.

**Parameters:**
- `run_data` (string, required): JSON string of run data

**Returns:**
- Total decision count
- Success/failure rates
- Decision breakdown by type
- Average latency metrics
- Most active nodes

**Example:**
```python
analysis = analyze_decision_patterns(run_data=run_json)
# Returns:
# {
#   "total_decisions": 15,
#   "overall_success_rate": 0.867,
#   "by_decision_type": { ... },
#   "by_node": { ... }
# }
```

### `compare_decision_outcomes`

Compare multiple decisions to identify patterns and evaluate choices.

**Parameters:**
- `run_data` (string, required): JSON string of run data
- `decision_ids` (list[string]): Specific decisions to compare (optional)

**Returns:**
- Comparison of chosen vs alternative options
- Confidence vs outcome correlation
- Quality scores for each decision

## Use Cases

### 1. Post-Run Analysis

```python
# Load run and generate audit trail
run = storage.load_run("run_123")
trail = generate_audit_trail(
    run_data=run.model_dump_json(),
    format="markdown"
)
print(trail)
```

### 2. Debugging Failed Runs

```python
# Focus on failed decisions
run = storage.load_run("failed_run_456")
analysis = analyze_decision_patterns(run.model_dump_json())

# Find which decision types are failing
failed_types = {
    k: v for k, v in analysis["by_decision_type"].items()
    if v["success_rate"] < 0.5
}
```

### 3. Compliance Reporting

```python
# Generate structured audit log
audit_log = generate_audit_trail(
    run_data=run.model_dump_json(),
    format="json",
    include_reasoning=True,
    include_outcomes=True,
)

# Save for compliance records
with open("audit_log.json", "w") as f:
    f.write(audit_log)
```

## Decision Types

The tool recognizes these decision types (from `DecisionType` enum):

| Type | Description |
|------|-------------|
| `tool_selection` | Which tool to use |
| `parameter_choice` | What parameters to pass |
| `path_choice` | Which branch to take |
| `output_format` | How to format output |
| `retry_strategy` | How to handle failure |
| `delegation` | Whether to delegate |
| `termination` | Whether to stop/continue |
| `custom` | User-defined type |

## Output Formats

### Markdown (default)

Best for human reading, includes headers, tables, and emoji indicators.

### JSON

Structured format ideal for programmatic analysis or storage.

### Text

Plain text format for logs and terminals without markdown support.

## Related Schemas

- `Decision` - The atomic unit of agent behavior
- `Outcome` - What happened when a decision was executed
- `DecisionEvaluation` - Post-hoc evaluation of decision quality
- `Run` - Complete agent run containing decisions

See `core/framework/schemas/decision.py` for full schema definitions.
