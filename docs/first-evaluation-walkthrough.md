# First Evaluation Walkthrough

You've completed the [Quickstart](./getting-started.md), everything installed, and you're ready to run an agent. Now what?

This walkthrough bridges the gap between "setup complete" and "I understand what's happening." You'll run an agent, learn what to observe, understand what success looks like, and make small changes to build intuition about how Hive works.

## Prerequisites

- Completed [Quickstart](./getting-started.md) setup (`./quickstart.sh` ran successfully)
- You're in the `hive/` project root directory

No API keys are required for this walkthrough. Everything runs locally with pure Python functions.

---

## Step 1: Run the Manual Agent

The fastest way to see Hive in action is the minimal manual agent. It uses `function` nodes (plain Python, no LLM calls), so there's nothing external to configure.

```bash
uv run python core/examples/manual_agent.py
```

### What You Should See

```
🚀 Setting up Manual Agent...
▶ Executing agent with input: name='Alice'...

✅ Success!
Path taken: greeter -> uppercaser
Final output: HELLO, ALICE!
```

If you see this, the core runtime is working: graph construction, node execution, edge traversal, and shared memory all functioned correctly.

### What Just Happened

Here's what the framework did behind the scenes:

1. **Goal defined** — A `Goal` object was created with a success criterion (`greeting_generated`). This is the outcome the agent is working toward.
2. **Graph built** — Two `function` nodes (`greeter` → `uppercaser`) were connected by an edge that fires on success.
3. **Execution started** — The `GraphExecutor` entered the graph at the `greeter` node.
4. **Shared memory flowed** — `greeter` read `name` from input, wrote `greeting`. `uppercaser` read `greeting`, wrote `final_greeting`. Each node only accessed the keys it declared.
5. **Graph completed** — The executor followed the edge from `greeter` to `uppercaser`, reached the terminal node, and reported success.

This is the same execution model that powers complex multi-node agents with LLM calls, tool use, and human-in-the-loop — just with simpler nodes.

---

## Step 2: Enable Logging and Observe the Runtime

The manual agent has a commented-out logging line. Let's enable it to see the framework's internal decisions.

Open `core/examples/manual_agent.py` and find the line near the bottom:

```python
# Optional: Enable logging to see internal decision flow
# logging.basicConfig(level=logging.INFO)
```

Uncomment it (and add the import at the top of the file if it's not already there):

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Run again:

```bash
uv run python core/examples/manual_agent.py
```

### What to Look For in the Logs

With logging enabled, you'll see messages from the framework internals. Pay attention to these patterns:

| Log pattern | What it tells you |
|---|---|
| Node entry/exit messages | Which node is executing and in what order |
| Edge evaluation | Which edges were checked and which condition matched |
| Memory read/write | What data flowed between nodes through shared memory |
| Execution path | The full route the executor took through the graph |

This is the same observability infrastructure that powers the TUI dashboard and event streaming in production agents. Even in this minimal example, you can see the executor's decision-making process.

> **Tip:** For even more detail, try `logging.basicConfig(level=logging.DEBUG)`. This is verbose but useful when you're trying to understand exactly how the runtime handles a specific step.

---

## Step 3: Check the Execution Artifacts

The manual agent writes runtime data to `./agent_logs/`. After a run, inspect what's there:

```bash
ls -la agent_logs/
```

Hive uses file-based persistence (no database required). For exported agents run via the CLI or `AgentRunner`, runtime logs are written under the agent’s storage path:

```
~/.hive/agents/{agent_name}/runtime_logs/
  sessions/{session_id}/logs/
    summary.json     # Level 1 summary
    details.jsonl    # Level 2 node details
    tool_logs.jsonl  # Level 3 tool logs
```

The manual agent uses a minimal runtime and may not write logs. To inspect runtime logs, run an exported agent and then inspect the session folder, for example:

```bash
ls -la ~/.hive/agents/your_agent/runtime_logs/sessions/
```

This JSON contains everything that happened: which nodes ran, what they produced, the path taken through the graph, and the final outcome. In production agents, this data is what the [evolution](./key_concepts/evolution.md) process uses to diagnose failures and improve future generations.

---

## Step 4: Understand What Success Looks Like

Now that you've seen a successful run, let's be precise about what "success" means in Hive.

### Immediate signals (this run)

**`result.success == True`** — visible in the script output as `✅ Success!`
The graph reached a terminal node without errors.

**`result.path`** — visible in the script output as `Path taken: ...`
The executor traversed the expected nodes in order.

**`result.output`** — visible in the script output as `Final output: ...`
The terminal node produced the expected data in shared memory.

**No exceptions** — the script exits cleanly
Runtime, graph, and nodes all operated without errors.

### Deeper signals (production agents)

In a real agent with LLM nodes and success criteria, you'd also check:

- **Success criteria scores** — Each criterion in the goal gets evaluated and weighted. A run can succeed partially (e.g., 0.7 out of 1.0) rather than just pass/fail.
- **Constraint compliance** — Hard constraints (like budget limits or safety rules) must not be violated. Soft constraints are warnings.
- **Decision log** — Every decision the agent made is recorded. This is what makes [evolution](./key_concepts/evolution.md) possible — without it, failure analysis is guesswork.
- **Cost metrics** — LLM token usage and estimated cost per node and per run.

The manual agent is simple enough that `result.success == True` with the right output is sufficient. But the framework evaluates the same way at every scale.

---

## Step 5: Make Small Changes and Observe

The best way to build intuition is to modify the agent and see what happens. Here are three experiments, ordered by increasing complexity.

### Experiment A: Add a Third Node

Add a new function and wire it into the graph. In `core/examples/manual_agent.py`:

**1. Define a new function:**

```python
def add_emoji(text: str) -> str:
    """Add a wave emoji to the greeting."""
    return f"👋 {text}"
```

**2. Create a new NodeSpec:**

```python
node3 = NodeSpec(
    id="emoji_adder",
    name="Emoji Adder",
    description="Adds a wave emoji to the greeting",
    node_type="function",
    function="add_emoji",
    input_keys=["final_greeting"],
    output_keys=["decorated_greeting"],
)
```

**3. Add an edge from `uppercaser` to the new node:**

```python
edge2 = EdgeSpec(
    id="upper-to-emoji",
    source="uppercaser",
    target="emoji_adder",
    condition=EdgeCondition.ON_SUCCESS,
)
```

**4. Update the graph spec:**

- Add `node3` to the `nodes` list
- Add `edge2` to the `edges` list (you'll need to create an `edges` field or update accordingly)
- Change `terminal_nodes` from `["uppercaser"]` to `["emoji_adder"]`

**5. Register the function:**

```python
executor.register_function("emoji_adder", add_emoji)
```

**6. Update the output key in the result check:**

```python
print(f"Final output: {result.output.get('decorated_greeting')}")
```

Run it. You should see:

```
Path taken: greeter -> uppercaser -> emoji_adder
Final output: 👋 HELLO, ALICE!
```

**What this teaches you:** Nodes are composable units. Adding a step means defining a function, creating a `NodeSpec`, wiring an edge, and registering the implementation. The framework handles execution order, memory flow, and result aggregation.

### Experiment B: Introduce a Failure Path

What happens when a node fails? Let's find out.

Replace the `uppercase` function with one that sometimes fails:

```python
import random

def uppercase(greeting: str) -> str:
    """Convert text to uppercase, but sometimes fail."""
    if random.random() < 0.5:
        raise ValueError("Simulated failure: couldn't process greeting")
    return greeting.upper()
```

Run the agent several times:

```bash
for i in $(seq 1 5); do uv run python core/examples/manual_agent.py; echo "---"; done
```

**What to observe:**

- Some runs succeed (`✅ Success!`) and some fail (`❌ Failed: ...`)
- Failed runs report which node caused the failure
- The execution path is shorter on failure (stops at the failing node)

**What this teaches you:** The framework captures *where* and *why* failures happen. In a production agent, this failure data is exactly what the [evolution](./key_concepts/evolution.md) process uses. It doesn't just know "the agent failed" — it knows "node `uppercaser` raised a `ValueError` because..." That specificity is what allows a coding agent to make targeted fixes in the next generation.

### Experiment C: Add Weighted Success Criteria

Modify the goal to have multiple weighted success criteria:

```python
goal = Goal(
    id="greet-user",
    name="Greet User",
    description="Generate a friendly uppercase greeting",
    success_criteria=[
        {
            "id": "greeting_generated",
            "description": "A greeting was produced",
            "metric": "custom",
            "target": "any",
            "weight": 0.5,
        },
        {
            "id": "greeting_uppercase",
            "description": "The greeting is fully uppercase",
            "metric": "custom",
            "target": "any",
            "weight": 0.5,
        },
    ],
)
```

**What this teaches you:** Goals aren't binary. In Hive, [Outcome-Driven Development](./key_concepts/goals_outcome.md) means defining *what good looks like* with weighted, multi-dimensional criteria. An agent that produces a greeting but doesn't uppercase it has partially succeeded. The weights express what matters most — and give the evolution process a precise target for improvement.

---

## Step 6: Validate with Mock Mode (Optional)

If you want to validate the structure of a full agent without making LLM calls, use mock mode in tests:

```bash
MOCK_MODE=1 pytest exports/your_agent/tests/
```

Mock mode is for structure validation only — it does not verify LLM behavior or output quality. It’s useful for:

- Verifying graph structure before spending on API calls
- Testing edge conditions and routing logic
- CI/CD pipelines where you want fast structural validation

---

## What to Explore Next

Now that you understand the execution model, here's where to go depending on what interests you:

| If you want to... | Go to... |
|---|---|
| Build a real agent with LLM nodes | [Getting Started: Build Your First Agent](./getting-started.md#building-your-first-agent) |
| Understand how goals drive agent behavior | [Goals & Outcome-Driven Development](./key_concepts/goals_outcome.md) |
| Learn how graphs, nodes, and edges work | [The Agent Graph](./key_concepts/graph.md) |
| Understand how agents improve over time | [Evolution](./key_concepts/evolution.md) |
| See a full agent template you can customize | [Example Templates](../examples/templates/) |
| Use the interactive TUI dashboard | Run `hive tui` from the project root |
| Set up API keys for LLM-powered agents | [Configuration Guide](./configuration.md) |
| Run and debug agents in production | [Developer Guide](./developer-guide.md) |

---

## Quick Reference: Evaluation Checklist

Use this checklist after any agent run to confirm things are working:

- [ ] **Did the agent complete?** — Check for `Success` or `Failed` in output
- [ ] **Was the path correct?** — Verify the node execution order matches your graph
- [ ] **Is the output what you expected?** — Check the final shared memory values
- [ ] **Are artifacts written?** — Look in the storage directory for run records
- [ ] **Were constraints respected?** — No hard constraint violations in logs
- [ ] **Do logs make sense?** — Enable `INFO` or `DEBUG` logging if anything is unclear

For production agents, also check:

- [ ] **Success criteria scores** — Are they meeting your thresholds?
- [ ] **Cost within budget** — Are LLM costs within the goal's constraints?
- [ ] **Decision log populated** — Is the agent recording its reasoning?
- [ ] **HITL nodes pausing correctly** — Are human checkpoints working?

---

*This walkthrough is part of the Hive documentation. For setup instructions, see [Getting Started](./getting-started.md). For the full developer workflow, see the [Developer Guide](./developer-guide.md).*