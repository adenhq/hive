"""Agent graph construction for Blog Writer Agent."""

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    analyze_topic_node,
    create_outline_node,
    fetch_sources_node,
    quality_check_node,
    research_topic_node,
    save_blog_node,
    seo_optimize_node,
    write_draft_node,
)

# Goal definition
goal = Goal(
    id="seo-blog-writer",
    name="SEO Blog Writer",
    description="Research any topic and produce a well-structured, SEO-optimized blog post with citations, saved as a polished markdown file.",
    success_criteria=[
        SuccessCriterion(
            id="word-count",
            description="Blog post is 1500-3000 words",
            metric="word_count",
            target="1500-3000",
            weight=0.15,
        ),
        SuccessCriterion(
            id="citations",
            description="All factual claims cite their sources",
            metric="citation_coverage",
            target="100%",
            weight=0.20,
        ),
        SuccessCriterion(
            id="seo-optimization",
            description="Post includes meta description, keyword-optimized headers, and tags",
            metric="seo_score",
            target="85%",
            weight=0.20,
        ),
        SuccessCriterion(
            id="readability",
            description="Clear, engaging prose with good flow and structure",
            metric="readability_score",
            target="85%",
            weight=0.20,
        ),
        SuccessCriterion(
            id="accuracy",
            description="All information accurately reflects source material",
            metric="accuracy_score",
            target="95%",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="no-hallucination",
            description="Only include information found in researched sources",
            constraint_type="hard",
            category="accuracy",
        ),
        Constraint(
            id="seo-compliant",
            description="Follow SEO best practices for meta description, headers, and keyword usage",
            constraint_type="soft",
            category="quality",
        ),
        Constraint(
            id="original-content",
            description="Content must be original; no plagiarized text from sources",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

# Node list
nodes = [
    analyze_topic_node,
    research_topic_node,
    fetch_sources_node,
    create_outline_node,
    write_draft_node,
    seo_optimize_node,
    quality_check_node,
    save_blog_node,
]

# Edge definitions
edges = [
    EdgeSpec(
        id="analyze-to-research",
        source="analyze-topic",
        target="research-topic",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="research-to-fetch",
        source="research-topic",
        target="fetch-sources",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="fetch-to-outline",
        source="fetch-sources",
        target="create-outline",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="outline-to-write",
        source="create-outline",
        target="write-draft",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="write-to-seo",
        source="write-draft",
        target="seo-optimize",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="seo-to-quality",
        source="seo-optimize",
        target="quality-check",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="quality-to-save",
        source="quality-check",
        target="save-blog",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

# Graph configuration
entry_node = "analyze-topic"
entry_points = {"start": "analyze-topic"}
pause_nodes = []
terminal_nodes = ["save-blog"]


class BlogWriterAgent:
    """
    Blog Writer Agent - SEO-optimized blog post generation.

    Uses AgentRuntime for multi-entrypoint support with HITL pause/resume.
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
        """Convert entry_points dict to EntryPointSpec list."""
        specs = []
        for ep_id, node_id in self.entry_points.items():
            if ep_id == "start":
                trigger_type = "manual"
                name = "Start"
            elif "_resume" in ep_id:
                trigger_type = "resume"
                name = f"Resume from {ep_id.replace('_resume', '')}"
            else:
                trigger_type = "manual"
                name = ep_id.replace("-", " ").title()

            specs.append(
                EntryPointSpec(
                    id=ep_id,
                    name=name,
                    entry_node=node_id,
                    trigger_type=trigger_type,
                    isolation_level="shared",
                )
            )
        return specs

    def _create_runtime(self, mock_mode=False) -> AgentRuntime:
        """Create AgentRuntime instance."""
        import json
        from pathlib import Path

        # Persistent storage in ~/.hive for telemetry and run history
        storage_path = Path.home() / ".hive" / "blog_writer_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        tool_registry = ToolRegistry()

        # Load MCP servers (always load, needed for tool validation)
        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            tool_registry.load_mcp_config(mcp_config_path)

        llm = None
        if not mock_mode:
            # LiteLLMProvider uses environment variables for API keys
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )

        self._graph = GraphSpec(
            id="blog-writer-agent-graph",
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

        # Create AgentRuntime with all entry points
        self._runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=storage_path,
            entry_points=self._build_entry_point_specs(),
            llm=llm,
            tools=list(tool_registry.get_tools().values()),
            tool_executor=tool_registry.get_executor(),
        )

        return self._runtime

    async def start(self, mock_mode=False) -> None:
        """Start the agent runtime."""
        if self._runtime is None:
            self._create_runtime(mock_mode=mock_mode)
        await self._runtime.start()

    async def stop(self) -> None:
        """Stop the agent runtime."""
        if self._runtime is not None:
            await self._runtime.stop()

    async def trigger(
        self,
        entry_point: str,
        input_data: dict,
        correlation_id: str | None = None,
        session_state: dict | None = None,
    ) -> str:
        """
        Trigger execution at a specific entry point (non-blocking).

        Args:
            entry_point: Entry point ID (e.g., "start", "pause-node_resume")
            input_data: Input data for the execution
            correlation_id: Optional ID to correlate related executions
            session_state: Optional session state to resume from (with paused_at, memory)

        Returns:
            Execution ID for tracking
        """
        if self._runtime is None or not self._runtime.is_running:
            raise RuntimeError("Agent runtime not started. Call start() first.")
        return await self._runtime.trigger(
            entry_point, input_data, correlation_id, session_state=session_state
        )

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        """
        Trigger execution and wait for completion.

        Args:
            entry_point: Entry point ID
            input_data: Input data for the execution
            timeout: Maximum time to wait (seconds)
            session_state: Optional session state to resume from (with paused_at, memory)

        Returns:
            ExecutionResult or None if timeout
        """
        if self._runtime is None or not self._runtime.is_running:
            raise RuntimeError("Agent runtime not started. Call start() first.")
        return await self._runtime.trigger_and_wait(
            entry_point, input_data, timeout, session_state=session_state
        )

    async def run(
        self, context: dict, mock_mode=False, session_state=None
    ) -> ExecutionResult:
        """
        Run the agent (convenience method for simple single execution).

        For more control, use start() + trigger_and_wait() + stop().
        """
        await self.start(mock_mode=mock_mode)
        try:
            # Determine entry point based on session_state
            if session_state and "paused_at" in session_state:
                paused_node = session_state["paused_at"]
                resume_key = f"{paused_node}_resume"
                if resume_key in self.entry_points:
                    entry_point = resume_key
                else:
                    entry_point = "start"
            else:
                entry_point = "start"

            result = await self.trigger_and_wait(
                entry_point, context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    async def get_goal_progress(self) -> dict:
        """Get goal progress across all executions."""
        if self._runtime is None:
            raise RuntimeError("Agent runtime not started")
        return await self._runtime.get_goal_progress()

    def get_stats(self) -> dict:
        """Get runtime statistics."""
        if self._runtime is None:
            return {"running": False}
        return self._runtime.get_stats()

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
            "multi_entrypoint": True,
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

        for pause in self.pause_nodes:
            if pause not in node_ids:
                errors.append(f"Pause node '{pause}' not found")

        # Validate entry points
        for ep_id, node_id in self.entry_points.items():
            if node_id not in node_ids:
                errors.append(
                    f"Entry point '{ep_id}' references unknown node '{node_id}'"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Create default instance
default_agent = BlogWriterAgent()
