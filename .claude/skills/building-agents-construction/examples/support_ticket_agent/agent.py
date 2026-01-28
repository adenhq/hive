import os
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List

from framework.runtime.agent_runtime import create_agent_runtime
from framework.graph.edge import GraphSpec, EdgeSpec
from framework.graph.node import NodeSpec
from framework.graph import Goal, SuccessCriterion
from framework.runtime.execution_stream import EntryPointSpec
from framework.llm.provider import LLMResponse

# --- 1. Defining a Local Mock Provider ---
class MockLLMProvider:
    """A simple mock provider that returns dummy JSON."""
    
    # Synchronous method (no 'async') to match framework expectations
    def complete(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """
        Intercepts the LLM call and returns a fake response immediately.
        """
        last_msg = ""
        if messages and isinstance(messages, list):
            last_msg = messages[-1].get("content", "")
        
        print(f"   [MockLLM] Processing request...")

        
        if "category" in last_msg and "priority" in last_msg:
            # Node 2: Draft Response
            return LLMResponse(
                content=json.dumps({
                    "response_draft": "Subject: Login Issue\n\nDear Customer,\n\nWe noticed you are having trouble logging in. Since this is a High Priority Technical issue, I have escalated your ticket immediately.\n\nBest,\nSupport Team"
                }),
                model="mock-gpt"
            )
        else:
            # Node 1: Analyze Ticket
            return LLMResponse(
                content=json.dumps({
                    "category": "Technical",
                    "priority": "High",
                    "sentiment": "Negative"
                }),
                model="mock-gpt"
            )

# --- 2. Main Agent Class ---
class SupportTicketAgent:
    def __init__(self, mock: bool = False):
        self.mock = mock
        self.runtime = None

    async def initialize(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, "agent.json"), "r") as f:
            data = json.load(f)

        # Build Goal
        goal_data = data["goal"]
        criterion = SuccessCriterion(
            id="success_1",
            description=goal_data["success_criteria"],
            metric="completion_rate", 
            target=1.0
        )
        goal_obj = Goal(
            id=goal_data["goal_id"],
            name=goal_data["name"],
            description=goal_data["description"],
            success_criteria=[criterion]
        )

        # Build Nodes
        node_objects = []
        for n in data["nodes"]:
            node_objects.append(
                NodeSpec(
                    id=n["node_id"],
                    name=n["name"],
                    description=n.get("description", f"Node for {n['name']}"), 
                    node_type=n["node_type"],
                    system_prompt=n.get("system_prompt"),
                    input_keys=n.get("input_keys", []),
                    output_keys=n.get("output_keys", [])
                )
            )

        # Build Edges
        edge_objects = []
        for e in data["edges"]:
            edge_objects.append(
                EdgeSpec(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    condition=e.get("condition", "on_success")
                )
            )

        # Build Graph
        graph_obj = GraphSpec(
            id="support_ticket_graph",
            goal_id=goal_obj.id,
            nodes=node_objects,
            edges=edge_objects,
            entry_node=data["nodes"][0]["node_id"]
        )

        # Entry Point
        entry_point = EntryPointSpec(
            id="start",
            name="Manual Start",
            entry_node=data["nodes"][0]["node_id"],
            trigger_type="manual"
        )

        storage = Path(current_dir) / ".storage"
        storage.mkdir(exist_ok=True)

        # Pass the Mock Provider
        mock_llm = MockLLMProvider()

        self.runtime = create_agent_runtime(
            graph=graph_obj,
            goal=goal_obj,
            storage_path=storage,
            entry_points=[entry_point],
            llm=mock_llm 
        )

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if not self.runtime:
            await self.initialize()
            
        await self.runtime.start()
        
        try:
            # Using 'input_data' as confirmed by the previous error log
            result = await self.runtime.trigger_and_wait(
                entry_point_id="start", 
                input_data=inputs
            )
            return result
        finally:
            await self.runtime.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run in mock mode")
    parser.add_argument("--input", type=str, default='{"ticket_content": "I cannot login to my account"}')
    args = parser.parse_args()

    try:
        inputs = json.loads(args.input)
    except:
        inputs = {"ticket_content": args.input}

    async def main():
        print(f"🚀 Starting Support Ticket Agent...")
        agent = SupportTicketAgent(mock=True)
        
        try:
            result = await agent.run(inputs)
            print("\n Agent Finished!")
            # Use default=str to insure all objects are printable
            print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            import traceback
            traceback.print_exc()

    asyncio.run(main())