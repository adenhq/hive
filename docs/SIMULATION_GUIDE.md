# Hive Simulation Mode Guide

Simulation Mode allows you to develop, test, and debug Hive agents in a fully sandboxed environment. It replaces real LLM calls with a **MockLLMProvider** and uses canned or generated tool responses to ensure 100% safe execution without costs or side effects.

## 🚀 Why Use Simulation Mode?

- **Cost Efficient**: No tokens are spent during simulation. Perfect for rapid iterative development.
- **Safety First**: Real tools (like file deletion, financial transfers, or email sending) are replaced with mocks.
- **Predictable Testing**: Use deterministic "canned" responses to test complex edge cases and retry logic.
- **CI/CD Friendly**: Run agent regression tests in your pipeline without needing API keys or external services.

---

## 🏗️ Building an Agent for Simulation

While every agent can run in simulation mode, well-structured agents provide a much higher fidelity experience.

### 1. Define Explicit Output Keys
The simulator uses `output_keys` declared in your `agent.json` to generate structured mock data. Always include them in your node prompt hints:

```json
{
  "id": "audit_node",
  "name": "Bug Analyzer",
  "node_type": "llm_generate",
  "system_prompt": "Analyze the code... output_keys: [bugs_list]",
  "output_keys": ["bugs_list"]
}
```

### 2. Use the `@tool` Decorator
Ensure all Python functions are decorated with `@tool` in your `tools.py`. This allows the `ToolRegistry` to properly manage them in both real and simulation modes.

```python
from core.framework.runner.tool_registry import tool

@tool(description="Calculates mood intensity")
def get_mood_score(text: str) -> int:
    return len(text)
```

---

## ⚙️ Configuring Simulation Responses

Simulation behavior is controlled via a `simulation_config.json` file located in your agent's directory.

### Canned Responses
You can provide specific results for tool calls. If a tool is called with arguments that don't match any specific entry, it falls back to the `default` key.

```json
{
  "tools": {
    "web_search": {
      "default": "Simulated search result: The weather today is sunny."
    },
    "format_report": {
      "default": "# Mock Report\n\nGenerated for testing purposes."
    }
  }
}
```

### Smart Mock Heuristics
If no mock result is provided for a tool, Hive's **Smart Mock** system attempts to generate a realistic response based on the tool's name:
- Tools containing "search" or "read" return text snippets.
- Tools containing "list" return array structures.
- Tools containing "status" return boolean or "OK" strings.

---

## 🏃 Running the Simulator

Use the `--simulate` (or `-s`) flag with the Hive CLI.

### Basic Simulation
```bash
python -m framework.cli run exports/my_agent --input '{"key": "value"}' --simulate
```

### Verbose Simulation (Recommended)
Shows the internal logic of the simulator, including tool interceptions and mock data mapping.
```bash
python -m framework.cli run exports/my_agent -i '{"q": "test"}' -s --verbose
```

### Simulation with Specific Config
If you have multiple test scenarios, you can specify different simulation configs:
```bash
python -m framework.cli run exports/my_agent -s --sim-config tests/edge_case_sim.json
```

---

## 📊 Understanding Simulation Traces

After every run, a simulation trace is saved to `simulations/trace_<run_id>.json`. This file contains:
- **Path**: Exactly which nodes were visited.
- **Data Flow**: Every input and output for every node.
- **Metrics**: Theoretical token counts and latency (recorded as 0 in simulation).

---

## 💡 Best Practices

1. **Keep it Small**: Start with a single node and verify its simulation output before building the full graph.
2. **Standardize Keys**: Use consistent keys like `result`, `success`, or `response` across your nodes to help the Smart Mock heuristics.
3. **Verify in Real Mode**: Once the simulation flow looks perfect, run once in Real Mode to ensure the LLM understands your prompts as expected.
