"""Agent graph construction for Invoice Analyzer."""
from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .nodes import extract_items_node, analyze_charges_node
from .config import default_config, metadata


goal = Goal(
    id="detect-hidden-charges",
    name="Detect Hidden Invoice Charges",
    description="Analyze invoices to identify hidden fees, suspicious charges, and billing irregularities.",
    success_criteria=[
        SuccessCriterion(
            id="items-extracted",
            description="Successfully extract all line items from invoice",
            metric="extraction_complete",
            target="true",
            weight=0.4,
        ),
        SuccessCriterion(
            id="analysis-complete",
            description="Provide analysis of potential hidden charges",
            metric="analysis_present",
            target="true",
            weight=0.6,
        ),
    ],
    constraints=[
        Constraint(
            id="offline-operation",
            description="Must work without external API calls",
            constraint_type="functional",
            category="availability",
        ),
        Constraint(
            id="consumer-protection",
            description="Err on the side of flagging suspicious charges",
            constraint_type="quality",
            category="accuracy",
        ),
    ],
)


edges = [
    EdgeSpec(
        id="extract-to-analyze",
        source="extract-items",
        target="analyze-charges",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]


entry_node = "extract-items"
entry_points = {"start": "extract-items"}
pause_nodes = []
terminal_nodes = ["analyze-charges"]

nodes = [extract_items_node, analyze_charges_node]


class InvoiceAnalyzerAgent:
    """
    Invoice Analyzer Agent - Detects hidden charges and suspicious fees.

    Works offline with Ollama - no API keys needed.
    """

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
        self._graph: GraphSpec | None = None

    def _build_entry_point_specs(self) -> list[EntryPointSpec]:
        specs = []
        for ep_id, node_id in self.entry_points.items():
            specs.append(EntryPointSpec(
                id=ep_id,
                name="Start" if ep_id == "start" else ep_id.replace("-", " ").title(),
                entry_node=node_id,
                trigger_type="manual",
                isolation_level="shared",
            ))
        return specs

    def _create_runtime(self, mock_mode=False) -> AgentRuntime:
        from pathlib import Path

        storage_path = Path.home() / ".hive" / "invoice_analyzer_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        tool_registry = ToolRegistry()

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(model=self.config.model)

        self._graph = GraphSpec(
            id="invoice-analyzer-graph",
            goal_id=self.goal.id,
            version="1.0.0",
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
            graph=self._graph,
            goal=self.goal,
            storage_path=storage_path,
            entry_points=self._build_entry_point_specs(),
            llm=llm,
            tools=[],
            tool_executor=tool_registry.get_executor(),
        )

        return self._runtime

    async def start(self, mock_mode=False) -> None:
        if self._runtime is None:
            self._create_runtime(mock_mode=mock_mode)
        await self._runtime.start()

    async def stop(self) -> None:
        if self._runtime is not None:
            await self._runtime.stop()

    async def run(self, context: dict, mock_mode=False) -> ExecutionResult:
        await self.start(mock_mode=mock_mode)
        try:
            result = await self._runtime.trigger_and_wait("start", context)
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {"name": self.goal.name, "description": self.goal.description},
            "nodes": [n.id for n in self.nodes],
            "edges": [f"{e.source} -> {e.target}" for e in self.edges],
            "entry_node": self.entry_node,
            "terminal_nodes": self.terminal_nodes,
        }

    def validate(self):
        errors = []
        node_ids = {node.id for node in self.nodes}

        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target '{edge.target}' not found")

        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")

        for terminal in self.terminal_nodes:
            if terminal not in node_ids:
                errors.append(f"Terminal node '{terminal}' not found")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": []}


default_agent = InvoiceAnalyzerAgent()
