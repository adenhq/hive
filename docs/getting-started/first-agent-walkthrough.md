# Your First Aden Agent (Beginner Walkthrough)

This guide walks you through building and running your **first goal-driven AI agent** using Aden.
No prior agent framework experience is required.

---

## What You Will Build

You will build a **simple research summary agent**.

**Input:** A topic  
**Output:** A short bullet-point summary  

This example demonstrates how Aden:
- Converts goals into agent graphs
- Runs agents without hardcoded workflows
- Handles execution automatically

---

## Prerequisites

Before starting, ensure you have:

- Python 3.11+
- Git installed
- Claude Code installed
- This repository cloned

Run the setup script:

```bash
./scripts/setup-python.sh
```

---

## Step 1: Define Your Goal

In Aden, you do not design workflows manually.
You describe the outcome.

Example goal:

> Build an agent that takes a topic as input and returns a concise bullet-point summary.

This goal will be used by the coding agent to generate the full agent structure.

---

## Step 2: Generate the Agent

Start Claude Code and run:

```bash
claude> /building-agents-construction
```

Claude will:
- Ask clarifying questions
- Generate the agent graph
- Create connection logic between nodes

You do not need to define nodes or edges manually.

---

## Step 3: Understand What Was Created

After generation, your agent includes:
- SDK-wrapped nodes
- Shared memory
- Tool access
- Observability hooks

Aden handles graph creation automatically based on your goal.

---

## Step 4: Run the Agent

Run the agent locally:

```bash
PYTHONPATH=core:exports python -m <your_agent_name> run --input '{...}'
```

Replace `<your_agent_name>` with the module name Claude created.

---

## What Happens If Something Fails?

If execution fails:
- Aden captures failure data
- Updates the agent configuration
- Evolving the graph automatically

This enables self-improving agents without manual intervention.

---

## Where to Go Next

- Learn about core concepts: [/concepts/overview]
- Add testing: [/building/testing]
- Explore MCP tools: [/mcp-server/introduction]

You’ve now built and run your first Aden agent.
