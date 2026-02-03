CSV Tool
This tool enables agents to read, write, and perform advanced analytical queries on CSV files using DuckDB-powered SQL.

Key Features
High Performance: Uses DuckDB Views for lazy loading, allowing analysis of large files without excessive RAM usage.

Relational Queries: Supports SQL JOINs across multiple CSV files.

Secure Sandbox: Fully integrated with Aden's security layer to ensure data isolation.

Usage Examples
1. Basic SQL Query

Query a single CSV file as a table named data.

Python
# Query example
query = "SELECT * FROM data WHERE price > 100 ORDER BY price DESC"
2. Multi-file JOIN (Advanced)

Pass a list of paths to perform relational queries. Files are aliased as data0, data1, etc.

Python
# Query example
paths = ["users.csv", "orders.csv"]
query = "SELECT u.name, o.amount FROM data0 u JOIN data1 o ON u.id = o.user_id"
Tool Arguments: csv_sql
Argument	Type	Description
paths	`list[str]	str`
query	string	Standard SQL SELECT query.
workspace_id	string	Workspace identifier for security validation.
agent_id	string	Agent identifier for security validation.
session_id	string	Session identifier for security validation.
Security Notes
Only SELECT statements are allowed.

DML and DDL commands (INSERT, UPDATE, DROP, etc.) are strictly blocked for security reasons.