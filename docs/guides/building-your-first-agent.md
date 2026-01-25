# Building Your First Agent

This guide shows how to build agents using Hive. There are two approaches:

1. **Recommended: Using Claude Code skills** - Interactive, guided process
2. **Manual: Writing files directly** - Full control, useful for understanding internals

## Approach 1: Using Claude Code Skills (Recommended)

This is the recommended way. Claude Code guides you through the process using MCP builder tools.

### Step 1: Install Skills

Run the quickstart script to install Claude Code skills:

```bash
./quickstart.sh
```

This installs skills to `~/.claude/skills/`.

### Step 2: Start Building

In Claude Code, run the workflow orchestrator:

```
/agent-workflow
```

Or use specific skills directly:

```
/building-agents-construction   # Step-by-step building
/building-agents-core           # Core concepts
/testing-agent                  # Test your agent
```

### Step 3: Describe Your Agent

Claude will ask what you want to build. Describe it naturally:

```
"Build an agent that converts natural language questions into SQL queries.
Input: a question and database schema.
Output: the SQL query and an explanation."
```

### Step 4: Claude Builds It

Claude will:

1. Create a build session using MCP tools
2. Define the goal and success criteria
3. Create nodes (processing steps)
4. Connect nodes with edges
5. Generate all the code files
6. Validate the structure

You approve each step before Claude proceeds.

### Step 5: Test Your Agent

```bash
PYTHONPATH=core:exports python -m your_agent_name validate
PYTHONPATH=core:exports python -m your_agent_name demo
```

### MCP Builder Tools

Behind the scenes, Claude uses these MCP tools:

```python
# Create a build session
mcp__agent-builder__create_session(name="SQL Generator")

# Define the goal
mcp__agent-builder__set_goal(
    goal_id="generate-sql",
    name="Generate SQL from Natural Language",
    description="Convert questions to SQL queries",
    success_criteria='[{"id": "valid-sql", "description": "...", ...}]',
    constraints='[{"id": "no-injection", ...}]'
)

# Add nodes
mcp__agent-builder__add_node(
    node_id="parse-request",
    name="Parse Request",
    node_type="llm",
    input_keys='["question", "schema"]',
    output_keys='["tables_needed", "operation_type"]',
    system_prompt="...",
    tools='[]'
)

# Connect nodes
mcp__agent-builder__add_edge(
    edge_id="parse-to-generate",
    source="parse-request",
    target="generate-sql",
    condition="on_success"
)

# Validate
mcp__agent-builder__validate_graph()
```

---

## Approach 2: Manual File Creation

If you prefer full control or want to understand the internals, you can create files manually.

### Package Structure

```
exports/your_agent_name/
  __init__.py       # Package exports
  __main__.py       # CLI interface
  agent.py          # Goal, edges, agent class
  config.py         # Model and settings
  nodes/
    __init__.py     # Node definitions
```

### Step 1: Create Directories

```bash
mkdir -p exports/sql_generator_agent/nodes
```

### Step 2: Write config.py

```python
"""Runtime configuration."""
from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    model: str = "ollama/llama3.2"  # or gemini/gemini-2.0-flash
    temperature: float = 0.2
    max_tokens: int = 4096


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "SQL Generator Agent"
    version: str = "1.0.0"
    description: str = "Generates SQL from natural language."


metadata = AgentMetadata()
```

### Step 3: Write nodes/__init__.py

Each node is a processing step:

```python
"""Node definitions."""
from framework.graph import NodeSpec


parse_request_node = NodeSpec(
    id="parse-request",
    name="Parse Request",
    description="Analyze the question and schema",
    node_type="llm_generate",
    input_keys=["question", "schema"],
    output_keys=["tables_needed", "columns_needed", "operation_type"],
    system_prompt="""\
You are a SQL query planner. Analyze the question and schema.

Identify which tables and columns are needed.

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

{"tables_needed": ["users"], "columns_needed": ["id", "name"], "operation_type": "SELECT"}
""",
    tools=[],
    max_retries=3,
)


generate_sql_node = NodeSpec(
    id="generate-sql",
    name="Generate SQL",
    description="Write the SQL query",
    node_type="llm_generate",
    input_keys=["question", "schema", "tables_needed", "columns_needed", "operation_type"],
    output_keys=["sql", "explanation"],
    system_prompt="""\
You are an expert SQL developer. Generate a correct SQL query.

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

{"sql": "SELECT id, name FROM users;", "explanation": "Gets all users"}
""",
    tools=[],
    max_retries=3,
)


__all__ = ["parse_request_node", "generate_sql_node"]
```

### Step 4: Write agent.py

Wire the nodes together:

```python
"""Agent graph construction."""
from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .nodes import parse_request_node, generate_sql_node
from .config import default_config, metadata


goal = Goal(
    id="generate-sql",
    name="Generate SQL from Natural Language",
    description="Convert questions to SQL queries.",
    success_criteria=[
        SuccessCriterion(
            id="valid-sql",
            description="Generate correct SQL",
            metric="sql_valid",
            target="true",
            weight=1.0,
        ),
    ],
    constraints=[
        Constraint(
            id="no-injection",
            description="No SQL injection",
            constraint_type="security",
            category="safety",
        ),
    ],
)

edges = [
    EdgeSpec(
        id="parse-to-generate",
        source="parse-request",
        target="generate-sql",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "parse-request"
entry_points = {"start": "parse-request"}
pause_nodes = []
terminal_nodes = ["generate-sql"]
nodes = [parse_request_node, generate_sql_node]


class SQLGeneratorAgent:
    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._runtime = None

    async def run(self, context: dict, mock_mode=False) -> ExecutionResult:
        # ... implementation
        pass

    def validate(self):
        # ... validation logic
        pass


default_agent = SQLGeneratorAgent()
```

### Step 5: Write __main__.py (CLI)

```python
"""CLI for agent."""
import asyncio
import click
from .agent import default_agent


@click.group()
def cli():
    """SQL Generator Agent."""
    pass


@cli.command()
@click.option("--question", "-q", required=True)
@click.option("--schema", "-s", required=True)
def run(question, schema):
    """Generate SQL."""
    result = asyncio.run(default_agent.run({
        "question": question,
        "schema": schema
    }))
    print(f"SQL: {result.output.get('sql')}")


if __name__ == "__main__":
    cli()
```

### Step 6: Write __init__.py

```python
"""SQL Generator Agent."""
from .agent import SQLGeneratorAgent, default_agent
from .config import RuntimeConfig, default_config, metadata

__version__ = "1.0.0"
__all__ = ["SQLGeneratorAgent", "default_agent", "RuntimeConfig", "default_config", "metadata"]
```

---

## Key Concepts

### Nodes

Nodes are processing steps. Each node:
- Takes inputs (`input_keys`)
- Runs an LLM with a prompt (`system_prompt`)
- Produces outputs (`output_keys`)

Node types:
- `llm_generate`: Pure LLM output, no tools
- `llm_tool_use`: LLM can call tools (web search, file operations, etc.)
- `router`: Conditional branching
- `function`: Python function execution

### Edges

Edges connect nodes. Conditions:
- `ON_SUCCESS`: Only if previous node succeeded
- `ON_FAILURE`: Only if previous node failed
- `ALWAYS`: Always traverse
- `conditional`: Custom condition expression

### Goals

Goals define success criteria and constraints. Used for:
- Validating agent behavior
- Self-improvement feedback loops
- Monitoring and alerting

---

## Troubleshooting

### LLM returns markdown instead of JSON

Add to your prompt:
```
CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.
```

### Agent is slow with Ollama

Use a cloud provider for faster responses:
```python
model: str = "gemini/gemini-2.0-flash"  # Fast and free tier available
```

### Node output missing keys

Check that `output_keys` in one node match `input_keys` in the next node.

---

---

## Try Pre-made Example Agents

Before building your own, try these working examples:

### Invoice Analyzer Agent

Detects hidden charges in invoices (telecom bills, restaurant receipts, SaaS invoices).

```bash
# Copy example to exports
cp -r .claude/skills/building-agents-construction/examples/invoice_analyzer_agent exports/

# Run demo
source .venv/bin/activate
PYTHONPATH=core:exports python -m invoice_analyzer_agent demo

# Run with your own invoice
PYTHONPATH=core:exports python -m invoice_analyzer_agent run --file path/to/invoice.pdf
```

### SQL Generator Agent

Converts natural language questions to SQL queries.

```bash
# Copy example to exports
cp -r .claude/skills/building-agents-construction/examples/sql_generator_agent exports/

# Run demo
source .venv/bin/activate
PYTHONPATH=core:exports python -m sql_generator_agent demo

# Run with your own query
PYTHONPATH=core:exports python -m sql_generator_agent run --question "Find users over 18" --schema "users(id, name, age)"
```

### Online Research Agent

Researches topics using web search (requires Brave API key).

```bash
# Copy example to exports
cp -r .claude/skills/building-agents-construction/examples/online_research_agent exports/

# Set API key
export BRAVE_SEARCH_API_KEY="your-key"

# Run
PYTHONPATH=core:exports python -m online_research_agent run --topic "AI agents 2025"
```

---

## Next Steps

- Read the local LLM guide: `docs/guides/local-llm-setup.md`
- Try the `/testing-agent` skill to test your agent
- Join the Discord: https://discord.com/invite/MXE49hrKDk
