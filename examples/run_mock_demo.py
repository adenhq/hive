#!/usr/bin/env python3
"""
Mock Agent Runner Example

This script demonstrates how to run an agent in "Mock Mode" without requiring real API keys.
It handles:
1. Loading an agent with `mock_mode=True`
2. Auto-registering dummy tools to satisfy validation requirements
3. Patching MCP server loading if local environment issues exist

Usage:
    python examples/run_mock_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path so we can import framework if not installed as package
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Add templates directory to path to allow relative imports within agents
templates_dir = project_root / "examples" / "templates"
if str(templates_dir) not in sys.path:
    sys.path.append(str(templates_dir))

try:
    from core.framework.runner import AgentRunner
except ImportError:
    # Try importing directly if package structure is different
    try:
        from framework.runner import AgentRunner
    except ImportError:
        print("Error: Could not import AgentRunner. Make sure you are running from the project root.")
        sys.exit(1)

async def main():
    # Path to the example agent
    agent_path = templates_dir / "tech_news_reporter"
    if not agent_path.exists():
        print(f"Agent path not found: {agent_path}")
        return

    print(f"Loading agent from {agent_path} in MOCK MODE...")

    try:
        # OPTIONAL: Monkeypatch AgentRunner to skip MCP loading
        # This is useful if 'uv' or MCP servers are not set up in the environment
        original_load_mcp = AgentRunner._load_mcp_servers_from_config
        AgentRunner._load_mcp_servers_from_config = lambda self, path: print(f"Skipping MCP load for {path} (Mock Mode)")

        # Load with mock_mode=True
        # We set model to a dummy value "mock/gpt-4" to indicate mocking
        runner = AgentRunner.load(agent_path, mock_mode=True, model="mock/gpt-4")

        # Restore patch (good practice)
        AgentRunner._load_mcp_servers_from_config = original_load_mcp

        # AUTO-REGISTER MOCK TOOLS
        # Real agents expect tools to return actual data. In mock mode, we must provide
        # dummy implementations for any required tools that aren't loaded.
        required_tools = runner.info().required_tools
        print(f"Required tools to mock: {required_tools}")

        for tool_name in required_tools:
            if not runner._tool_registry.has_tool(tool_name):
                print(f"  - Registering mock implementation for: {tool_name}")

                # Create a dummy function that returns a placeholder string
                async def mock_tool(*args, **kwargs):
                    return f"Mock result for {tool_name}"

                # Tool function needs a name attribute
                mock_tool.__name__ = tool_name
                runner.register_tool(tool_name, mock_tool)

        print("\n" + "="*40)
        print(" STARTING MOCK EXECUTION")
        print("="*40)

        input_data = {
            "topic": "The future of AI agents",
            "style": "concise"
        }
        print(f"Input: {input_data}")

        # Run the agent
        # Note: In mock mode, the LLM returns fixed/random responses.
        # Deep loops may trigger the LogicalLoopDetector, which is expected behavior.
        result = await runner.run(input_data)

        print("\n" + "="*40)
        print(" EXECUTION FINISHED")
        print("="*40)

        if result.success:
            print("Status: ✅ Success")
            import json
            print("\nOutput:")
            print(json.dumps(result.output, indent=2, default=str))
        else:
            print(f"Status: ❌ Failed (or stopped by safety limit)")
            print(f"Reason: {result.error}")

    except Exception as e:
        print(f"\nError running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
