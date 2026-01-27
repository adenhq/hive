"""
Tests for Audit Trail Tool.
"""
import json
import tempfile
from pathlib import Path

import pytest
from fastmcp import FastMCP

from aden_tools.tools.audit_trail_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance with audit trail tools registered."""
    server = FastMCP("test")
    register_tools(server)
    return server


@pytest.fixture
def sample_run_data():
    """Sample run data for testing."""
    return {
        "id": "run_123",
        "goal_id": "goal_001",
        "status": "completed",
        "started_at": "2025-01-15T10:00:00Z",
        "completed_at": "2025-01-15T10:05:00Z",
        "decisions": [
            {
                "id": "dec_001",
                "node_id": "search_node",
                "decision_type": "tool_selection",
                "intent": "Search for customer information",
                "reasoning": "Need to find customer details",
                "timestamp": "2025-01-15T10:00:05Z",
                "chosen_option_id": "opt_web_search",
                "options": [
                    {
                        "id": "opt_web_search",
                        "description": "Use web search API",
                        "action_type": "tool_call",
                    },
                    {
                        "id": "opt_database",
                        "description": "Query internal database",
                        "action_type": "tool_call",
                    },
                ],
            }
        ],
        "outcomes": {
            "dec_001": {
                "success": True,
                "summary": "Found 3 results",
                "tokens_used": 150,
                "latency_ms": 1200,
            }
        },
    }


@pytest.fixture
def temp_storage(sample_run_data):
    """Create temporary storage directory with sample run data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        runs_dir = storage_path / "runs"
        runs_dir.mkdir(parents=True)

        # Write sample run data
        run_file = runs_dir / f"{sample_run_data['id']}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(sample_run_data, f)

        yield storage_path


def test_generate_audit_trail_json(mcp, temp_storage, sample_run_data):
    """Test generating JSON audit trail."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="run_123",
        storage_path=str(temp_storage),
        format="json",
        include_outcomes=True,
        include_options=True,
    )

    assert "error" not in result
    assert result["run_id"] == "run_123"
    assert result["goal_id"] == "goal_001"
    assert result["status"] == "completed"
    assert result["total_decisions"] == 1
    assert len(result["timeline"]) == 1

    timeline_entry = result["timeline"][0]
    assert timeline_entry["decision_id"] == "dec_001"
    assert timeline_entry["node_id"] == "search_node"
    assert timeline_entry["intent"] == "Search for customer information"
    assert "chosen_option" in timeline_entry
    assert "outcome" in timeline_entry
    assert timeline_entry["outcome"]["success"] is True


def test_generate_audit_trail_markdown(mcp, temp_storage):
    """Test generating markdown audit trail."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="run_123",
        storage_path=str(temp_storage),
        format="markdown",
    )

    assert "error" not in result
    assert result["format"] == "markdown"
    assert "markdown" in result
    assert "# Audit Trail" in result["markdown"]
    assert "run_123" in result["markdown"]


def test_generate_audit_trail_no_outcomes(mcp, temp_storage):
    """Test generating audit trail without outcomes."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="run_123",
        storage_path=str(temp_storage),
        include_outcomes=False,
    )

    assert "error" not in result
    timeline_entry = result["timeline"][0]
    assert "outcome" not in timeline_entry


def test_generate_audit_trail_no_options(mcp, temp_storage):
    """Test generating audit trail without options."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="run_123",
        storage_path=str(temp_storage),
        include_options=False,
    )

    assert "error" not in result
    timeline_entry = result["timeline"][0]
    assert "chosen_option" not in timeline_entry


def test_generate_audit_trail_invalid_run(mcp, temp_storage):
    """Test error handling for invalid run ID."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="nonexistent",
        storage_path=str(temp_storage),
    )

    assert "error" in result
    assert "not found" in result["error"].lower()


def test_generate_audit_trail_invalid_path(mcp):
    """Test error handling for invalid storage path."""
    tool_fn = mcp._tool_manager._tools["generate_audit_trail"].fn
    result = tool_fn(
        run_id="run_123",
        storage_path="/nonexistent/path",
    )

    assert "error" in result
    assert "does not exist" in result["error"]


def test_list_runs(mcp, temp_storage, sample_run_data):
    """Test listing runs."""
    tool_fn = mcp._tool_manager._tools["list_runs"].fn
    result = tool_fn(storage_path=str(temp_storage))

    assert "error" not in result
    assert result["total_runs"] == 1
    assert len(result["runs"]) == 1
    assert result["runs"][0]["run_id"] == "run_123"
    assert result["runs"][0]["goal_id"] == "goal_001"
    assert result["runs"][0]["total_decisions"] == 1


def test_list_runs_with_goal_filter(mcp, temp_storage):
    """Test listing runs filtered by goal ID."""
    tool_fn = mcp._tool_manager._tools["list_runs"].fn
    result = tool_fn(storage_path=str(temp_storage), goal_id="goal_001")

    assert "error" not in result
    assert len(result["runs"]) == 1

    # Filter by non-existent goal
    result = tool_fn(storage_path=str(temp_storage), goal_id="goal_999")
    assert "error" not in result
    assert len(result["runs"]) == 0


def test_list_runs_with_limit(mcp, temp_storage):
    """Test listing runs with limit."""
    tool_fn = mcp._tool_manager._tools["list_runs"].fn
    result = tool_fn(storage_path=str(temp_storage), limit=5)

    assert "error" not in result
    assert len(result["runs"]) <= 5


def test_list_runs_invalid_path(mcp):
    """Test error handling for invalid storage path."""
    tool_fn = mcp._tool_manager._tools["list_runs"].fn
    result = tool_fn(storage_path="/nonexistent/path")

    assert "error" in result
    assert "does not exist" in result["error"]
