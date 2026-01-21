# Example: Calculator Agent

A simple agent that evaluates mathematical expressions.

## Goal

```python
from framework.graph import Goal, SuccessCriterion, Constraint

goal = Goal(
    id="calculator",
    name="Calculator",
    description="Evaluate mathematical expressions accurately",
    success_criteria=[
        SuccessCriterion(
            id="correct-result",
            description="Mathematical result is correct",
            metric="output_equals_expected",
            target="exact_match",
            weight=1.0,
        ),
    ],
    constraints=[
        Constraint(
            id="no-crash",
            description="Invalid operations return 'Error', not exceptions",
            constraint_type="hard",
            category="safety",
            check="no_exception",
        ),
    ],
)
```

## Nodes

```python
from framework.graph import NodeSpec

nodes = [
    NodeSpec(
        id="calculator",
        name="Calculator",
        description="Evaluate the mathematical expression",
        node_type="llm_tool_use",
        input_keys=["expression"],
        output_keys=["result"],
        tools=["calculate"],
        system_prompt="Calculate the expression using the calculate tool. Return only the numeric result.",
    ),
    NodeSpec(
        id="formatter",
        name="Formatter",
        description="Format the result for display",
        node_type="llm_generate",
        input_keys=["result"],
        output_keys=["formatted"],
        system_prompt="Format the number for display. Output only the formatted result.",
    ),
]
```

## Edges

```python
from framework.graph import EdgeSpec, EdgeCondition

edges = [
    EdgeSpec(
        id="calc-to-format",
        source="calculator",
        target="formatter",
        condition=EdgeCondition.ON_SUCCESS,
    ),
]
```

## Graph

```python
from framework.graph.edge import GraphSpec

graph = GraphSpec(
    id="calculator-graph",
    goal_id=goal.id,
    entry_node="calculator",
    terminal_nodes=["formatter"],
    nodes=nodes,
    edges=edges,
)
```

## Tool Definition

```python
from framework.llm.provider import Tool, ToolResult

tools = [
    Tool(
        name="calculate",
        description="Evaluate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"],
        },
    ),
]

def tool_executor(ctx, tool_use):
    if tool_use.name == "calculate":
        expr = tool_use.input["expression"]
        try:
            # Safe evaluation (in production, use a proper math parser)
            result = eval(expr.replace('×', '*').replace('÷', '/'))
            return ToolResult(tool_use.id, json.dumps({"result": result}), False)
        except Exception:
            return ToolResult(tool_use.id, json.dumps({"error": "Error"}), True)
    return ToolResult(tool_use.id, json.dumps({"error": "Unknown tool"}), True)
```

## Running

```python
from core import Runtime
from framework.llm import AnthropicProvider
from framework.graph import GraphExecutor

async def run():
    runtime = Runtime("/tmp/calculator")
    llm = AnthropicProvider()

    executor = GraphExecutor(
        runtime=runtime,
        llm=llm,
        tools=tools,
        tool_executor=tool_executor,
    )

    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={"expression": "2 + 3 * 4"},
    )

    print(f"Result: {result.output}")
```

## Architecture

```
┌────────────┐    on_success    ┌───────────┐
│ Calculator │ ───────────────► │ Formatter │
│ (tool_use) │                  │ (generate)│
└────────────┘                  └───────────┘
     │                                │
  calculate                      formats
  tool call                      output
```
