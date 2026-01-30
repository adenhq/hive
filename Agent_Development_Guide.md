# Agent Development Guide

**Document Version:** 1.3

This guide provides a comprehensive walkthrough for setting up, creating, and running agents. It includes setup instructions, development workflows, and detailed explanations of the interactive testing process.

## 1. Initial Project Setup

Follow these steps to create an isolated environment for agent development. This is a mandatory first step.

1.  **Create Virtual Environment:**
    ```bash
    python3 -m venv .venv
    ```

2.  **Activate Environment:**
    ```bash
    source .venv/bin/activate
    ```
    *(Your terminal prompt will now start with `(.venv)`)*

3.  **Set PYTHONPATH:**
    ```bash
    export PYTHONPATH=core
    ```
    *(This allows the framework to find its core modules. Add this to your `~/.bashrc` or `~/.zshrc` for convenience.)*

## 2. Manual Agent Creation

This approach gives you full control over the agent's design.

### Step 2.1: Create Agent Directory and Files

```bash
mkdir -p exports/support_ticket_agent
touch exports/support_ticket_agent/agent.json
```

### Step 2.2: Iteratively Develop and Validate

Use the `validate` command repeatedly as you build your `agent.json` file.

**Command to Validate:**
```bash
python -m framework validate exports/support_ticket_agent
```

### Common Validation Errors & Solutions

| Error Encountered | Succinct Description & Solution |
| :--- | :--- |
| **`TypeError: string indices must be integers...`** | **Reason:** A field expecting a list of objects (like `success_criteria`) received a simple string. **Fix:** Ensure the value is a `[{"key": "value"}]` array. |
| **`ERROR: Entry node '' not found`** | **Reason:** The agent needs a starting point. **Fix:** Add `"entry_node": "<your_node_id>"`. If the error persists, wrap your entire JSON in a `{"graph": { ... }}` object. |
| **`pydantic_core.ValidationError`** | **Reason:** JSON keys don't match the required schema. **Fix:** Check the error message. Common fixes: rename `"node_id"` to `"id"`; add `"description"` to all nodes. |
| **`ERROR: ...references missing source 'START'`** | **Reason:** An edge references a non-existent node. **Fix:** The `entry_node` makes this redundant for simple agents. Remove the `edges` array if not needed. |

## 3. Automatic Agent Creation (via LLM)

This method is recommended for new users to quickly generate a baseline agent.

### Step 3.1: Generate Agent from Goal

Use the `new` command with a descriptive goal.

**Conceptual Command:**
```bash
python -m framework new "An agent that processes support tickets by categorizing them" --output-dir exports/support_ticket_agent
```

### Step 3.2: Validate and Inspect

**Do not trust the generated agent.** Immediately run `validate` and use the error table above to fix any issues in the generated `agent.json` file.

## 4. Running Your Agent Interactively (Manual Testing)

Once your agent is valid, you can test it in an interactive shell. This is best for quick, exploratory testing.

### Step 4.1: Launch the Interactive Shell

This command activates the environment, sets the `PYTHONPATH`, and starts the agent shell in one line. Run it from the root of your project.

**Command:**
```bash
. .venv/bin/activate && PYTHONPATH=core python -m framework shell exports/support_ticket_agent
```

You will be greeted with a welcome message and a list of available commands at the `>>>` prompt.

### Step 4.2: Executing a Manual Test Run

This demonstrates a full run of our `support_ticket_agent`.

**1. Provide Initial Input:**
Start by providing the `ticket_content` as a JSON object at the `>>>` prompt:
```json
{
  "ticket_content": "Hello, my account is not working and I cannot log in."
}
```

**2. Observe Agent Execution:**
The agent will run. If it uses an `llm` node, it requires a valid API key (e.g., `CEREBRAS_API_KEY`) to be set. If it uses a `human_in_the_loop` node, it will pause and ask for your input.

**3. View the Final Result:**
The agent completes the run and prints the final state of its memory.

## 5. Automated Testing

Automated tests are a powerful way to ensure your agent is reliable and works as expected without requiring manual intervention or live API keys.

### Manual vs. Automated Testing

*   **Manual Testing (Interactive Shell):** Good for debugging and quickly trying out your agent. However, it requires a live LLM connection and is not easily repeatable.
*   **Automated Testing (`pytest`):** Best for creating a reliable, repeatable suite of tests. It uses a "mock" LLM, so no API key is needed. This is the recommended way to ensure your agent's logic is sound.

### Step 5.1: Create the Test Directory and File

```bash
mkdir -p exports/support_ticket_agent/tests
touch exports/support_ticket_agent/tests/test_agent.py
```

### Step 5.2: Write the Test Code

Paste the following code into your `exports/support_ticket_agent/tests/test_agent.py` file. This test simulates the agent's execution and verifies its output.

```python
import asyncio
import json
from pathlib import Path
import pytest
import tempfile
from core.framework.graph.edge import GraphSpec, EdgeSpec
from core.framework.graph.node import NodeSpec
from core.framework.graph.goal import Goal
from core.framework.graph.executor import GraphExecutor
from core.framework.runtime.core import Runtime
from core.framework.llm.provider import LLMProvider, LLMResponse

# A mock response object for the LLM provider
class MockLLMResponse(LLMResponse):
    def __init__(self, content, input_tokens=0, output_tokens=0):
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

# A mock LLM provider for testing
class MockLLMProvider(LLMProvider):
    def complete(self, messages, system="", json_mode=False):
        mock_analysis = {
            "category": "technical",
            "priority": "high"
        }
        return MockLLMResponse(content=json.dumps(mock_analysis))

    def complete_with_tools(self, messages, tools, system=""):
        return MockLLMResponse(content="mocked response with tools")

@pytest.fixture
def agent_graph():
    """Loads the agent graph from JSON and returns it as a GraphSpec."""
    agent_path = Path("exports/support_ticket_agent")
    agent_json_path = agent_path / "agent.json"
    assert agent_json_path.exists(), "agent.json not found at exports/support_ticket_agent/agent.json"
    with open(agent_json_path, "r") as f:
        agent_json = json.load(f)
    
    graph_data = agent_json["graph"]
    
    nodes = [NodeSpec(**node_data) for node_data in graph_data.get("nodes", [])]
    edges = [EdgeSpec(**edge_data) for edge_data in graph_data.get("edges", [])]
    
    graph_args = {
        "id": graph_data["id"],
        "goal_id": graph_data["goal_id"],
        "entry_node": graph_data["entry_node"],
        "nodes": nodes,
        "edges": edges,
        "terminal_nodes": graph_data.get("terminal_nodes", []),
        "memory_keys": graph_data.get("memory_keys", []),
        "description": graph_data.get("description", ""),
        "created_by": graph_data.get("created_by", ""),
    }

    optional_fields = [
        "default_model", 
        "max_tokens", 
        "max_steps", 
        "max_retries_per_node"
    ]
    for field in optional_fields:
        if field in graph_data and graph_data[field] is not None:
            graph_args[field] = graph_data[field]

    return GraphSpec(**graph_args)

@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for runtime storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.mark.asyncio
async def test_run_support_ticket_agent(agent_graph, temp_storage_path):
    """
    Tests that the support_ticket_agent can be loaded and executed successfully.
    """
    graph_spec = agent_graph

    goal = Goal(
        id="test-goal",
        name="Test Support Ticket Processing",
        description="A test to verify the support ticket agent can process a simple ticket.",
    )

    runtime = Runtime(storage_path=temp_storage_path)
    llm = MockLLMProvider()

    executor = GraphExecutor(runtime=runtime, llm=llm, tools=[])

    initial_input = {
        "ticket_content": "Hello, my account is not working and I cannot log in."
    }

    result = await executor.execute(
        graph=graph_spec,
        goal=goal,
        input_data=initial_input,
    )

    print("Agent final output:", result.output)

    assert result.success, f"Execution failed: {result.error}"
    assert result.output, "The agent should produce a final output in its memory"
    
    final_memory = result.output
    assert final_memory.get("category") == "technical", "The category should be set to 'technical'"
    assert final_memory.get("priority") == "high", "The priority should be set to 'high'"
```

### Step 5.3: Run the Automated Test

Execute the test using `pytest`. The `-s` flag is added to ensure the `print` statement's output is displayed.

**Command:**
```bash
. .venv/bin/activate && export PYTHONPATH=. && pytest -s exports/support_ticket_agent/tests/test_agent.py
```

**Expected Output:**
You will see the test pass and the final output of the agent's memory printed to the console.

```
...
exports/support_ticket_agent/tests/test_agent.py::test_run_support_ticket_agent Agent final output: {'ticket_content': '{"category": "technical", "priority": "high"}', 'result': '{"category": "technical", "priority": "high"}', 'category': 'technical', 'priority': 'high'}
PASSED
...
```

## 6. Key Files & Directories Explained

-   **`__init__.py` and `__main__.py`:** In the agent export directory, `__init__.py` makes the agent a Python package (useful for programmatic import), while `__main__.py` was for an older, deprecated method of running agents. **You do not need to create or modify these files.**

-   **`agent_logs` Directory:** This directory is **created automatically** the first time you execute an agent. It contains detailed, timestamped logs of every run, which is essential for debugging.
