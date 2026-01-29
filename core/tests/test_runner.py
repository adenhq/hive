"""Tests for AgentRunner and load_agent_export.

Run with:
    cd core
    python -m pytest tests/test_runner.py -v
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from framework.graph import Goal
from framework.graph.edge import (
    AsyncEntryPointSpec,
    EdgeCondition,
    EdgeSpec,
    GraphSpec,
)
from framework.graph.executor import ExecutionResult
from framework.graph.goal import Constraint, SuccessCriterion
from framework.graph.node import NodeSpec
from framework.llm.provider import LLMResponse, Tool
from framework.runner.runner import AgentInfo, AgentRunner, ValidationResult, load_agent_export


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _sample_export_dict(
    *,
    with_async_entry_points: bool = False,
    with_tools: bool = False,
) -> dict:
    """Return a minimal agent export dict."""
    nodes = [
        {
            "id": "start",
            "name": "Start Node",
            "description": "Entry node",
            "node_type": "llm_generate",
            "input_keys": ["query"],
            "output_keys": ["result"],
        },
        {
            "id": "end",
            "name": "End Node",
            "description": "Terminal node",
            "node_type": "llm_generate",
            "input_keys": ["result"],
            "output_keys": ["answer"],
        },
    ]

    if with_tools:
        nodes[0]["tools"] = ["search_tool", "calc_tool"]

    export = {
        "graph": {
            "id": "test-graph",
            "goal_id": "test-goal",
            "version": "1.0.0",
            "entry_node": "start",
            "terminal_nodes": ["end"],
            "nodes": nodes,
            "edges": [
                {
                    "id": "e1",
                    "source": "start",
                    "target": "end",
                    "condition": "on_success",
                    "priority": 1,
                },
            ],
            "description": "A test agent for searching and calculating",
        },
        "goal": {
            "id": "test-goal",
            "name": "Test Goal",
            "description": "Perform test operations accurately",
            "success_criteria": [
                {
                    "id": "sc1",
                    "description": "Output is correct",
                    "metric": "output_equals",
                    "target": "expected",
                    "weight": 1.0,
                },
            ],
            "constraints": [
                {
                    "id": "c1",
                    "description": "Must not crash",
                    "constraint_type": "hard",
                    "category": "safety",
                },
            ],
        },
    }

    if with_async_entry_points:
        export["graph"]["async_entry_points"] = [
            {
                "id": "webhook",
                "name": "Webhook Handler",
                "entry_node": "start",
                "trigger_type": "webhook",
                "isolation_level": "shared",
                "priority": 1,
                "max_concurrent": 5,
            },
        ]

    return export


def _write_agent_dir(tmp_path: Path, export: dict | None = None) -> Path:
    """Write agent.json to a temp directory and return its path."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_json = agent_dir / "agent.json"
    agent_json.write_text(json.dumps(export or _sample_export_dict()))
    return agent_dir


# ===========================================================================
# TestLoadAgentExport
# ===========================================================================

class TestLoadAgentExport:
    """Tests for the load_agent_export() function."""

    def test_parse_valid_json_string(self):
        """Parse a valid JSON string into GraphSpec and Goal."""
        data = json.dumps(_sample_export_dict())
        graph, goal = load_agent_export(data)

        assert isinstance(graph, GraphSpec)
        assert isinstance(goal, Goal)
        assert graph.id == "test-graph"
        assert goal.name == "Test Goal"

    def test_parse_dict_input(self):
        """Accept a dict (not just JSON string)."""
        graph, goal = load_agent_export(_sample_export_dict())

        assert graph.entry_node == "start"
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_missing_graph_key(self):
        """Handle missing 'graph' key gracefully by defaulting."""
        graph, goal = load_agent_export({"goal": {"id": "g1", "name": "G"}})

        assert graph.id == "agent-graph"
        assert len(graph.nodes) == 0

    def test_missing_goal_key(self):
        """Handle missing 'goal' key gracefully by defaulting."""
        data = _sample_export_dict()
        del data["goal"]
        graph, goal = load_agent_export(data)

        assert goal.id == ""
        assert goal.name == ""
        assert len(goal.success_criteria) == 0

    def test_edge_condition_mapping(self):
        """Map all five edge condition strings correctly."""
        conditions = ["always", "on_success", "on_failure", "conditional", "llm_decide"]
        expected = [
            EdgeCondition.ALWAYS,
            EdgeCondition.ON_SUCCESS,
            EdgeCondition.ON_FAILURE,
            EdgeCondition.CONDITIONAL,
            EdgeCondition.LLM_DECIDE,
        ]
        data = _sample_export_dict()
        edges = []
        for i, cond in enumerate(conditions):
            edges.append({
                "id": f"e{i}",
                "source": "start",
                "target": "end",
                "condition": cond,
            })
        data["graph"]["edges"] = edges

        graph, _ = load_agent_export(data)

        for edge, exp in zip(graph.edges, expected):
            assert edge.condition == exp

    def test_unknown_condition_defaults_to_on_success(self):
        """Unknown condition strings default to ON_SUCCESS."""
        data = _sample_export_dict()
        data["graph"]["edges"][0]["condition"] = "unknown_condition"
        graph, _ = load_agent_export(data)

        assert graph.edges[0].condition == EdgeCondition.ON_SUCCESS

    def test_async_entry_points_parsed(self):
        """Build AsyncEntryPointSpec objects from export data."""
        data = _sample_export_dict(with_async_entry_points=True)
        graph, _ = load_agent_export(data)

        assert len(graph.async_entry_points) == 1
        ep = graph.async_entry_points[0]
        assert ep.id == "webhook"
        assert ep.entry_node == "start"
        assert ep.trigger_type == "webhook"
        assert ep.max_concurrent == 5

    def test_empty_nodes_and_edges(self):
        """Handle export with no nodes or edges."""
        data = {"graph": {"nodes": [], "edges": []}, "goal": {}}
        graph, _ = load_agent_export(data)

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_invalid_json_string_raises(self):
        """Raise json.JSONDecodeError on invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            load_agent_export("{invalid json")


# ===========================================================================
# TestAgentRunnerLoad
# ===========================================================================

class TestAgentRunnerLoad:
    """Tests for AgentRunner.load() classmethod."""

    def test_load_from_valid_directory(self, tmp_path):
        """Load agent from a directory containing agent.json."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        assert runner.graph.id == "test-graph"
        assert runner.goal.name == "Test Goal"

    def test_load_raises_for_missing_directory(self, tmp_path):
        """Raise FileNotFoundError when the directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            AgentRunner.load(tmp_path / "nonexistent")

    def test_load_raises_for_missing_agent_json(self, tmp_path):
        """Raise FileNotFoundError when agent.json is absent."""
        empty_dir = tmp_path / "empty-agent"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="agent.json not found"):
            AgentRunner.load(empty_dir)

    def test_load_with_mock_mode(self, tmp_path):
        """mock_mode flag is stored on the runner."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner.mock_mode is True

    def test_load_with_custom_storage_path(self, tmp_path):
        """Custom storage_path is used instead of default."""
        agent_dir = _write_agent_dir(tmp_path)
        storage = tmp_path / "custom-storage"
        storage.mkdir()
        runner = AgentRunner.load(agent_dir, storage_path=storage)

        assert runner._storage_path == storage

    def test_load_with_custom_model(self, tmp_path):
        """Custom model parameter is stored."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, model="gpt-4o")
        assert runner.model == "gpt-4o"


# ===========================================================================
# TestAgentRunnerInfo
# ===========================================================================

class TestAgentRunnerInfo:
    """Tests for AgentRunner.info()."""

    def test_info_returns_correct_fields(self, tmp_path):
        """info() returns AgentInfo with correct metadata."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        info = runner.info()

        assert isinstance(info, AgentInfo)
        assert info.name == "test-graph"
        assert info.goal_name == "Test Goal"
        assert info.node_count == 2
        assert info.edge_count == 1
        assert info.entry_node == "start"
        assert "end" in info.terminal_nodes

    def test_info_with_multi_entry_point(self, tmp_path):
        """info() includes async_entry_points for multi-entry agents."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        info = runner.info()

        assert info.is_multi_entry_point is True
        assert len(info.async_entry_points) == 1
        assert info.async_entry_points[0]["id"] == "webhook"

    def test_info_with_empty_graph(self, tmp_path):
        """info() handles agent with no nodes."""
        export = _sample_export_dict()
        export["graph"]["nodes"] = []
        export["graph"]["edges"] = []
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        info = runner.info()

        assert info.node_count == 0
        assert info.edge_count == 0

    def test_info_includes_required_tools(self, tmp_path):
        """info() lists tools required by nodes."""
        export = _sample_export_dict(with_tools=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        info = runner.info()

        assert "calc_tool" in info.required_tools
        assert "search_tool" in info.required_tools


# ===========================================================================
# TestAgentRunnerValidation
# ===========================================================================

class TestAgentRunnerValidation:
    """Tests for AgentRunner.validate()."""

    def test_valid_agent(self, tmp_path):
        """validate() returns valid=True for a well-formed agent."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        result = runner.validate()

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_flags_missing_required_tools(self, tmp_path):
        """validate() warns about required tools that aren't registered."""
        export = _sample_export_dict(with_tools=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        result = runner.validate()

        assert len(result.missing_tools) > 0
        assert "search_tool" in result.missing_tools
        assert any("Missing tool" in w for w in result.warnings)

    def test_warns_no_success_criteria(self, tmp_path):
        """validate() warns when goal has no success criteria."""
        export = _sample_export_dict()
        export["goal"]["success_criteria"] = []
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        result = runner.validate()

        assert any("success criteria" in w.lower() for w in result.warnings)

    def test_validation_result_dataclass(self):
        """ValidationResult fields have correct defaults."""
        result = ValidationResult(valid=True)
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_tools == []
        assert result.missing_credentials == []

    def test_flags_missing_credentials_without_aden_tools(self, tmp_path):
        """validate() falls back to direct API key check when aden_tools is not installed."""
        export = _sample_export_dict()
        export["graph"]["nodes"][0]["node_type"] = "llm_generate"
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, model="gpt-4o")

        with patch.dict(os.environ, {}, clear=True):
            result = runner.validate()

        assert "OPENAI_API_KEY" in result.missing_credentials


# ===========================================================================
# TestAgentRunnerToolRegistration
# ===========================================================================

class TestAgentRunnerToolRegistration:
    """Tests for tool registration methods."""

    def test_register_tool_with_function(self, tmp_path):
        """register_tool() with a callable function."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        def my_tool(x: int) -> str:
            return str(x)

        runner.register_tool("my_tool", my_tool)
        assert runner._tool_registry.has_tool("my_tool")

    def test_register_tool_with_tool_object_and_executor(self, tmp_path):
        """register_tool() with a Tool object requires an executor."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        tool = Tool(name="t1", description="A tool", parameters={"properties": {}})
        executor = Mock()
        runner.register_tool("t1", tool, executor=executor)

        assert runner._tool_registry.has_tool("t1")

    def test_register_tool_object_without_executor_raises(self, tmp_path):
        """register_tool() raises ValueError when Tool has no executor."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        tool = Tool(name="t1", description="A tool")
        with pytest.raises(ValueError, match="executor required"):
            runner.register_tool("t1", tool)

    def test_register_tools_from_module(self, tmp_path):
        """register_tools_from_module() delegates to ToolRegistry."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with patch.object(runner._tool_registry, "discover_from_module", return_value=3) as mock_disc:
            count = runner.register_tools_from_module(Path("/fake/tools.py"))
            mock_disc.assert_called_once_with(Path("/fake/tools.py"))
            assert count == 3

    def test_register_mcp_server(self, tmp_path):
        """register_mcp_server() delegates to ToolRegistry."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with patch.object(runner._tool_registry, "register_mcp_server", return_value=5) as mock_reg:
            count = runner.register_mcp_server(
                name="tools-server", transport="stdio", command="python"
            )
            mock_reg.assert_called_once()
            assert count == 5


# ===========================================================================
# TestAgentRunnerRun
# ===========================================================================

class TestAgentRunnerRun:
    """Tests for AgentRunner.run() and execution paths."""

    @pytest.mark.asyncio
    async def test_run_single_entry_calls_executor(self, tmp_path):
        """run() uses GraphExecutor for single-entry agents."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        expected = ExecutionResult(success=True, output={"answer": "42"})
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=expected)
        runner._executor = mock_executor

        result = await runner.run({"query": "test"})

        assert result.success is True
        mock_executor.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_multi_entry_calls_agent_runtime(self, tmp_path):
        """run() uses AgentRuntime for multi-entry-point agents."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        expected = ExecutionResult(success=True, output={"result": "ok"})
        mock_runtime = MagicMock()
        mock_runtime.is_running = True
        mock_runtime.get_entry_points.return_value = [MagicMock(id="webhook")]
        mock_runtime.trigger_and_wait = AsyncMock(return_value=expected)
        runner._agent_runtime = mock_runtime

        result = await runner.run({"data": "test"})

        assert result.success is True
        mock_runtime.trigger_and_wait.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_defaults_input_data_to_empty_dict(self, tmp_path):
        """run() with None input_data passes empty dict."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=ExecutionResult(success=True))
        runner._executor = mock_executor

        await runner.run(None)

        call_kwargs = mock_executor.execute.call_args[1]
        assert call_kwargs["input_data"] == {}

    @pytest.mark.asyncio
    async def test_run_calls_setup_lazily(self, tmp_path):
        """run() calls _setup() on first invocation if executor is None."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with patch.object(runner, "_setup") as mock_setup:
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(return_value=ExecutionResult(success=True))

            def setup_side_effect():
                runner._executor = mock_executor

            mock_setup.side_effect = setup_side_effect

            await runner.run({"x": 1})
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_multi_entry_auto_starts_runtime(self, tmp_path):
        """run() starts AgentRuntime if it's not already running."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_runtime = MagicMock()
        mock_runtime.is_running = False
        mock_runtime.start = AsyncMock()
        mock_runtime.get_entry_points.return_value = [MagicMock(id="webhook")]
        mock_runtime.trigger_and_wait = AsyncMock(
            return_value=ExecutionResult(success=True)
        )
        runner._agent_runtime = mock_runtime

        await runner.run({})
        mock_runtime.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_multi_entry_selects_default_entry_point(self, tmp_path):
        """run() selects first entry point when none specified."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_ep = MagicMock()
        mock_ep.id = "webhook"
        mock_runtime = MagicMock()
        mock_runtime.is_running = True
        mock_runtime.get_entry_points.return_value = [mock_ep]
        mock_runtime.trigger_and_wait = AsyncMock(
            return_value=ExecutionResult(success=True)
        )
        runner._agent_runtime = mock_runtime

        await runner.run({})
        call_kwargs = mock_runtime.trigger_and_wait.call_args[1]
        assert call_kwargs["entry_point_id"] == "webhook"

    @pytest.mark.asyncio
    async def test_run_returns_error_on_none_result(self, tmp_path):
        """run() returns error ExecutionResult when trigger_and_wait returns None."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_runtime = MagicMock()
        mock_runtime.is_running = True
        mock_runtime.get_entry_points.return_value = [MagicMock(id="webhook")]
        mock_runtime.trigger_and_wait = AsyncMock(return_value=None)
        runner._agent_runtime = mock_runtime

        result = await runner.run({})
        assert result.success is False
        assert "timed out" in result.error.lower() or "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_passes_session_state(self, tmp_path):
        """run() forwards session_state to executor."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=ExecutionResult(success=True))
        runner._executor = mock_executor

        await runner.run({"q": "hi"}, session_state={"paused_at": "node2"})
        call_kwargs = mock_executor.execute.call_args[1]
        assert call_kwargs["session_state"] == {"paused_at": "node2"}


# ===========================================================================
# TestAgentRunnerCapability
# ===========================================================================

class TestAgentRunnerCapability:
    """Tests for can_handle() and _keyword_capability_check()."""

    @pytest.mark.asyncio
    async def test_can_handle_with_llm(self, tmp_path):
        """can_handle() uses LLM to evaluate capability."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = LLMResponse(
            content='{"level": "can_handle", "confidence": 0.9, "reasoning": "good match"}',
            model="test",
        )
        runner._llm = mock_llm

        result = await runner.can_handle({"task": "search for info"})

        from framework.runner.protocol import CapabilityLevel
        assert result.level == CapabilityLevel.CAN_HANDLE
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_can_handle_falls_back_to_keyword(self, tmp_path):
        """can_handle() falls back to keyword matching when no LLM available."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        runner._llm = None

        result = await runner.can_handle({"task": "searching and calculating"})

        assert result.agent_name == "test-graph"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_can_handle_handles_json_parse_error(self, tmp_path):
        """can_handle() falls back on malformed LLM response."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = LLMResponse(
            content="This is not JSON at all",
            model="test",
        )
        runner._llm = mock_llm

        result = await runner.can_handle({"task": "test"})
        assert result is not None

    def test_keyword_capability_check_computes_overlap(self, tmp_path):
        """_keyword_capability_check() scores keyword overlap."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        from framework.runner.protocol import CapabilityLevel

        result = runner._keyword_capability_check(
            {"task": "searching and calculating operations"}
        )
        assert result.level in (
            CapabilityLevel.CAN_HANDLE,
            CapabilityLevel.UNCERTAIN,
            CapabilityLevel.CANNOT_HANDLE,
        )
        assert 0 <= result.confidence <= 1.0


# ===========================================================================
# TestAgentRunnerLifecycle
# ===========================================================================

class TestAgentRunnerLifecycle:
    """Tests for async context manager and lifecycle methods."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path):
        """Async context manager calls _setup and cleanup."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with patch.object(runner, "_setup") as mock_setup, \
             patch.object(runner, "cleanup_async", new_callable=AsyncMock) as mock_cleanup:
            async with runner as r:
                assert r is runner
                mock_setup.assert_called_once()
            mock_cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_stop_multi_entry(self, tmp_path):
        """start()/stop() operate on AgentRuntime for multi-entry agents."""
        export = _sample_export_dict(with_async_entry_points=True)
        agent_dir = _write_agent_dir(tmp_path, export)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        mock_runtime = MagicMock()
        mock_runtime.start = AsyncMock()
        mock_runtime.stop = AsyncMock()
        mock_runtime.is_running = True
        runner._agent_runtime = mock_runtime

        await runner.start()
        mock_runtime.start.assert_awaited_once()

        await runner.stop()
        mock_runtime.stop.assert_awaited_once()

    def test_cleanup_cleans_tool_registry(self, tmp_path):
        """cleanup() delegates to tool registry."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with patch.object(runner._tool_registry, "cleanup") as mock_clean:
            runner.cleanup()
            mock_clean.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_raises_on_single_entry_agent(self, tmp_path):
        """trigger() raises RuntimeError on single-entry-point agent."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with pytest.raises(RuntimeError, match="multi-entry-point"):
            await runner.trigger("ep1", {"data": "test"})

    @pytest.mark.asyncio
    async def test_get_goal_progress_raises_on_single_entry(self, tmp_path):
        """get_goal_progress() raises RuntimeError on single-entry agent."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        with pytest.raises(RuntimeError, match="multi-entry-point"):
            await runner.get_goal_progress()

    def test_get_entry_points_empty_for_single_entry(self, tmp_path):
        """get_entry_points() returns empty list for single-entry agent."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        assert runner.get_entry_points() == []

    def test_is_running_false_when_no_runtime(self, tmp_path):
        """is_running is False when agent_runtime is None."""
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)

        assert runner.is_running is False


# ===========================================================================
# TestAgentRunnerApiKeyDetection
# ===========================================================================

class TestAgentRunnerApiKeyDetection:
    """Tests for _get_api_key_env_var()."""

    def test_cerebras_model(self, tmp_path):
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner._get_api_key_env_var("cerebras/zai-glm-4.7") == "CEREBRAS_API_KEY"

    def test_openai_model(self, tmp_path):
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner._get_api_key_env_var("gpt-4o") == "OPENAI_API_KEY"

    def test_anthropic_model(self, tmp_path):
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner._get_api_key_env_var("claude-sonnet-4-20250514") == "ANTHROPIC_API_KEY"

    def test_ollama_model_returns_none(self, tmp_path):
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner._get_api_key_env_var("ollama/llama3") is None

    def test_unknown_model_defaults_to_openai(self, tmp_path):
        agent_dir = _write_agent_dir(tmp_path)
        runner = AgentRunner.load(agent_dir, mock_mode=True)
        assert runner._get_api_key_env_var("some-random-model") == "OPENAI_API_KEY"
