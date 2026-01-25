# SQL Generator Agent

Converts natural language questions into SQL queries.

## What It Does

Takes a question and database schema, generates:
- Valid SQL query
- Explanation of what the query does

## Flow

```
[question, schema] --> parse-request --> generate-sql --> [sql, explanation]
```

Two nodes:
1. **parse-request**: Analyzes question, identifies tables/columns needed
2. **generate-sql**: Generates the SQL query with explanation

## Usage

```bash
# Set up (if using cloud LLM)
export GOOGLE_API_KEY="..."  # or OPENAI_API_KEY, etc.

# Run with inline schema
PYTHONPATH=core:exports python -m sql_generator_agent run \
  --question "Find users who spent over $100" \
  --schema "users(id, name); orders(id, user_id, amount)"

# Run with schema file
PYTHONPATH=core:exports python -m sql_generator_agent run \
  --question "List products out of stock" \
  --schema ./schema.sql

# Run demo
PYTHONPATH=core:exports python -m sql_generator_agent demo
```

## Example Output

```
SQL QUERY:

  SELECT u.id, u.name
  FROM users AS u
  JOIN orders AS o ON u.id = o.user_id
  GROUP BY u.id, u.name
  HAVING SUM(o.amount) > 100;

EXPLANATION:
  Joins users with orders, groups by user, filters those
  with total order amount exceeding $100.
```

## Configuration

Edit `config.py` to change the model:

```python
model: str = "ollama/llama3.2"      # Free, local, slow
model: str = "gemini/gemini-2.0-flash"  # Free tier, fast
model: str = "gpt-4o-mini"          # Paid, fast, high quality
```

## Customization

Edit `nodes/__init__.py` to:
- Add database-specific syntax (PostgreSQL, MySQL, SQLite)
- Include query optimization hints
- Add validation for dangerous operations (DROP, DELETE)
