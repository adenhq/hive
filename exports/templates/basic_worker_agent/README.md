# Basic Worker Agent (Template)

A minimal, runnable template for building goal-driven worker agents using the Hive framework.

This agent is intentionally simple. It is designed as a **starting point for contributors** who want to understand agent structure and build new worker agents using a copy-and-extend workflow.

## Purpose

This template helps developers:

- Understand the minimum required agent structure
- Start building worker agents quickly
- Validate their environment and runtime setup
- Avoid unnecessary complexity early on

## What This Template Includes

- A minimal goal definition with success criteria and constraints
- A small, linear workflow
- `AgentRuntime` setup
- CLI entry points (`info`, `validate`, `run`)
- A simple Python API interface

## Workflow Overview

The agent follows a simple execution flow:

1. Parse input
2. Perform task
3. Format output

This structure can be extended with routers, tools, pause/resume, or HITL later.

## CLI Usage

```bash
# Show agent info
python -m online_research_agent info

# Validate agent structure
python -m online_research_agent validate

# Mock run
python -m basic_worker_agent run --mock
```
## Python Usage

Example usage from Python:

    from basic_worker_agent import default_agent

    result = await default_agent.run({"input": "Explain recursion simply"})

    if result.success:
        print(result.output)

## How to Extend This Template

To create your own agent from this template:

1. Copy the agent directory and rename it
2. Update the goal definition in agent.py
3. Modify or add nodes in nodes/__init__.py
4. Adjust edges in agent.py
5. Customize prompts and schemas for your task

This template is intentionally minimal so contributors can understand the framework before adding complexity.

## Recommended Next Steps

- Add tool-based nodes
- Introduce routing or branching
- Add pause/resume for human-in-the-loop flows
- Write tests using the testing-agent skill

## Notes

- This template is meant for learning and iteration
- Advanced patterns are intentionally excluded
- Designed to be copied, not modified in place
