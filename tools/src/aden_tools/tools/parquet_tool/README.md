# Parquet Tool

Read-only Parquet dataset inspection and querying toolkit for the Aden Agent Framework.

## Features

- **parquet_info**: Get schema (columns + types) and metadata
- **parquet_preview**: Preview rows with optional column selection and filtering
- **parquet_query**: Execute SQL queries with DuckDB

## Safety & Limits

- **Path security**: All paths validated against session sandbox
- **Row limits**: Preview max 20 rows, query max 200 rows
- **Cell truncation**: Long strings truncated to 1000 chars
- **Read-only**: Only SELECT queries allowed
- **Timeout protection**: DuckDB in-memory execution

## Usage

### Get Schema and Metadata

```python
parquet_info(
    path="data.parquet",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789"
)
```

Returns:
- Column names and types
- Row count (best effort)
- File count (for partitioned datasets)

### Preview Data

```python
parquet_preview(
    path="data.parquet",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789",
    limit=10,
    columns=["name", "price"],
    where="price > 100"
)
```

### Query with SQL

```python
parquet_query(
    path="data.parquet",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789",
    sql="SELECT category, AVG(price) FROM data GROUP BY category",
    limit=50
)
```

The Parquet file is available as table `data` in queries.

## Partitioned Datasets

Supports folder paths with multiple Parquet files:

```python
parquet_info(path="dataset_folder/")
```

DuckDB automatically reads all `*.parquet` files in the folder.

## Requirements

- DuckDB: `uv pip install duckdb`
