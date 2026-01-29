"""
Agent graph construction for Basic Worker Agent (Template).

This agent does nothing by default and is intended purely
as a starting point for new worker agents.
"""

from pathlib import Path

from framework.graph import Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.llm import LiteLLMProvider

from .config import default_config, metadata
from .nodes import noop_node

# Goal (minimal placeholder)
goal = Goal(
    id="noop-goal",
    name="Noop Agent Goal",
    description="Placeholder goal for a template agent.",
    success_criteria=[
        SuccessCriterion(
            id="completed",
            description="Agent completes execution",
            metric="completed",
            target="true",
            weight=1.0,
        )
    ],
    constraints=[
        Constraint(
            id="no-side-effects",
            description="Agent must not perform unintended actions",
            constraint_type="soft",
            category="safety",
        )
    ],
)

# Graph definition
nodes = [noop_node]
edges = []

entry_node = "noop"
entry_points = {"start": "noop"}
pause_nodes = []
terminal_nodes = ["noop"]

# Agent implementation
class BasicWorkerAgent:
    """Minimal runnable worker-agent template."""

    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._runtime: AgentRuntime | None = None

    def _build_entry_points(self) -> list[EntryPointSpec]:
        return [
            EntryPointSpec(
                id="start",
                name="Start",
                entry_node=self.entry_node,
                trigger_type="manual",
                isolation_level="shared",
            )
        ]

    def _create_runtime(self, mock_mode: bool = False) -> AgentRuntime:
        # Local runtime storage (template-safe)
        storage_path = Path(__file__).parent / ".runtime"
        storage_path.mkdir(parents=True, exist_ok=True)

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )

        graph = GraphSpec(
            id="basic-worker-agent-graph",
            goal_id=self.goal.id,
            version="0.1.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
        )

        self._runtime = create_agent_runtime(
            graph=graph,
            goal=self.goal,
            storage_path=storage_path,  # ✅ FIXED
            entry_points=self._build_entry_points(),
            llm=llm,
            tools=[],
            tool_executor=None,
        )

        return self._runtime

    async def run(self, context: dict | None = None, mock_mode: bool = False):
        if self._runtime is None:
            self._create_runtime(mock_mode=mock_mode)

        await self._runtime.start()
        try:
            return await self._runtime.trigger_and_wait(
                "start", context or {}
            )
        finally:
            await self._runtime.stop()

    def validate(self):
        return {"valid": True, "errors": [], "warnings": []}

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "nodes": [n.id for n in self.nodes],
            "entry_node": self.entry_node,
            "terminal_nodes": self.terminal_nodes,
        }

# Default export
default_agent = BasicWorkerAgent()
