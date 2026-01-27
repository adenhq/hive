"""Agent graph construction for SQL Generator."""
from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .nodes import parse_request_node, generate_sql_node
from .config import default_config, metadata


goal = Goal(
    id="generate-sql-from-natural-language",
    name="Generate SQL from Natural Language",
    description="Convert natural language questions into correct SQL queries.",
    success_criteria=[
        SuccessCriterion(
            id="valid-sql",
            description="Generate syntactically correct SQL",
            metric="sql_valid",
            target="true",
            weight=0.5,
        ),
        SuccessCriterion(
            id="matches-intent",
            description="SQL correctly answers the user's question",
            metric="intent_match",
            target="true",
            weight=0.5,
        ),
    ],
    constraints=[
        Constraint(
            id="no-injection",
            description="Never generate SQL injection vulnerable queries",
            constraint_type="security",
            category="safety",
        ),
        Constraint(
            id="standard-sql",
            description="Use standard SQL compatible with major databases",
            constraint_type="functional",
            category="compatibility",
        ),
    ],
)


edges = [
    EdgeSpec(
        id="parse-to-generate",
        source="parse-request",
        target="generate-sql",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]


entry_node = "parse-request"
entry_points = {"start": "parse-request"}
pause_nodes = []
terminal_nodes = ["generate-sql"]

nodes = [parse_request_node, generate_sql_node]


class SQLGeneratorAgent:
    """
    SQL Generator Agent - Converts natural language to SQL queries.
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

        storage_path = Path.home() / ".hive" / "sql_generator_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        tool_registry = ToolRegistry()

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(model=self.config.model)

        self._graph = GraphSpec(
            id="sql-generator-graph",
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


default_agent = SQLGeneratorAgent()
