"""
Agent graph construction for Research & Summarization Agent
"""

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata
from .nodes import intake_node, research_node, compile_report_node


# GOAL DEFINITION

goal = Goal(
    id="research-summarizer",
    name="Research & Summarization Agent",
    description=(
        "Research any user-provided topic from the web and generate a clear, "
        "structured summary with key insights and references."
    ),
    success_criteria=[
        SuccessCriterion(
            id="sc-relevant-info",
            description="Finds relevant information about the given topic",
            metric="relevant_sources",
            target=">=3",
            weight=0.3,
        ),
        SuccessCriterion(
            id="sc-summary-quality",
            description="Produces a clear structured summary with key insights",
            metric="summary_quality",
            target="true",
            weight=0.3,
        ),
        SuccessCriterion(
            id="sc-source-attribution",
            description="Includes sources or references",
            metric="sources_included",
            target="true",
            weight=0.2,
        ),
        SuccessCriterion(
            id="sc-delivery",
            description="Delivers final structured response to user",
            metric="delivered",
            target="true",
            weight=0.2,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-fabrication",
            description="Do not fabricate facts or sources",
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="c-clear-format",
            description="Always produce structured readable output",
            constraint_type="soft",
            category="quality",
        ),
    ],
)


# NODES and EDGES

nodes = [intake_node, research_node, compile_report_node]

edges = [
    EdgeSpec(
        id="intake-to-research",
        source="intake",
        target="research",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="research-to-compile",
        source="research",
        target="compile-report",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = ["compile-report"]


# AGENT CLASS

class ResearchSummarizerAgent:

    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="research-summarizer-graph",
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
            loop_config={
                "max_iterations": 40,
                "max_tool_calls_per_turn": 8,
                "max_history_tokens": 24000,
            },
        )

    def _setup(self) -> GraphExecutor:
        from pathlib import Path

        storage_path = Path.home() / ".hive" / "research_summarizer_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()

        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        tool_executor = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())

        self._graph = self._build_graph()
        runtime = Runtime(storage_path)

        self._executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            event_bus=self._event_bus,
            storage_path=storage_path,
            loop_config=self._graph.loop_config,
        )

        return self._executor

    async def start(self) -> None:
        if self._executor is None:
            self._setup()

    async def stop(self) -> None:
        self._executor = None
        self._event_bus = None

    async def run(self, context: dict, session_state=None) -> ExecutionResult:
        await self.start()
        try:
            result = await self._executor.execute(
                graph=self._graph,
                goal=self.goal,
                input_data=context,
                session_state=session_state,
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()


# default instance required by framework
default_agent = ResearchSummarizerAgent()

# REQUIRED EXPORTS
goal = goal
nodes = nodes
edges = edges
