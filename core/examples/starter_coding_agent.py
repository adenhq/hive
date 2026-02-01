"""Starter Coding Agent (Dev/Test Only)
-------------------------------------
This lightweight example demonstrates running an LLM-backed node locally
without requiring Claude. It will use OpenRouter if `OPENROUTER_API_KEY`
is present, otherwise it falls back to `LiteLLMProvider` (if installed) or
the `MockLLMProvider` for offline development.

Run with:
    PYTHONPATH=core python core/examples/starter_coding_agent.py

This script is intended for development and testing only — it's NOT a
production-ready agent. It helps validate LLM node execution, basic
tool usage plumbing, and graph generation locally.
"""

import asyncio
import os
from pathlib import Path

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime

# LLM providers
from framework.llm import mock as _mock

try:
    from framework.llm.openrouter import OpenRouterProvider
except Exception:
    OpenRouterProvider = None  # type: ignore[assignment]

try:
    from framework.llm.litellm import LiteLLMProvider
except Exception:
    LiteLLMProvider = None  # type: ignore[assignment]


async def main():
    print("🚧 Starter coding agent (dev/test-only) — starting...")

    # Choose provider: OpenRouter > LiteLLM > Mock
    # Set STARTER_USE_MOCK=1 to force mock provider (offline testing)
    provider = None
    use_mock = os.environ.get("STARTER_USE_MOCK") == "1"
    
    if use_mock:
        print("Using MockLLMProvider (STARTER_USE_MOCK=1)")
        provider = _mock.MockLLMProvider()
    else:
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key and OpenRouterProvider is not None:
            print("Using OpenRouter provider (OPENROUTER_API_KEY detected)")
            # OpenRouter requires provider prefix: "openai/gpt-4o-mini", "anthropic/claude-3-haiku", etc.
            default_model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
            provider = OpenRouterProvider(api_key=openrouter_key, model=default_model)
        elif LiteLLMProvider is not None:
            print("Using LiteLLM provider (litellm available). Configure model via OPENROUTER_MODEL env var.")
            provider = LiteLLMProvider(model=os.environ.get("OPENROUTER_MODEL", ""))
        else:
            print("No LLM available — falling back to MockLLMProvider for offline testing")
            provider = _mock.MockLLMProvider()

    # Define a simple goal that asks the LLM to produce a JSON 'solution'
    goal = Goal(
        id="starter-coding",
        name="Starter Coding Agent",
        description="Produce a short development-friendly solution string",
        success_criteria=[
            {
                "id": "solution_present",
                "description": "Solution key present in output",
                "metric": "custom",
                "target": "any",
            }
        ],
    )

    # LLM Node: expect JSON with key 'solution'
    node = NodeSpec(
        id="coder",
        name="Coder",
        description="Generates a short solution description",
        node_type="llm_generate",
        input_keys=["task"],
        output_keys=["solution"],
        system_prompt=(
            "You are a concise coding assistant. Given a 'task' input, respond with a JSON object "
            "containing a single key 'solution' with a short, actionable answer. Only output valid JSON."
        ),
        max_retries=1,
    )

    # Graph with single node
    graph = GraphSpec(
        id="starter-graph",
        goal_id=goal.id,
        entry_node=node.id,
        terminal_nodes=[node.id],
        nodes=[node],
        edges=[],
    )

    # Initialize runtime and executor
    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime, llm=provider)

    # Execute with a small test task
    print("▶ Executing starter agent with sample task...")
    result = await executor.execute(graph=graph, goal=goal, input_data={"task": "Write a one-line Python function that returns the sum of two numbers."})

    if result.success:
        print("\n✅ Starter agent completed successfully")
        print(f"Output: {result.output}")
    else:
        print("\n❌ Starter agent failed")
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
