"""Node definitions for SQL Generator Agent."""
from framework.graph import NodeSpec


parse_request_node = NodeSpec(
    id="parse-request",
    name="Parse Request",
    description="Understand the natural language question and schema",
    node_type="llm_generate",
    input_keys=["question", "schema"],
    output_keys=["tables_needed", "columns_needed", "operation_type", "conditions"],
    system_prompt="""\
You are a SQL query planner. Analyze the user's question and database schema to plan the query.

Given:
- question: The natural language question
- schema: The database schema (tables, columns, types)

Identify:
1. tables_needed: Which tables are needed
2. columns_needed: Which columns to select or use
3. operation_type: SELECT, INSERT, UPDATE, DELETE, or JOIN
4. conditions: Any WHERE conditions, ORDER BY, GROUP BY, etc.

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.
Just the JSON object starting with { and ending with }

{"tables_needed": ["users"], "columns_needed": ["id", "name"], "operation_type": "SELECT", "conditions": {"where": "age > 18", "order_by": "name"}}
""",
    tools=[],
    max_retries=3,
)


generate_sql_node = NodeSpec(
    id="generate-sql",
    name="Generate SQL",
    description="Generate the SQL query from the parsed request",
    node_type="llm_generate",
    input_keys=["question", "schema", "tables_needed", "columns_needed", "operation_type", "conditions"],
    output_keys=["sql", "explanation"],
    system_prompt="""\
You are an expert SQL developer. Generate a correct SQL query based on the analysis.

Given the parsed request (tables, columns, operation, conditions) and original schema,
write a clean, efficient SQL query.

Rules:
- Use standard SQL syntax (works on PostgreSQL, MySQL, SQLite)
- Use proper JOINs when multiple tables needed
- Add appropriate WHERE clauses
- Use aliases for readability
- Avoid SQL injection patterns

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.
Just the JSON object starting with { and ending with }

{"sql": "SELECT id, name FROM users WHERE age > 18 ORDER BY name;", "explanation": "Retrieves id and name of adult users, sorted alphabetically"}
""",
    tools=[],
    max_retries=3,
)


__all__ = [
    "parse_request_node",
    "generate_sql_node",
]
