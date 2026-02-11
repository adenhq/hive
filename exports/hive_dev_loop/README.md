# 🐝 Hive Dev Loop: Autonomous TDD Reference Agent

A reference Test-Driven Development (TDD) agent built on the Hive framework.

This agent demonstrates how an autonomous development loop can be implemented using the graph architecture: generating tests, writing code, executing `pytest` in a sandbox, and iteratively fixing failures based on runtime logs.

## Core Features

* **End-to-end TDD loop:** Converts a natural language task into a failing test, generates implementation, executes `pytest`, and performs iterative debugging until tests pass.
* **Linear state propagation:** Ensures stable context flow between nodes to avoid state-loss across graph transitions.
* **AST validation guardrails:** Validates generated Python code before writing to disk to prevent syntax-level crashes during execution.
* **Autonomous debugging:** When `pytest` fails, terminal logs are routed back into a debugger node which generates patches and re-runs verification automatically.
* **Execution telemetry:** Generates an execution report including runtime metrics and produced artifacts.

## Graph Flow

1. `plan_task` – analyze user request and create execution plan
2. `write_test` – generate pytest test suite
3. `save_test` – validate and write test file
4. `write_code` – generate implementation
5. `save_code` – validate and write code
6. `run_pytest` – execute tests
7. `debug_loop` – analyze failures and patch
8. `verify` – re-run tests
9. `finalize` – generate execution report

## Running the Agent

### With Claude/OpenAI
Set API key:
```
set ANTHROPIC_API_KEY=your_key
Run:
python exports/hive_dev_loop/agent.py
```
## Output
On successful execution the agent generates:
1. `solution.py`
2. `solution_test.py`
3. `execution_report.md`

## Purpose

This project is a reference implementation for building autonomous development agents on Hive and demonstrates structured graph-based agent design.