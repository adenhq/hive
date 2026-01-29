#!/usr/bin/env python3
"""
Example: Integrating MCP Servers with the Core Framework

This example demonstrates how to:
1. Register MCP servers programmatically
2. Use MCP tools in agents
3. Load MCP servers from configuration files

Prerequisites:
    Run this script from the core/ directory.
    Examples 1-3 use a minimal task-planner agent that is auto-created.
"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from framework.runner.runner import AgentRunner


def create_minimal_agent(agent_path: Path, agent_name: str = "task-planner") -> Path:
    """
    Create a minimal agent for MCP integration examples.

    Creates an agent.json file directly with the required format,
    suitable for demonstrating MCP tool integration.

    Args:
        agent_path: Directory to create the agent in
        agent_name: Name for the agent

    Returns:
        Path to the created agent directory
    """
    agent_path.mkdir(parents=True, exist_ok=True)

    # Create minimal agent.json directly (following the format from export_graph)
    agent_data = {
        "agent": {
            "id": agent_name,
            "name": agent_name.replace("-", " ").title(),
            "version": "1.0.0",
            "description": "Minimal agent for MCP integration examples",
        },
        "graph": {
            "id": f"{agent_name}-graph",
            "goal_id": agent_name,
            "version": "1.0.0",
            "entry_node": "planner",
            "entry_points": {"start": "planner"},
            "pause_nodes": [],
            "terminal_nodes": ["planner"],
            "nodes": [
                {
                    "id": "planner",
                    "name": "Task Planner",
                    "description": "Plan and execute tasks using available tools",
                    "node_type": "llm_tool_use",
                    "system_prompt": "Complete the following task: {objective}",
                    "tools": [],  # Tools will be added via MCP
                    "input_keys": ["objective"],
                    "output_keys": ["result"],
                }
            ],
            "edges": [],
            "max_steps": 100,
            "max_retries_per_node": 3,
            "description": f"Graph for {agent_name}",
            "created_at": datetime.now().isoformat(),
        },
        "goal": {
            "id": agent_name,
            "name": agent_name.replace("-", " ").title(),
            "description": "Minimal agent for MCP integration examples",
            "success_criteria": [
                {
                    "id": "task-complete",
                    "description": "Successfully complete the assigned task",
                    "metric": "completion",
                    "target": "100%",
                    "weight": 1.0,
                }
            ],
            "constraints": [],
        },
        "required_tools": [],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "node_count": 1,
            "edge_count": 0,
        },
    }

    # Write agent.json
    agent_json_path = agent_path / "agent.json"
    with open(agent_json_path, "w") as f:
        json.dump(agent_data, f, indent=2)

    return agent_path


async def example_1_programmatic_registration():
    """Example 1: Register MCP server programmatically"""
    print("\n=== Example 1: Programmatic MCP Server Registration ===\n")

    # Create a temporary agent for this example
    temp_dir = Path(tempfile.mkdtemp(prefix="mcp_example_"))
    agent_path = temp_dir / "task-planner"

    try:
        create_minimal_agent(agent_path)
        runner = AgentRunner.load(agent_path)

        # Register tools MCP server via STDIO
        num_tools = runner.register_mcp_server(
            name="tools",
            transport="stdio",
            command="python",
            args=["-m", "aden_tools.mcp_server", "--stdio"],
            cwd="../tools",
        )

        print(f"Registered {num_tools} tools from tools MCP server")

        # List all available tools
        tools = runner._tool_registry.get_tools()
        print(f"\nAvailable tools: {list(tools.keys())}")

        # Run the agent with MCP tools available
        result = await runner.run(
            {"objective": "Search for 'Claude AI' and summarize the top 3 results"}
        )

        print(f"\nAgent result: {result}")

        # Cleanup
        runner.cleanup()

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def example_2_http_transport():
    """Example 2: Connect to MCP server via HTTP"""
    print("\n=== Example 2: HTTP MCP Server Connection ===\n")

    # First, start the tools MCP server in HTTP mode:
    # cd tools && python mcp_server.py --port 4001

    # Create a temporary agent for this example
    temp_dir = Path(tempfile.mkdtemp(prefix="mcp_example_"))
    agent_path = temp_dir / "task-planner"

    try:
        create_minimal_agent(agent_path)
        runner = AgentRunner.load(agent_path)

        # Register tools via HTTP
        num_tools = runner.register_mcp_server(
            name="tools-http",
            transport="http",
            url="http://localhost:4001",
        )

        print(f"Registered {num_tools} tools from HTTP MCP server")

        # Cleanup
        runner.cleanup()

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def example_3_config_file():
    """Example 3: Load MCP servers from configuration file"""
    print("\n=== Example 3: Load from Configuration File ===\n")

    # Create a temporary agent for this example
    temp_dir = Path(tempfile.mkdtemp(prefix="mcp_example_"))
    agent_path = temp_dir / "task-planner"

    try:
        create_minimal_agent(agent_path)

        # Copy example config to the agent folder
        examples_dir = Path(__file__).parent
        shutil.copy(
            examples_dir / "mcp_servers.json",
            agent_path / "mcp_servers.json"
        )

        # Load agent - MCP servers will be auto-discovered
        runner = AgentRunner.load(agent_path)

        # Tools are automatically available
        tools = runner._tool_registry.get_tools()
        print(f"Available tools: {list(tools.keys())}")

        # Cleanup
        runner.cleanup()

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def example_4_custom_agent_with_mcp_tools():
    """Example 4: Build custom agent that uses MCP tools"""
    print("\n=== Example 4: Custom Agent with MCP Tools ===\n")

    # Create a temporary directory for the agent export
    temp_dir = Path(tempfile.mkdtemp(prefix="mcp_example_"))
    export_path = temp_dir / "web-research-agent"

    try:
        # Create agent.json directly with multi-node graph
        agent_data = {
            "agent": {
                "id": "web-research-agent",
                "name": "Web Research Agent",
                "version": "1.0.0",
                "description": "Search the web and summarize findings",
            },
            "graph": {
                "id": "web-research-agent-graph",
                "goal_id": "web-researcher",
                "version": "1.0.0",
                "entry_node": "web-searcher",
                "entry_points": {"start": "web-searcher"},
                "pause_nodes": [],
                "terminal_nodes": ["summarizer"],
                "nodes": [
                    {
                        "id": "web-searcher",
                        "name": "Web Search",
                        "description": "Search the web for information",
                        "node_type": "llm_tool_use",
                        "system_prompt": (
                            "Search for {query} and return the top results. "
                            "Use the web_search tool."
                        ),
                        "tools": ["web_search"],
                        "input_keys": ["query"],
                        "output_keys": ["search_results"],
                    },
                    {
                        "id": "summarizer",
                        "name": "Summarize Results",
                        "description": "Summarize the search results",
                        "node_type": "llm_generate",
                        "system_prompt": (
                            "Summarize the following search results "
                            "in 2-3 sentences: {search_results}"
                        ),
                        "tools": [],
                        "input_keys": ["search_results"],
                        "output_keys": ["summary"],
                    },
                ],
                "edges": [
                    {
                        "id": "search-to-summarize",
                        "source": "web-searcher",
                        "target": "summarizer",
                        "condition": "on_success",
                        "condition_expr": None,
                        "priority": 0,
                        "input_mapping": {},
                    }
                ],
                "max_steps": 100,
                "max_retries_per_node": 3,
                "description": "Web research workflow",
                "created_at": datetime.now().isoformat(),
            },
            "goal": {
                "id": "web-researcher",
                "name": "Web Research Agent",
                "description": "Search the web and summarize findings",
                "success_criteria": [
                    {
                        "id": "search-results",
                        "description": "Successfully retrieve search results",
                        "metric": "result_count",
                        "target": ">=3",
                        "weight": 0.5,
                    },
                    {
                        "id": "summary",
                        "description": "Provide a clear summary of the findings",
                        "metric": "summary_quality",
                        "target": "80%",
                        "weight": 0.5,
                    },
                ],
                "constraints": [],
            },
            "required_tools": ["web_search"],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "node_count": 2,
                "edge_count": 1,
            },
        }

        # Write agent.json
        export_path.mkdir(parents=True, exist_ok=True)
        with open(export_path / "agent.json", "w") as f:
            json.dump(agent_data, f, indent=2)

        # Load and register MCP server
        runner = AgentRunner.load(export_path)
        runner.register_mcp_server(
            name="tools",
            transport="stdio",
            command="python",
            args=["-m", "aden_tools.mcp_server", "--stdio"],
            cwd="../tools",
        )

        # Run the agent
        result = await runner.run({"query": "latest AI breakthroughs 2026"})

        print(f"\nAgent completed with result:\n{result}")

        # Cleanup
        runner.cleanup()

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main():
    """Run all examples"""
    print("=" * 60)
    print("MCP Integration Examples")
    print("=" * 60)

    try:
        # Run examples
        await example_1_programmatic_registration()
        # await example_2_http_transport()  # Requires HTTP server running
        # await example_3_config_file()
        # await example_4_custom_agent_with_mcp_tools()

    except Exception as e:
        print(f"\nError running example: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
