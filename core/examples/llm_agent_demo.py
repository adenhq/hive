"""
Simple LLM Agent Example - Core Feature Demo
---------------------------------------------
This demonstrates Hive's core LLM integration feature:
- LLM nodes (not just function nodes)
- Dynamic text generation
- Conditional routing based on LLM responses
- Multi-step reasoning workflows

This example creates a simple story generator agent.
"""

import asyncio
import logging
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try loading from project root first, then current directory
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Loaded .env from {env_path}")
    else:
        load_dotenv()  # Try current directory
except ImportError:
    print("[WARN] python-dotenv not installed, using environment variables directly")
from framework.graph import Goal, NodeSpec, EdgeSpec, GraphSpec, EdgeCondition
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime
from framework.llm.litellm import LiteLLMProvider

async def main():
    print("[*] Hive Core Feature Demo: LLM-Based Agent")
    print("=" * 60)
    
    # Initialize LLM provider using Cerebras API
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        print("[ERROR] CEREBRAS_API_KEY environment variable is not set")
        print("   Please set it with: set CEREBRAS_API_KEY=your-key-here")
        return
    
    llm = LiteLLMProvider(
        model="cerebras/llama-3.3-70b",  # Using Cerebras Llama model
        api_key=api_key,
    )
    print("[OK] LLM Provider initialized: cerebras/llama-3.3-70b")
    
    # Define Goal
    goal = Goal(
        id="story-generator",
        name="Story Generator",
        description="Generate a creative short story based on a given theme",
        success_criteria=[
            {
                "id": "story_created",
                "description": "A creative story has been generated",
                "metric": "custom",
                "target": "any"
            }
        ]
    )
    
    # Node 1: Generate story outline
    outline_node = NodeSpec(
        id="outliner",
        name="Story Outliner",
        description="Creates a story outline from the theme",
        node_type="llm_generate",
        model="cerebras/llama-3.3-70b",  # Using Cerebras - fast!
        system_prompt="You are a creative writer. Generate a 3-point outline for a short story about: {theme}",
        input_keys=["theme"],
        output_keys=["outline"]
    )
    
    # Node 2: Write the story
    writer_node = NodeSpec(
        id="writer",
        name="Story Writer",
        description="Writes the full story from the outline",
        node_type="llm_generate",
        model="cerebras/llama-3.3-70b",  # Using Cerebras
        system_prompt="Based on this outline: {outline}\n\nWrite a creative short story (3-4 paragraphs).",
        input_keys=["outline"],
        output_keys=["story"]
    )
    
    # Node 3: Add a title
    title_node = NodeSpec(
        id="titler",
        name="Title Generator",
        description="Creates an engaging title for the story",
        node_type="llm_generate",
        model="cerebras/llama-3.3-70b",  # Using Cerebras
        system_prompt="Given this story: {story}\n\nCreate a short, catchy title (max 5 words).",
        input_keys=["story"],
        output_keys=["title"]
    )
    
    # Define Edges (workflow connections)
    edge1 = EdgeSpec(
        id="outline-to-writer",
        source="outliner",
        target="writer",
        condition=EdgeCondition.ON_SUCCESS
    )
    
    edge2 = EdgeSpec(
        id="writer-to-title",
        source="writer",
        target="titler",
        condition=EdgeCondition.ON_SUCCESS
    )
    
    # Create the Graph
    graph = GraphSpec(
        id="story-gen-agent",
        goal_id="story-generator",
        entry_node="outliner",
        terminal_nodes=["titler"],
        nodes=[outline_node, writer_node, title_node],
        edges=[edge1, edge2],
    )
    
    # Initialize Runtime & Executor
    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime, llm=llm)
    
    # Execute the Agent
    print("\n[>] Executing story generator agent...")
    print("   Theme: 'A robot learning to paint'")
    print("   This will:")
    print("   1. Create an outline (LLM Node)")
    print("   2. Write the story (LLM Node)")
    print("   3. Generate a title (LLM Node)")
    print("\n" + "=" * 60)
    
    try:
        result = await executor.execute(
            graph=graph,
            goal=goal,
            input_data={"theme": "A robot learning to paint"}
        )
        
        # Display Results
        if result.success:
            print("\n[SUCCESS] Story Generation Complete!")
            print("=" * 60)
            print(f"\n[TITLE] {result.output.get('title', 'Untitled')}")
            print("\n" + "-" * 60)
            print(result.output.get('story', ''))
            print("=" * 60)
            print(f"\n[PATH] Execution: {' -> '.join(result.path)}")
        else:
            print(f"\n[FAILED] {result.error}")
            
    except Exception as e:
        print(f"\n[WARN] Note: This example requires an LLM API key (CEREBRAS_API_KEY)")
        print(f"Error: {e}")
        print("\n[TIP] To run this example:")
        print("   1. Set API key: set CEREBRAS_API_KEY=your-key-here")
        print("   2. Or create a .env file with the key")
        print("\nThe example demonstrates Hive's key features:")
        print("   [x] LLM-based nodes (not just functions)")
        print("   [x] Multi-step workflows")
        print("   [x] Graph-based agent architecture")
        print("   [x] Dynamic text generation")

if __name__ == "__main__":
    # Enable logging to see internal decision flow
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
