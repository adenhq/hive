# Audit Trail Tool

Decision timeline generation and export for compliance, debugging, and analysis.

## Overview

The Audit Trail Tool provides structured, queryable audit trails of all agent decisions. It reads from the framework's `FileStorage` and generates chronological timelines in multiple formats.

## Tools

### `generate_audit_timeline`

Generate a complete decision timeline from agent runs.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `storage_path` | string | Yes | Path to storage directory |
| `run_id` | string | No | Filter to specific run |
| `goal_id` | string | No | Filter to runs for a goal |
| `node_id` | string | No | Filter by node |
| `decision_type` | string | No | Filter by type |
| `start_date` | string | No | ISO date filter (after) |
| `end_date` | string | No | ISO date filter (before) |
| `success_only` | bool | No | Only successful decisions |
| `failure_only` | bool | No | Only failed decisions |
| `export_format` | string | No | "json", "csv", or "text" |

**Example:**
```python
result = generate_audit_timeline(
    storage_path="./storage",
    goal_id="support_agent",
    export_format="text"
)
```

### `get_decision_details`

Get detailed information about a specific decision.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `storage_path` | string | Yes | Path to storage directory |
| `run_id` | string | Yes | Run containing the decision |
| `decision_id` | string | Yes | Decision ID to retrieve |

### `get_audit_summary`

Get aggregate statistics about decisions.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `storage_path` | string | Yes | Path to storage directory |
| `goal_id` | string | No | Filter to specific goal |

**Returns:** JSON with total runs, decisions, success rate, decision types, and nodes used.

## Export Formats

### JSON
Full structured data with all fields. Best for programmatic access.

### CSV
Tabular format for spreadsheet analysis. One row per decision.

### Text
Human-readable format with visual formatting. Best for logs and reports.

## Use Cases

1. **Compliance Auditing** - Track all decisions for regulatory requirements
2. **Debugging** - Trace decision flow to identify issues
3. **Analysis** - Analyze patterns across multiple runs
4. **Reporting** - Generate reports for stakeholders
