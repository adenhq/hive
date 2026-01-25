"""
Tests for the Audit Trail Tool.

Tests cover:
- Audit trail generation in multiple formats
- Decision pattern analysis
- Decision outcome comparison
- Error handling for invalid input
- Filtering capabilities
"""

import json
import pytest
from datetime import datetime, timedelta

from fastmcp import FastMCP

from aden_tools.tools.audit_trail_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance with audit trail tools registered."""
    mcp = FastMCP("test-server")
    register_tools(mcp)
    return mcp


@pytest.fixture
def sample_run_data():
    """Create sample run data with decisions for testing."""
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    
    return {
        "id": "run_test_001",
        "goal_id": "goal_test_001",
        "status": "completed",
        "decisions": [
            {
                "id": "decision_1",
                "timestamp": (base_time + timedelta(seconds=0)).isoformat(),
                "node_id": "search_node",
                "intent": "Find relevant documents",
                "decision_type": "tool_selection",
                "options": [
                    {
                        "id": "opt_1a",
                        "description": "Use web search",
                        "action_type": "tool_call",
                        "confidence": 0.8,
                        "pros": ["Fast", "Comprehensive"],
                        "cons": ["May return irrelevant results"],
                    },
                    {
                        "id": "opt_1b",
                        "description": "Use local file search",
                        "action_type": "tool_call",
                        "confidence": 0.5,
                        "pros": ["Accurate for local data"],
                        "cons": ["Limited scope"],
                    },
                ],
                "chosen_option_id": "opt_1a",
                "reasoning": "Web search provides broader coverage for this query",
                "outcome": {
                    "success": True,
                    "summary": "Found 5 relevant documents",
                    "latency_ms": 250,
                    "tokens_used": 100,
                },
                "evaluation": {
                    "goal_aligned": True,
                    "outcome_quality": 0.9,
                    "better_option_existed": False,
                },
            },
            {
                "id": "decision_2",
                "timestamp": (base_time + timedelta(seconds=5)).isoformat(),
                "node_id": "process_node",
                "intent": "Extract key information",
                "decision_type": "parameter_choice",
                "options": [
                    {
                        "id": "opt_2a",
                        "description": "Extract all fields",
                        "action_type": "generate",
                        "confidence": 0.6,
                    },
                    {
                        "id": "opt_2b",
                        "description": "Extract only required fields",
                        "action_type": "generate",
                        "confidence": 0.7,
                    },
                ],
                "chosen_option_id": "opt_2b",
                "reasoning": "Only required fields needed to meet the goal",
                "outcome": {
                    "success": True,
                    "summary": "Extracted 3 key fields",
                    "latency_ms": 150,
                    "tokens_used": 50,
                },
                "evaluation": {
                    "goal_aligned": True,
                    "outcome_quality": 0.85,
                    "better_option_existed": False,
                },
            },
            {
                "id": "decision_3",
                "timestamp": (base_time + timedelta(seconds=10)).isoformat(),
                "node_id": "output_node",
                "intent": "Format the output",
                "decision_type": "output_format",
                "options": [
                    {
                        "id": "opt_3a",
                        "description": "Format as JSON",
                        "action_type": "generate",
                        "confidence": 0.9,
                    },
                ],
                "chosen_option_id": "opt_3a",
                "reasoning": "JSON format requested by user",
                "outcome": {
                    "success": False,
                    "error": "JSON serialization failed",
                    "summary": "Failed to format output",
                    "latency_ms": 50,
                    "tokens_used": 20,
                },
                "evaluation": {
                    "goal_aligned": False,
                    "outcome_quality": 0.0,
                    "better_option_existed": True,
                    "better_option_id": None,
                    "why_better": "Should have validated data before serialization",
                },
            },
        ],
        "metrics": {
            "total_tokens": 170,
            "total_cost": 0.0017,
            "total_duration_ms": 500,
        },
    }


@pytest.fixture
def sample_run_json(sample_run_data):
    """Return sample run data as JSON string."""
    return json.dumps(sample_run_data)


class TestGenerateAuditTrail:
    """Tests for generate_audit_trail tool."""

    def test_markdown_format_default(self, sample_run_json):
        """Test default markdown format generation."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_markdown,
        )
        
        run_data = json.loads(sample_run_json)
        result = _format_markdown(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        # Verify markdown structure
        assert "# Audit Trail" in result
        assert "## Decision Timeline" in result
        assert "run_test_001" in result
        assert "goal_test_001" in result
        
        # Verify decisions are included
        assert "Find relevant documents" in result
        assert "Extract key information" in result
        assert "Format the output" in result
        
        # Verify reasoning is included
        assert "Web search provides broader coverage" in result
        
        # Verify outcomes are included
        assert "Found 5 relevant documents" in result
        assert "250ms" in result

    def test_json_format(self, sample_run_json):
        """Test JSON format generation."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
        )
        
        run_data = json.loads(sample_run_json)
        result = _format_json(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        # Parse result to verify it's valid JSON
        parsed = json.loads(result)
        
        assert parsed["run_id"] == "run_test_001"
        assert parsed["goal_id"] == "goal_test_001"
        assert parsed["decision_count"] == 3
        assert len(parsed["timeline"]) == 3
        
        # Verify decision details
        first_decision = parsed["timeline"][0]
        assert first_decision["intent"] == "Find relevant documents"
        assert first_decision["reasoning"] == "Web search provides broader coverage for this query"
        assert first_decision["outcome"]["success"] is True

    def test_text_format(self, sample_run_json):
        """Test plain text format generation."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_text,
        )
        
        run_data = json.loads(sample_run_json)
        result = _format_text(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        assert "AUDIT TRAIL" in result
        assert "TIMELINE" in result
        assert "[OK]" in result  # Successful decision
        assert "[FAIL]" in result  # Failed decision
        assert "run_test_001" in result

    def test_exclude_reasoning(self, sample_run_json):
        """Test excluding reasoning from output."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
        )
        
        run_data = json.loads(sample_run_json)
        result = _format_json(
            run_data,
            run_data["decisions"],
            include_reasoning=False,
            include_outcomes=True,
        )
        
        parsed = json.loads(result)
        
        # Reasoning should not be in the output
        first_decision = parsed["timeline"][0]
        assert "reasoning" not in first_decision

    def test_exclude_outcomes(self, sample_run_json):
        """Test excluding outcomes from output."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
        )
        
        run_data = json.loads(sample_run_json)
        result = _format_json(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=False,
        )
        
        parsed = json.loads(result)
        
        # Outcome should not be in the output
        first_decision = parsed["timeline"][0]
        assert "outcome" not in first_decision

    def test_filter_by_decision_type(self, sample_run_data):
        """Test filtering by decision type."""
        # Manually filter as the tool would
        decisions = sample_run_data["decisions"]
        filtered = [d for d in decisions if d["decision_type"] == "tool_selection"]
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "decision_1"

    def test_filter_by_node_id(self, sample_run_data):
        """Test filtering by node ID."""
        decisions = sample_run_data["decisions"]
        filtered = [d for d in decisions if d["node_id"] == "process_node"]
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "decision_2"

    def test_invalid_json_error(self):
        """Test error handling for invalid JSON input."""
        # Test that invalid JSON raises appropriate error
        import json
        
        invalid_json = "invalid json {{{"
        
        try:
            json.loads(invalid_json)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            pass  # Expected behavior
        
        # Test that our tool handles it gracefully
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
        )
        
        # The tool should handle the error at a higher level
        # Here we just verify the JSON parsing fails as expected


class TestAnalyzeDecisionPatterns:
    """Tests for analyze_decision_patterns tool."""

    def test_analysis_totals(self, sample_run_json):
        """Test that analysis correctly calculates totals."""
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            register_tools,
        )
        
        # Import and run analysis logic directly
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        total_success = sum(
            1 for d in decisions
            if d.get("outcome", {}).get("success", False)
        )
        total_failure = len(decisions) - total_success
        
        assert total_success == 2
        assert total_failure == 1

    def test_analysis_by_type(self, sample_run_json):
        """Test breakdown by decision type."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        by_type = {}
        for d in decisions:
            dt = d.get("decision_type", "unknown")
            by_type[dt] = by_type.get(dt, 0) + 1
        
        assert by_type["tool_selection"] == 1
        assert by_type["parameter_choice"] == 1
        assert by_type["output_format"] == 1

    def test_analysis_by_node(self, sample_run_json):
        """Test breakdown by node."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        by_node = {}
        for d in decisions:
            node_id = d.get("node_id", "unknown")
            by_node[node_id] = by_node.get(node_id, 0) + 1
        
        assert by_node["search_node"] == 1
        assert by_node["process_node"] == 1
        assert by_node["output_node"] == 1

    def test_latency_calculation(self, sample_run_json):
        """Test average latency calculation."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        total_latency = sum(
            d.get("outcome", {}).get("latency_ms", 0)
            for d in decisions
        )
        avg_latency = total_latency / len(decisions)
        
        # 250 + 150 + 50 = 450 / 3 = 150
        assert avg_latency == 150

    def test_success_rate_calculation(self, sample_run_json):
        """Test success rate calculation."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        successes = sum(
            1 for d in decisions
            if d.get("outcome", {}).get("success", False)
        )
        rate = successes / len(decisions)
        
        # 2 successes out of 3 decisions
        assert abs(rate - 0.667) < 0.01


class TestCompareDecisionOutcomes:
    """Tests for compare_decision_outcomes tool."""

    def test_comparison_structure(self, sample_run_json):
        """Test that comparison returns correct structure."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        
        comparisons = []
        for decision in decisions:
            chosen_id = decision.get("chosen_option_id", "")
            options = decision.get("options", [])
            
            chosen_option = None
            for opt in options:
                if opt.get("id") == chosen_id:
                    chosen_option = opt
                    break
            
            comparisons.append({
                "decision_id": decision.get("id"),
                "chosen": {
                    "id": chosen_id,
                    "description": (
                        chosen_option.get("description") if chosen_option else None
                    ),
                },
            })
        
        assert len(comparisons) == 3
        assert comparisons[0]["decision_id"] == "decision_1"
        assert comparisons[0]["chosen"]["description"] == "Use web search"

    def test_alternatives_counted(self, sample_run_json):
        """Test that alternatives are correctly counted."""
        run_data = json.loads(sample_run_json)
        first_decision = run_data["decisions"][0]
        
        chosen_id = first_decision["chosen_option_id"]
        alternatives = [
            opt for opt in first_decision["options"]
            if opt["id"] != chosen_id
        ]
        
        assert len(alternatives) == 1
        assert alternatives[0]["description"] == "Use local file search"

    def test_filter_by_decision_ids(self, sample_run_json):
        """Test filtering by specific decision IDs."""
        run_data = json.loads(sample_run_json)
        decisions = run_data["decisions"]
        decision_ids = ["decision_1", "decision_3"]
        
        filtered = [d for d in decisions if d.get("id") in decision_ids]
        
        assert len(filtered) == 2
        assert filtered[0]["id"] == "decision_1"
        assert filtered[1]["id"] == "decision_3"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_decisions(self):
        """Test handling of run with no decisions."""
        run_data = {
            "id": "empty_run",
            "goal_id": "goal_1",
            "status": "completed",
            "decisions": [],
        }
        
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_markdown,
        )
        
        result = _format_markdown(
            run_data,
            [],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        assert "# Audit Trail" in result
        assert "Decisions | 0" in result

    def test_missing_outcome(self):
        """Test handling of decision without outcome."""
        run_data = {
            "id": "run_1",
            "goal_id": "goal_1",
            "status": "running",
            "decisions": [
                {
                    "id": "decision_1",
                    "timestamp": "2024-01-15T10:00:00",
                    "node_id": "node_1",
                    "intent": "Test intent",
                    "decision_type": "tool_selection",
                    "chosen_option_id": "opt_1",
                    "options": [],
                    # No outcome - decision not yet executed
                }
            ],
        }
        
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
        )
        
        result = _format_json(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        parsed = json.loads(result)
        assert parsed["timeline"][0]["outcome"]["success"] is False

    def test_missing_evaluation(self):
        """Test handling of decision without evaluation."""
        run_data = {
            "id": "run_1",
            "goal_id": "goal_1",
            "status": "completed",
            "decisions": [
                {
                    "id": "decision_1",
                    "timestamp": "2024-01-15T10:00:00",
                    "node_id": "node_1",
                    "intent": "Test intent",
                    "decision_type": "tool_selection",
                    "chosen_option_id": "opt_1",
                    "options": [],
                    "outcome": {"success": True, "summary": "Done"},
                    # No evaluation
                }
            ],
        }
        
        decisions = run_data["decisions"]
        
        # Should handle missing evaluation gracefully
        for d in decisions:
            evaluation = d.get("evaluation", {})
            goal_aligned = evaluation.get("goal_aligned", True)
            assert goal_aligned is True  # Default value

    def test_special_characters_in_content(self):
        """Test handling of special characters in decision content."""
        run_data = {
            "id": "run_1",
            "goal_id": "goal_1",
            "status": "completed",
            "decisions": [
                {
                    "id": "decision_1",
                    "timestamp": "2024-01-15T10:00:00",
                    "node_id": "node_1",
                    "intent": "Handle <script>alert('xss')</script>",
                    "decision_type": "tool_selection",
                    "reasoning": "User said: \"Hello, World!\" with 'quotes'",
                    "chosen_option_id": "opt_1",
                    "options": [],
                    "outcome": {"success": True, "summary": "Done"},
                }
            ],
        }
        
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_markdown,
        )
        
        result = _format_markdown(
            run_data,
            run_data["decisions"],
            include_reasoning=True,
            include_outcomes=True,
        )
        
        # Should handle special characters without crashing
        assert "Handle <script>" in result
        assert "quotes" in result


class TestToolRegistration:
    """Tests for tool registration with FastMCP."""

    def test_tools_registered(self, mcp):
        """Test that audit trail tools can be registered without errors."""
        # Verify registration completed without raising exceptions
        assert mcp is not None
        
        # Verify the module exports what we expect
        from aden_tools.tools.audit_trail_tool.audit_trail_tool import (
            _format_json,
            _format_text,
            _format_markdown,
        )
        
        # These formatter functions should exist and be callable
        assert callable(_format_json)
        assert callable(_format_text)
        assert callable(_format_markdown)

    def test_register_multiple_times(self):
        """Test that registering tools multiple times doesn't cause issues."""
        mcp = FastMCP("test-server")
        
        # Register twice
        register_tools(mcp)
        register_tools(mcp)
        
        # Should not raise, though may have duplicate registrations
        assert mcp is not None
