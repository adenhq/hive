"""
Minimal Manual Agent Example
----------------------------
This example demonstrates how to build and run an agent programmatically
without using the Claude Code CLI or external LLM APIs.

It uses 'function' nodes to define logic in pure Python, making it perfect
for understanding the core runtime loop:
Setup -> Graph definition -> Execution -> Result

What this demo does:
    Constructs a two-node graph (greeter -> uppercaser), feeds in a hard-coded
    name, and prints the uppercased greeting.  No LLM calls are involved;
    every node is a plain Python function.

Run with:
    uv run python core/examples/manual_agent.py
"""

import asyncio

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime


# 1. Define Node Logic (Pure Python Functions)
# "greeter" node — takes a name string and returns a greeting.
# "uppercaser" node — takes that greeting and returns it in uppercase.
# Together they form a simple pipeline: name -> greeting -> GREETING.
def greet(name: str) -> str:
    """Generate a simple greeting."""
    return f"Hello, {name}!"


def uppercase(greeting: str) -> str:
    """Convert text to uppercase."""
    return greeting.upper()


async def main():
    print("🚀 Setting up Manual Agent...")

    # 2. Define the Goal
    # Every agent needs a goal with success criteria
    goal = Goal(
        id="greet-user",
        name="Greet User",
        description="Generate a friendly uppercase greeting",
        success_criteria=[
            {
                "id": "greeting_generated",
                "description": "Greeting produced",
                "metric": "custom",
                "target": "any",
            }
        ],
    )

    # 3. Define Nodes
    # Nodes describe steps in the process
    node1 = NodeSpec(
        id="greeter",
        name="Greeter",
        description="Generates a simple greeting",
        node_type="function",
        function="greet",  # Matches the registered function name
        input_keys=["name"],
        output_keys=["greeting"],
    )

    node2 = NodeSpec(
        id="uppercaser",
        name="Uppercaser",
        description="Converts greeting to uppercase",
        node_type="function",
        function="uppercase",
        input_keys=["greeting"],
        output_keys=["final_greeting"],
    )

    # 4. Define Edges
    # Edges define the flow between nodes
    edge1 = EdgeSpec(
        id="greet-to-upper",
        source="greeter",
        target="uppercaser",
        condition=EdgeCondition.ON_SUCCESS,
    )

    # 5. Create Graph
    # The graph works like a blueprint connecting nodes and edges
    graph = GraphSpec(
        id="greeting-agent",
        goal_id="greet-user",
        entry_node="greeter",
        terminal_nodes=["uppercaser"],
        nodes=[node1, node2],
        edges=[edge1],
    )

    # 6. Initialize Runtime & Executor
    # Runtime handles state/memory; Executor runs the graph
    from pathlib import Path

    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime)

    # 7. Register Function Implementations
    # Connect string names in NodeSpecs to actual Python functions
    executor.register_function("greeter", greet)
    executor.register_function("uppercaser", uppercase)

    # 8. Execute Agent
    # Input is hard-coded here because this is a self-contained demo whose
    # purpose is to illustrate the runtime flow, not to be a production tool.
    # For dynamic input, replace the dict below with e.g.:
    #     import sys
    #     input_data = {"name": sys.argv[1] if len(sys.argv) > 1 else "Alice"}
    print("▶ Executing agent with input: name='Alice'...")

    result = await executor.execute(graph=graph, goal=goal, input_data={"name": "Alice"})

    # 9. Verify Results
    if result.success:
        print("\n✅ Success!")
        print(f"Path taken: {' -> '.join(result.path)}")
        print(f"Final output: {result.output.get('final_greeting')}")
    else:
        print(f"\n❌ Failed: {result.error}")


if __name__ == "__main__":
    # Optional: Enable logging to see internal decision flow
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
