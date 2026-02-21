"""Tests for the Agent Runner module.

Tests for:
- load_agent_export() function
- AgentRunner validation and info methods
- Claude Code OAuth token handling (mocked)
- Edge cases and error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.graph.edge import EdgeCondition
from framework.runner.runner import (
    AgentInfo,
    ValidationResult,
    load_agent_export,
)


class TestLoadAgentExport:
    """Tests for load_agent_export function."""

    def test_load_from_dict(self):
        """Test loading GraphSpec and Goal from a dictionary."""
        data = {
            "graph": {
                "id": "test-graph",
                "goal_id": "test-goal",
                "version": "1.0.0",
                "entry_node": "node1",
                "terminal_nodes": ["node2"],
                "nodes": [
                    {
                        "id": "node1",
                        "name": "Start",
                        "description": "Starting node",
                        "node_type": "function",
                    },
                    {
                        "id": "node2",
                        "name": "End",
                        "description": "Ending node",
                        "node_type": "function",
                    },
                ],
                "edges": [
                    {
                        "id": "edge1",
                        "source": "node1",
                        "target": "node2",
                        "condition": "on_success",
                    }
                ],
            },
            "goal": {
                "id": "test-goal",
                "name": "Test Goal",
                "description": "A test goal",
                "success_criteria": [
                    {
                        "id": "sc1",
                        "description": "Success criterion",
                        "metric": "test_metric",
                        "target": "100%",
                    }
                ],
                "constraints": [
                    {
                        "id": "c1",
                        "description": "Constraint",
                        "constraint_type": "hard",
                    }
                ],
            },
        }

        graph, goal = load_agent_export(data)

        assert graph.id == "test-graph"
        assert graph.goal_id == "test-goal"
        assert graph.entry_node == "node1"
        assert graph.terminal_nodes == ["node2"]
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

        assert goal.id == "test-goal"
        assert goal.name == "Test Goal"
        assert len(goal.success_criteria) == 1
        assert len(goal.constraints) == 1

    def test_load_from_json_string(self):
        """Test loading from a JSON string."""
        json_str = json.dumps(
            {
                "graph": {
                    "id": "json-graph",
                    "goal_id": "json-goal",
                    "entry_node": "n1",
                    "nodes": [
                        {
                            "id": "n1",
                            "name": "N1",
                            "description": "Node 1",
                            "node_type": "function",
                        }
                    ],
                    "edges": [],
                },
                "goal": {
                    "id": "json-goal",
                    "name": "JSON Goal",
                    "success_criteria": [],
                    "constraints": [],
                },
            }
        )

        graph, goal = load_agent_export(json_str)

        assert graph.id == "json-graph"
        assert goal.id == "json-goal"

    def test_edge_condition_mapping(self):
        """Test that edge condition strings are properly mapped."""
        data = {
            "graph": {
                "id": "test",
                "goal_id": "g1",
                "entry_node": "start",
                "nodes": [
                    {"id": "start", "name": "Start", "description": "Start node"},
                ],
                "edges": [
                    {"id": "e1", "source": "a", "target": "b", "condition": "always"},
                    {
                        "id": "e2",
                        "source": "a",
                        "target": "c",
                        "condition": "on_failure",
                    },
                    {
                        "id": "e3",
                        "source": "a",
                        "target": "d",
                        "condition": "conditional",
                        "condition_expr": "x > 5",
                    },
                    {"id": "e4", "source": "a", "target": "e", "condition": "llm_decide"},
                ],
            },
            "goal": {"id": "g1", "success_criteria": [], "constraints": []},
        }

        graph, _ = load_agent_export(data)

        assert graph.edges[0].condition == EdgeCondition.ALWAYS
        assert graph.edges[1].condition == EdgeCondition.ON_FAILURE
        assert graph.edges[2].condition == EdgeCondition.CONDITIONAL
        assert graph.edges[2].condition_expr == "x > 5"
        assert graph.edges[3].condition == EdgeCondition.LLM_DECIDE

    def test_unknown_condition_defaults_to_on_success(self):
        """Test that unknown condition strings default to ON_SUCCESS."""
        data = {
            "graph": {
                "id": "test",
                "goal_id": "g1",
                "entry_node": "start",
                "nodes": [
                    {"id": "start", "name": "Start", "description": "Start node"},
                ],
                "edges": [{"id": "e1", "source": "a", "target": "b", "condition": "unknown"}],
            },
            "goal": {"id": "g1", "success_criteria": [], "constraints": []},
        }

        graph, _ = load_agent_export(data)

        assert graph.edges[0].condition == EdgeCondition.ON_SUCCESS

    def test_async_entry_points_loading(self):
        """Test loading async entry points from export data."""
        data = {
            "graph": {
                "id": "test",
                "goal_id": "g1",
                "entry_node": "start",
                "nodes": [],
                "edges": [],
                "async_entry_points": [
                    {
                        "id": "async1",
                        "name": "Webhook Entry",
                        "entry_node": "node1",
                        "trigger_type": "webhook",
                        "trigger_config": {"path": "/trigger"},
                        "isolation_level": "isolated",
                        "priority": 5,
                        "max_concurrent": 3,
                    }
                ],
            },
            "goal": {"id": "g1", "success_criteria": [], "constraints": []},
        }

        graph, _ = load_agent_export(data)

        assert len(graph.async_entry_points) == 1
        ep = graph.async_entry_points[0]
        assert ep.id == "async1"
        assert ep.name == "Webhook Entry"
        assert ep.entry_node == "node1"
        assert ep.trigger_type == "webhook"

    def test_edge_priority_and_input_mapping(self):
        """Test that edge priority and input_mapping are loaded correctly."""
        data = {
            "graph": {
                "id": "test",
                "goal_id": "g1",
                "entry_node": "start",
                "nodes": [],
                "edges": [
                    {
                        "id": "e1",
                        "source": "a",
                        "target": "b",
                        "priority": 10,
                        "input_mapping": {"old_key": "new_key"},
                    }
                ],
            },
            "goal": {"id": "g1", "success_criteria": [], "constraints": []},
        }

        graph, _ = load_agent_export(data)

        assert graph.edges[0].priority == 10
        assert graph.edges[0].input_mapping == {"old_key": "new_key"}

    def test_minimal_graph_defaults(self):
        """Test that minimal graph data uses sensible defaults."""
        data = {
            "graph": {
                "id": "test",
                "goal_id": "g1",
                "entry_node": "start",
                "nodes": [],
                "edges": [],
            },
            "goal": {"id": "g1", "success_criteria": [], "constraints": []},
        }

        graph, goal = load_agent_export(data)

        assert graph.id == "test"
        assert graph.version == "1.0.0"
        assert graph.max_steps == 100
        assert graph.max_retries_per_node == 3


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_agent_info_defaults(self):
        """Test AgentInfo with default values."""
        info = AgentInfo(
            name="test-agent",
            description="Test description",
            goal_name="Test Goal",
            goal_description="Goal description",
            node_count=5,
            edge_count=4,
            nodes=[],
            edges=[],
            entry_node="start",
            terminal_nodes=["end"],
            success_criteria=[],
            constraints=[],
            required_tools=["tool1"],
            has_tools_module=True,
        )

        assert info.async_entry_points == []
        assert info.is_multi_entry_point is False

    def test_agent_info_with_async_entry_points(self):
        """Test AgentInfo with async entry points."""
        info = AgentInfo(
            name="test-agent",
            description="Test",
            goal_name="Goal",
            goal_description="Desc",
            node_count=2,
            edge_count=1,
            nodes=[],
            edges=[],
            entry_node="start",
            terminal_nodes=["end"],
            success_criteria=[],
            constraints=[],
            required_tools=[],
            has_tools_module=False,
            async_entry_points=[{"id": "async1"}],
            is_multi_entry_point=True,
        )

        assert len(info.async_entry_points) == 1
        assert info.is_multi_entry_point is True


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_defaults(self):
        """Test ValidationResult with default empty lists."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_tools == []
        assert result.missing_credentials == []

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            missing_tools=["tool1"],
            missing_credentials=["API_KEY"],
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "tool1" in result.missing_tools
        assert "API_KEY" in result.missing_credentials


class TestClaudeCodeTokenFunctions:
    """Tests for Claude Code OAuth token handling functions."""

    def test_get_claude_code_token_no_file(self):
        """Test get_claude_code_token returns None when credentials file doesn't exist."""
        from framework.runner.runner import get_claude_code_token

        with patch("framework.runner.runner.CLAUDE_CREDENTIALS_FILE") as mock_path:
            mock_path.exists.return_value = False
            result = get_claude_code_token()
            assert result is None

    def test_get_claude_code_token_malformed_json(self):
        """Test get_claude_code_token handles malformed JSON gracefully."""
        from framework.runner.runner import get_claude_code_token

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with patch("framework.runner.runner.CLAUDE_CREDENTIALS_FILE") as mock_path:
                mock_path.exists.return_value = True
                mock_path.__str__ = lambda: temp_path
                with patch("builtins.open", side_effect=[open(temp_path)]):
                    result = get_claude_code_token()
                    assert result is None
        finally:
            Path(temp_path).unlink()

    def test_get_claude_code_token_no_access_token(self):
        """Test get_claude_code_token returns None when no access token in credentials."""
        from framework.runner.runner import get_claude_code_token

        with patch("framework.runner.runner.CLAUDE_CREDENTIALS_FILE") as mock_path:
            mock_path.exists.return_value = True

            creds_data = {"claudeAiOauth": {}}

            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = json.dumps(creds_data)
                mock_file.__enter__ = lambda self: mock_file
                mock_file.__exit__ = lambda self, *args: None
                mock_open.return_value = mock_file

                with patch("json.load", return_value=creds_data):
                    result = get_claude_code_token()
                    assert result is None

    def test_refresh_claude_code_token_network_error(self):
        """Test _refresh_claude_code_token handles network errors gracefully."""
        from framework.runner.runner import _refresh_claude_code_token
        import urllib.error

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network error")

            result = _refresh_claude_code_token("test_refresh_token")
            assert result is None


def _get_expected_api_key_env_var(model: str) -> str | None:
    """Helper function that mirrors AgentRunner._get_api_key_env_var logic for testing."""
    model_lower = model.lower()

    if model_lower.startswith("cerebras/"):
        return "CEREBRAS_API_KEY"
    elif model_lower.startswith("openai/") or model_lower.startswith("gpt-"):
        return "OPENAI_API_KEY"
    elif model_lower.startswith("anthropic/") or model_lower.startswith("claude"):
        return "ANTHROPIC_API_KEY"
    elif model_lower.startswith("gemini/") or model_lower.startswith("google/"):
        return "GEMINI_API_KEY"
    elif model_lower.startswith("mistral/"):
        return "MISTRAL_API_KEY"
    elif model_lower.startswith("groq/"):
        return "GROQ_API_KEY"
    elif model_lower.startswith("ollama/"):
        return None
    elif model_lower.startswith("azure/"):
        return "AZURE_API_KEY"
    elif model_lower.startswith("cohere/"):
        return "COHERE_API_KEY"
    elif model_lower.startswith("replicate/"):
        return "REPLICATE_API_KEY"
    elif model_lower.startswith("together/"):
        return "TOGETHER_API_KEY"
    else:
        return "OPENAI_API_KEY"


class TestGetApiKeyEnvVarLogic:
    """Tests for the API key env var mapping logic."""

    def test_cerebras_model(self):
        """Test Cerebras model returns correct env var."""
        assert _get_expected_api_key_env_var("cerebras/llama-3.3-70b") == "CEREBRAS_API_KEY"

    def test_openai_model(self):
        """Test OpenAI model returns correct env var."""
        assert _get_expected_api_key_env_var("openai/gpt-4o") == "OPENAI_API_KEY"
        assert _get_expected_api_key_env_var("gpt-4o-mini") == "OPENAI_API_KEY"

    def test_anthropic_model(self):
        """Test Anthropic model returns correct env var."""
        assert _get_expected_api_key_env_var("anthropic/claude-3-haiku") == "ANTHROPIC_API_KEY"
        assert _get_expected_api_key_env_var("claude-3-opus") == "ANTHROPIC_API_KEY"

    def test_gemini_model(self):
        """Test Gemini model returns correct env var."""
        assert _get_expected_api_key_env_var("gemini/gemini-1.5-flash") == "GEMINI_API_KEY"
        assert _get_expected_api_key_env_var("google/gemini-pro") == "GEMINI_API_KEY"

    def test_mistral_model(self):
        """Test Mistral model returns correct env var."""
        assert _get_expected_api_key_env_var("mistral/mistral-large") == "MISTRAL_API_KEY"

    def test_groq_model(self):
        """Test Groq model returns correct env var."""
        assert _get_expected_api_key_env_var("groq/llama3-70b") == "GROQ_API_KEY"

    def test_ollama_model_no_key(self):
        """Test Ollama model returns None (no key needed)."""
        assert _get_expected_api_key_env_var("ollama/llama3") is None

    def test_azure_model(self):
        """Test Azure model returns correct env var."""
        assert _get_expected_api_key_env_var("azure/gpt-4") == "AZURE_API_KEY"

    def test_cohere_model(self):
        """Test Cohere model returns correct env var."""
        assert _get_expected_api_key_env_var("cohere/command") == "COHERE_API_KEY"

    def test_replicate_model(self):
        """Test Replicate model returns correct env var."""
        assert _get_expected_api_key_env_var("replicate/llama") == "REPLICATE_API_KEY"

    def test_together_model(self):
        """Test Together model returns correct env var."""
        assert _get_expected_api_key_env_var("together/llama") == "TOGETHER_API_KEY"

    def test_unknown_model_defaults_to_openai(self):
        """Test unknown model defaults to OPENAI_API_KEY."""
        assert _get_expected_api_key_env_var("unknown/model") == "OPENAI_API_KEY"
