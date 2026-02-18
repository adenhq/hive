"""Agent graph construction for Fitness Coach Agent."""

from pathlib import Path

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import AsyncEntryPointSpec, GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    intake_node,
    coach_node,
    meal_checkin_node,
    exercise_reminder_node,
)

# Goal definition
goal = Goal(
    id="fitness-coach",
    name="Personal Fitness Coach",
    description=(
        "Conversational fitness coach that tracks daily calorie intake and burn "
        "via Google Sheets (separate tabs for Meals, Exercises, and Daily Summary), "
        "generates personalized workout plans, and sends scheduled check-ins for "
        "meals and exercise reminders."
    ),
    success_criteria=[
        SuccessCriterion(
            id="calorie-tracking",
            description=(
                "Accurately logs all reported meals and exercises to Google Sheets "
                "with approximate calorie estimates"
            ),
            metric="logging_completeness",
            target=">=95%",
            weight=0.35,
        ),
        SuccessCriterion(
            id="workout-generation",
            description=(
                "Generates personalized workout plans based on user fitness level, "
                "goals, and available equipment"
            ),
            metric="plan_relevance",
            target=">=90%",
            weight=0.30,
        ),
        SuccessCriterion(
            id="proactive-checkins",
            description=(
                "Timer-driven check-ins fire at configured meal times and exercise "
                "intervals, prompting the user naturally"
            ),
            metric="checkin_reliability",
            target=">=95%",
            weight=0.35,
        ),
    ],
    constraints=[
        Constraint(
            id="no-medical-advice",
            description=(
                "Never provide medical diagnoses, prescribe supplements or "
                "medications, or override doctor recommendations"
            ),
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="transparent-estimates",
            description=(
                "Always disclose that calorie estimates are approximate and suggest "
                "verifying with nutrition labels when possible"
            ),
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="non-destructive-sheets",
            description=(
                "Never bulk-delete rows or clear ranges in Google Sheets. "
                "Corrections to individual cells are allowed via update_values."
            ),
            constraint_type="hard",
            category="operational",
        ),
    ],
)

# Node list
nodes = [
    intake_node,
    coach_node,
    meal_checkin_node,
    exercise_reminder_node,
]

# Edge definitions
edges = [
    EdgeSpec(
        id="intake-to-coach",
        source="intake",
        target="coach",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="coach-loop",
        source="coach",
        target="coach",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="meal-checkin-to-coach",
        source="meal-checkin",
        target="coach",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="exercise-reminder-to-coach",
        source="exercise-reminder",
        target="coach",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

# Graph configuration
entry_node = "intake"
entry_points = {"start": "intake"}
async_entry_points = [
    AsyncEntryPointSpec(
        id="meal-timer",
        name="Meal Check-in",
        entry_node="meal-checkin",
        trigger_type="timer",
        trigger_config={"schedule": ["08:00", "12:00", "19:00"]},
        isolation_level="shared",
        max_concurrent=1,
    ),
    AsyncEntryPointSpec(
        id="exercise-timer",
        name="Exercise Reminder",
        entry_node="exercise-reminder",
        trigger_type="timer",
        trigger_config={"interval_minutes": 240},
        isolation_level="shared",
        max_concurrent=1,
    ),
]
pause_nodes = []
terminal_nodes = []
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 50,
    "max_history_tokens": 32000,
}
conversation_mode = "continuous"
identity_prompt = (
    "You are a friendly, knowledgeable personal fitness coach. You help users "
    "track their daily calorie intake and burn via Google Sheets, generate "
    "personalized workout plans, and stay on track with scheduled meal check-ins "
    "and exercise reminders. You are encouraging, concise, and transparent about "
    "the approximate nature of calorie estimates."
)


class FitnessCoachAgent:
    """
    Fitness Coach Agent — conversational fitness tracking with scheduled check-ins.

    Flow:
      [manual] → intake → coach ↺ (self-loop)
      [timer: 08:00, 12:00, 19:00] → meal-checkin → coach
      [timer: every 4h] → exercise-reminder → coach

    Uses AgentRuntime for:
    - Multi-entry-point execution (primary + 2 timer-driven)
    - Session-scoped storage
    - Shared state so timers read user profile set during intake
    - Checkpointing for resume capability
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
        self._graph: GraphSpec | None = None
        self._agent_runtime: AgentRuntime | None = None
        self._tool_registry: ToolRegistry | None = None
        self._storage_path: Path | None = None
        self._saved_profile: dict | None = None

    def _build_graph(self) -> GraphSpec:
        """Build the GraphSpec."""
        return GraphSpec(
            id="fitness-coach-graph",
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
            loop_config=loop_config,
            conversation_mode=conversation_mode,
            identity_prompt=identity_prompt,
            async_entry_points=async_entry_points,
        )

    def _setup(self, mock_mode=False) -> None:
        """Set up the agent runtime with sessions, checkpoints, and logging."""
        from .tools import load_profile

        self._storage_path = Path.home() / ".hive" / "agents" / "fitness_coach"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        # Discover custom tools (save_profile)
        tools_path = Path(__file__).parent / "tools.py"
        if tools_path.exists():
            self._tool_registry.discover_from_module(tools_path)

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )

        tool_executor = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())

        # Check for saved profile — skip intake if we already have one
        saved_profile = load_profile()
        default_entry_node = "coach" if saved_profile else self.entry_node
        self._saved_profile = saved_profile

        self._graph = self._build_graph()

        checkpoint_config = CheckpointConfig(
            enabled=True,
            checkpoint_on_node_start=False,
            checkpoint_on_node_complete=True,
            checkpoint_max_age_days=7,
            async_checkpoint=True,
        )

        # Build entry point specs for AgentRuntime
        entry_point_specs = [
            # Primary entry point — starts at coach if profile exists, intake otherwise
            EntryPointSpec(
                id="default",
                name="Default",
                entry_node=default_entry_node,
                trigger_type="manual",
                isolation_level="shared",
            ),
            # Meal check-in timer (clock-based schedule)
            EntryPointSpec(
                id="meal-timer",
                name="Meal Check-in",
                entry_node="meal-checkin",
                trigger_type="timer",
                trigger_config={"schedule": ["08:00", "12:00", "19:00"]},
                isolation_level="shared",
                max_concurrent=1,
            ),
            # Exercise reminder timer (interval-based)
            EntryPointSpec(
                id="exercise-timer",
                name="Exercise Reminder",
                entry_node="exercise-reminder",
                trigger_type="timer",
                trigger_config={"interval_minutes": 240},
                isolation_level="shared",
                max_concurrent=1,
            ),
        ]

        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=entry_point_specs,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            checkpoint_config=checkpoint_config,
        )

    async def start(self, mock_mode=False) -> None:
        """Set up and start the agent runtime.

        If a saved profile exists, the default entry point skips intake and
        goes straight to coach. The saved user_profile and sheet_id are
        injected as input_data so they appear in shared memory.
        """
        if self._agent_runtime is None:
            self._setup(mock_mode=mock_mode)
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self) -> None:
        """Stop and clean up the agent runtime."""
        if self._agent_runtime is not None and self._agent_runtime.is_running:
            await self._agent_runtime.stop()

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")

        # Inject saved profile into input_data so coach/timers have it
        if self._saved_profile and entry_point == "default":
            input_data = {**self._saved_profile, **input_data}

        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data,
            timeout=timeout,
            session_state=session_state,
        )

    async def run(
        self, context: dict, mock_mode=False, session_state=None
    ) -> ExecutionResult:
        """Run the agent (convenience method for single execution)."""
        await self.start(mock_mode=mock_mode)
        try:
            result = await self.trigger_and_wait(
                "default", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        """Get agent information."""
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {
                "name": self.goal.name,
                "description": self.goal.description,
            },
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "pause_nodes": self.pause_nodes,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
            "async_entry_points": [
                {"id": ep.id, "name": ep.name, "entry_node": ep.entry_node}
                for ep in async_entry_points
            ],
        }

    def validate(self):
        """Validate agent structure."""
        errors = []
        warnings = []

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

        for ep_id, node_id in self.entry_points.items():
            if node_id not in node_ids:
                errors.append(
                    f"Entry point '{ep_id}' references unknown node '{node_id}'"
                )

        # Validate async entry points
        for ep in async_entry_points:
            if ep.entry_node not in node_ids:
                errors.append(
                    f"Async entry point '{ep.id}' references unknown node '{ep.entry_node}'"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Create default instance
default_agent = FitnessCoachAgent()
