
"""Agent graph construction for GTM Marketing Agent."""

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata
from .nodes import (
    intake_node,
    analyze_node,
    draft_node,
)

# Goal definition
goal = Goal(
    id="marketing-analysis",
    name="GTM Marketing Agent",
    description=(
        "Analyze a competitor's messaging and draft strategic "
        "marketing content (LinkedIn, Ads, Email) to counter them."
    ),
    success_criteria=[
        SuccessCriterion(
            id="sc-identify-competitor",
            description="Correctly identifies the competitor and their main value proposition",
            metric="competitor_analyzed",
            target="true",
            weight=0.3,
        ),
        SuccessCriterion(
            id="sc-draft-content",
            description="Generates 3 distinct marketing drafts exploiting gaps",
            metric="drafts_created",
            target=">=3",
            weight=0.4,
        ),
        SuccessCriterion(
            id="sc-user-engagement",
            description="Engages user professionally and waits for input",
            metric="user_satisfied",
            target="true",
            weight=0.3,
        ),
    ],
    constraints=[
        Constraint(
            id="c-accurate-info",
            description="Never fabricate competitor claims; verify with scrape.",
            constraint_type="hard",
            category="accuracy",
        ),
    ],
)

# Node list
nodes = [
    intake_node,
    analyze_node,
    draft_node,
]

# Edge definitions
edges = [
    EdgeSpec(
        id="intake-to-analyze",
        source="intake",
        target="analyze",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="analyze-to-draft",
        source="analyze",
        target="draft",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

# Graph configuration
entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = ["intake"]  # Intake pauses for user input
terminal_nodes = ["draft"]


class MarketingAgent:
    """
    GTM Marketing Agent — 3-node pipeline.
    Flow: intake -> analyze -> draft
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
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        """Build the GraphSpec."""
        return GraphSpec(
            id="marketing-agent-graph",
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
                "max_iterations": 30,
                "max_tool_calls_per_turn": 5,
                "max_history_tokens": 16000,
            },
        )

    def _setup(self) -> GraphExecutor:
        """Set up the executor with all components."""
        from pathlib import Path

        storage_path = Path.home() / ".hive" / "marketing_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()
        
        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()
        
        # Define and register local tools for the agent
        # (The actual implementation would normally import from a shared library,
        # but for this template we define simple wrappers or mocks to ensure it runs)

        def web_scrape(url: str) -> dict:
            """
            Scrape a website.
            Args:
                url: The URL to scrape.
            """
            # In a real app, this would call the robust scraper.
            # For this template demo, we'll return a mock response if libraries aren't found,
            # or try to use a simple requests fetch.
            return {
                "url": url,
                "content": f"Scraped content from {url}. (This is a placeholder for the actual scraper tool)",
                "title": "Competitor Page"
            }

        def web_search(query: str) -> dict:
            """
            Search the web.
            Args:
                query: The query string.
            """
            return {
                "results": [
                    {"title": f"Result for {query}", "url": "https://example.com", "snippet": "A search result snippet."}
                ]
            }

        self._tool_registry.register_function(web_scrape)
        self._tool_registry.register_function(web_search)
        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        from framework.llm import LiteLLMProvider
        from framework.llm.mock import MockLLMProvider

        if self.config.model == "mock":
            llm = MockLLMProvider(model="mock-model")
        else:
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
        """Set up the agent (initialize executor and tools)."""
        if self._executor is None:
            self._setup()

    async def stop(self) -> None:
        """Clean up resources."""
        self._executor = None
        self._event_bus = None

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
        if self._executor is None:
            raise RuntimeError("Agent not started. Call start() first.")
        if self._graph is None:
            raise RuntimeError("Graph not built. Call start() first.")

        return await self._executor.execute(
            graph=self._graph,
            goal=self.goal,
            input_data=input_data,
            session_state=session_state,
        )

    async def run(self, context: dict, session_state=None) -> ExecutionResult:
        """Run the agent (convenience method for single execution)."""
        await self.start()
        try:
            result = await self.trigger_and_wait(
                "start", context, session_state=session_state
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
        }

# Create default instance
default_agent = MarketingAgent()
