"""
Agent Builder Backend - Runs agents from UI definitions.

Start: python server.py
API: POST /api/run - Execute agent with input
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "exports"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Hive Agent Builder API")

# Allow CORS from UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NodeConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    node_type: str
    input_keys: list[str] = []
    output_keys: list[str] = []
    system_prompt: str = ""
    tools: list[str] = []
    is_entry: bool = False
    is_terminal: bool = False


class EdgeConfig(BaseModel):
    id: str
    source: str
    target: str


class AgentConfig(BaseModel):
    name: str
    description: str = ""
    nodes: list[NodeConfig]
    edges: list[EdgeConfig]


class RunRequest(BaseModel):
    agent_config: AgentConfig
    input: dict
    model: str = "gemini/gemini-2.0-flash"
    api_key: str = ""


@app.post("/api/run")
async def run_agent(request: RunRequest):
    """Execute an agent with the given config and input."""
    try:
        from framework.graph import NodeSpec, EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
        from framework.graph.edge import GraphSpec
        from framework.graph.executor import ExecutionResult
        from framework.runtime.agent_runtime import create_agent_runtime
        from framework.runtime.execution_stream import EntryPointSpec
        from framework.llm import LiteLLMProvider
        from framework.runner.tool_registry import ToolRegistry

        config = request.agent_config

        # Build goal
        goal = Goal(
            id=f"{config.name.lower().replace(' ', '_')}-goal",
            name=f"{config.name} Goal",
            description=config.description,
            success_criteria=[
                SuccessCriterion(
                    id="task-completion",
                    description="Complete the task",
                    metric="completion_rate",
                    target="100%",
                    weight=1.0,
                ),
            ],
            constraints=[],
        )

        # Build nodes
        nodes = []
        entry_node_id = None
        terminal_nodes = []

        for n in config.nodes:
            node = NodeSpec(
                id=n.id,
                name=n.name,
                description=n.description,
                node_type=n.node_type,
                input_keys=n.input_keys,
                output_keys=n.output_keys,
                system_prompt=n.system_prompt,
                tools=n.tools,
                max_retries=3,
            )
            nodes.append(node)

            if n.is_entry:
                entry_node_id = n.id
            if n.is_terminal:
                terminal_nodes.append(n.id)

        # Default to first node if no entry specified
        if not entry_node_id and nodes:
            entry_node_id = nodes[0].id

        # Build edges
        edges = [
            EdgeSpec(
                id=e.id,
                source=e.source,
                target=e.target,
                condition=EdgeCondition.ON_SUCCESS,
                priority=1,
            )
            for e in config.edges
        ]

        # Build graph
        # Use model from request or default
        model = request.model or "gemini/gemini-2.0-flash"

        graph = GraphSpec(
            id=f"{config.name.lower().replace(' ', '_')}-graph",
            goal_id=goal.id,
            version="1.0.0",
            entry_node=entry_node_id,
            entry_points={"start": entry_node_id},
            terminal_nodes=terminal_nodes,
            pause_nodes=[],
            nodes=nodes,
            edges=edges,
            default_model=model,
            max_tokens=4096,
        )

        # Setup tools
        tool_registry = ToolRegistry()

        # Load hive-tools MCP server
        tools_path = Path(__file__).parent.parent / "tools"
        mcp_config = {
            "name": "hive-tools",
            "transport": "stdio",
            "command": "python",
            "args": ["mcp_server.py", "--stdio"],
            "cwd": str(tools_path),
        }
        tool_registry.register_mcp_server(mcp_config)

        print(f"[RUN DEBUG] Registered tools: {list(tool_registry.get_tools().keys())}")
        print(f"[RUN DEBUG] Node tools config: {[n.tools for n in nodes]}")

        # Set API key from request if provided
        if request.api_key:
            # Determine which env var to set based on model
            if model.startswith("gemini/"):
                os.environ["GEMINI_API_KEY"] = request.api_key
            elif model.startswith("gpt-") or model.startswith("openai/"):
                os.environ["OPENAI_API_KEY"] = request.api_key
            elif model.startswith("claude-") or model.startswith("anthropic/"):
                os.environ["ANTHROPIC_API_KEY"] = request.api_key

        # Setup LLM
        llm = LiteLLMProvider(model=model)

        # Create runtime
        storage_path = Path.home() / ".hive" / "ui_test"
        storage_path.mkdir(parents=True, exist_ok=True)

        runtime = create_agent_runtime(
            graph=graph,
            goal=goal,
            storage_path=storage_path,
            entry_points=[
                EntryPointSpec(
                    id="start",
                    name="Start",
                    entry_node=entry_node_id,
                    trigger_type="manual",
                    isolation_level="shared",
                )
            ],
            llm=llm,
            tools=list(tool_registry.get_tools().values()),
            tool_executor=tool_registry.get_executor(),
        )

        # Run agent
        await runtime.start()
        try:
            result = await runtime.trigger_and_wait("start", request.input, timeout=120)

            if result is None:
                return {
                    "success": False,
                    "error": "Execution timeout",
                    "output": None,
                }

            return {
                "success": result.success,
                "steps_executed": result.steps_executed,
                "output": result.output,
                "error": result.error,
            }
        finally:
            await runtime.stop()

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


class TestNodeRequest(BaseModel):
    node: NodeConfig
    input_data: dict
    model: str = "gemini/gemini-2.0-flash"
    api_key: str = ""


@app.post("/api/test-node")
async def test_node(request: TestNodeRequest):
    """Test a single node with given input."""
    try:
        from framework.llm import LiteLLMProvider
        from framework.runner.tool_registry import ToolRegistry

        node = request.node
        model = request.model or "gemini/gemini-2.0-flash"

        # Set API key from request if provided
        if request.api_key:
            if model.startswith("gemini/"):
                os.environ["GEMINI_API_KEY"] = request.api_key
            elif model.startswith("gpt-") or model.startswith("openai/"):
                os.environ["OPENAI_API_KEY"] = request.api_key
            elif model.startswith("claude-") or model.startswith("anthropic/"):
                os.environ["ANTHROPIC_API_KEY"] = request.api_key

        # Setup tools if needed
        tool_registry = ToolRegistry()
        tools_list = []
        tool_executor = None

        if node.tools:
            tools_path = Path(__file__).parent.parent / "tools"
            mcp_config = {
                "name": "hive-tools",
                "transport": "stdio",
                "command": "python",
                "args": ["mcp_server.py", "--stdio"],
                "cwd": str(tools_path),
            }
            tool_registry.register_mcp_server(mcp_config)
            tools_list = list(tool_registry.get_tools().values())
            tool_executor = tool_registry.get_executor()

        # Setup LLM
        llm = LiteLLMProvider(model=model)

        # Build prompt
        input_str = "\n".join([f"{k}: {v}" for k, v in request.input_data.items()])

        messages = [
            {"role": "system", "content": node.system_prompt},
            {"role": "user", "content": input_str}
        ]

        # Get available tools for this node
        node_tools = []
        print(f"[DEBUG] Node tools requested: {node.tools}")
        print(f"[DEBUG] Available tools: {[t.name for t in tools_list]}")
        if node.tools and tools_list:
            node_tools = [t for t in tools_list if t.name in node.tools]
        print(f"[DEBUG] Matched node_tools: {[t.name for t in node_tools]}")

        # Call LLM
        print(f"[DEBUG] System prompt: {node.system_prompt[:100]}...")
        print(f"[DEBUG] Calling LLM with {len(node_tools)} tools")
        if node_tools and tool_executor:
            # Tool use node - use complete_with_tools which handles tool loop internally
            response = llm.complete_with_tools(
                messages=messages,
                system=node.system_prompt,
                tools=node_tools,
                tool_executor=tool_executor,
                max_iterations=5,
            )
            final_response = response.content
            # Extract tool calls from raw response if available
            all_tool_calls = []
            if response.raw_response and hasattr(response.raw_response, 'choices'):
                for choice in response.raw_response.choices:
                    if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                        for tc in choice.message.tool_calls:
                            all_tool_calls.append({"name": tc.function.name, "args": tc.function.arguments})
        else:
            # Simple generation
            response = llm.complete(messages)
            final_response = response.content
            all_tool_calls = []

        # Parse output
        import re
        content = final_response or ""
        if "```" in content:
            content = re.sub(r'```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```', '', content)

        try:
            output = json.loads(content.strip())
        except:
            output = {"raw_response": content}

        return {
            "success": True,
            "node_id": node.id,
            "input": request.input_data,
            "output": output,
            "tool_calls": all_tool_calls,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Run:")
        print('   export GEMINI_API_KEY="your-key"')
        print()

    print("🚀 Starting Agent Builder Backend")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
