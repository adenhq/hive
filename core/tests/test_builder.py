"""Tests for the BuilderQuery interface - how Builder analyzes agent runs.

DEPRECATED: These tests rely on the deprecated FileStorage backend.
BuilderQuery and Runtime both use FileStorage which is deprecated.
New code should use unified session storage instead.
"""

from pathlib import Path

import pytest

from framework import BuilderQuery, Runtime
from framework.schemas.run import RunStatus
from framework.builder.query import PatternAnalysis
from framework.builder.query import FailureAnalysis


# Mark all tests in this module as skipped - they rely on deprecated FileStorage
pytestmark = pytest.mark.skip(reason="Tests rely on deprecated FileStorage backend")


def create_successful_run(runtime: Runtime, goal_id: str = "test_goal") -> str:
    """Helper to create a successful run with decisions."""
    run_id = runtime.start_run(goal_id, f"Test goal: {goal_id}")

    runtime.set_node("search-node")
    d1 = runtime.decide(
        intent="Search for data",
        options=[
            {"id": "web", "description": "Web search", "pros": ["Fresh data"]},
            {"id": "cache", "description": "Use cache", "pros": ["Fast"]},
        ],
        chosen="web",
        reasoning="Need fresh data",
    )
    runtime.record_outcome(d1, success=True, result={"items": 3}, tokens_used=50)

    runtime.set_node("process-node")
    d2 = runtime.decide(
        intent="Process results",
        options=[{"id": "filter", "description": "Filter and transform"}],
        chosen="filter",
        reasoning="Standard processing",
    )
    runtime.record_outcome(d2, success=True, result={"processed": 3}, tokens_used=30)

    runtime.end_run(success=True, narrative="Successfully processed data")
    return run_id


def create_failed_run(runtime: Runtime, goal_id: str = "test_goal") -> str:
    """Helper to create a failed run."""
    run_id = runtime.start_run(goal_id, f"Test goal: {goal_id}")

    runtime.set_node("search-node")
    d1 = runtime.decide(
        intent="Search for data",
        options=[{"id": "web", "description": "Web search"}],
        chosen="web",
        reasoning="Need data",
    )
    runtime.record_outcome(d1, success=True, result={"items": 0})

    runtime.set_node("process-node")
    d2 = runtime.decide(
        intent="Process results",
        options=[{"id": "process", "description": "Process data"}],
        chosen="process",
        reasoning="Continue pipeline",
    )
    runtime.record_outcome(d2, success=False, error="No data to process")

    runtime.report_problem(
        severity="critical",
        description="Processing failed due to empty input",
        decision_id=d2,
        suggested_fix="Add empty input handling",
    )

    runtime.end_run(success=False, narrative="Failed to process - no data")
    return run_id


class TestBuilderQueryBasics:
    """Test basic query operations."""

    def test_get_run_summary(self, tmp_path: Path):
        """Test getting a run summary."""
        runtime = Runtime(tmp_path)
        run_id = create_successful_run(runtime)

        query = BuilderQuery(tmp_path)
        summary = query.get_run_summary(run_id)

        assert summary is not None
        assert summary.run_id == run_id
        assert summary.status == RunStatus.COMPLETED
        assert summary.decision_count == 2
        assert summary.success_rate == 1.0

    def test_get_full_run(self, tmp_path: Path):
        """Test getting the full run details."""
        runtime = Runtime(tmp_path)
        run_id = create_successful_run(runtime)

        query = BuilderQuery(tmp_path)
        run = query.get_full_run(run_id)

        assert run is not None
        assert run.id == run_id
        assert len(run.decisions) == 2
        assert run.decisions[0].node_id == "search-node"
        assert run.decisions[1].node_id == "process-node"

    def test_list_runs_for_goal(self, tmp_path: Path):
        """Test listing all runs for a goal."""
        runtime = Runtime(tmp_path)
        create_successful_run(runtime, "goal_a")
        create_successful_run(runtime, "goal_a")
        create_successful_run(runtime, "goal_b")

        query = BuilderQuery(tmp_path)
        summaries = query.list_runs_for_goal("goal_a")

        assert len(summaries) == 2
        for s in summaries:
            assert s.goal_id == "goal_a"

    def test_get_recent_failures(self, tmp_path: Path):
        """Test getting recent failed runs."""
        runtime = Runtime(tmp_path)
        create_successful_run(runtime)
        create_failed_run(runtime)
        create_failed_run(runtime)

        query = BuilderQuery(tmp_path)
        failures = query.get_recent_failures()

        assert len(failures) == 2
        for f in failures:
            assert f.status == RunStatus.FAILED

    def test_pattern_analysis_to_dict(self):
        analysis = PatternAnalysis(
            goal_id="goal_123",
            run_count=10,
            success_rate=0.7,
            common_failures=[("timeout", 3), ("bad_input", 2)],
            problematic_nodes=[("node_a", 0.4)],
            decision_patterns={"choice": "A"},
        )

        result = analysis.to_dict()

        assert result == {
            "goal_id": "goal_123",
            "run_count": 10,
            "success_rate": 0.7,
            "common_failures": [("timeout", 3), ("bad_input", 2)],
            "problematic_nodes": [("node_a", 0.4)],
            "decision_patterns": {"choice": "A"},
        }

    def test_pattern_analysis_str_contains_key_info(self):
        analysis = PatternAnalysis(
            goal_id="goal_123",
            run_count=10,
            success_rate=0.7,
            common_failures=[("timeout", 3)],
            problematic_nodes=[("node_a", 0.4)],
            decision_patterns={},
        )

        text = str(analysis)

        assert "goal_123" in text
        assert "Runs Analyzed: 10" in text
        assert "timeout" in text
        assert "node_a" in text


class TestFailureAnalysis:
    """Test failure analysis capabilities."""

    def test_analyze_failure(self, tmp_path: Path):
        """Test analyzing why a run failed."""
        runtime = Runtime(tmp_path)
        run_id = create_failed_run(runtime)

        query = BuilderQuery(tmp_path)
        analysis = query.analyze_failure(run_id)

        assert analysis is not None
        assert analysis.run_id == run_id
        assert "No data to process" in analysis.root_cause
        assert len(analysis.decision_chain) >= 2
        assert len(analysis.problems) == 1
        assert "critical" in analysis.problems[0].lower()

    def test_analyze_failure_returns_none_for_success(self, tmp_path: Path):
        """analyze_failure returns None for successful runs."""
        runtime = Runtime(tmp_path)
        run_id = create_successful_run(runtime)

        query = BuilderQuery(tmp_path)
        analysis = query.analyze_failure(run_id)

        assert analysis is None

    def test_failure_analysis_has_suggestions(self, tmp_path: Path):
        """Failure analysis should include suggestions."""
        runtime = Runtime(tmp_path)
        run_id = create_failed_run(runtime)

        query = BuilderQuery(tmp_path)
        analysis = query.analyze_failure(run_id)

        assert len(analysis.suggestions) > 0
        # Should include the suggested fix from the problem
        assert any("empty input" in s.lower() for s in analysis.suggestions)

    def test_get_decision_trace(self, tmp_path: Path):
        """Test getting a readable decision trace."""
        runtime = Runtime(tmp_path)
        run_id = create_successful_run(runtime)

        query = BuilderQuery(tmp_path)
        trace = query.get_decision_trace(run_id)

        assert len(trace) == 2
        assert "search-node" in trace[0]
        assert "process-node" in trace[1]
    
    def test_failure_analysis_to_dict(self):
        """Test dictionary from Failure Analysis"""
        analysis = FailureAnalysis(
            run_id="run_1234",
            failure_point="failure_point_1234",
            root_cause="root_cause_1234",
            decision_chain=["chain_1", "chain_2", "chain_3"],
            problems=["sdvsdvs", "svsvs"],
            suggestions=[]

        )

        result = analysis.to_dict()

        assert result == {
            "run_id":"run_1234",
            "failure_point": "failure_point_1234",
            "root_cause": "root_cause_1234",
            "decision_chain": ["chain_1", "chain_2" , "chain_3"],
            "problems" : ["sdvsdvs", "svsvs"],
            "suggestions": []
        }

    def test_failure_analysis_str_contains_key_info(self):
        analysis = FailureAnalysis(
            run_id="run_1234",
            failure_point="failure_point",
            root_cause="root_cause",
            decision_chain=["a", "b"],
            problems=["problem1"],
            suggestions=["fix1"],
        )

        text = str(analysis)

        assert "run_1234" in text
        assert "Failure Point:" in text
        assert "root_cause" in text
        assert "1. a" in text
        assert "problem1" in text
        assert "fix1" in text



class TestPatternAnalysis:
    """Test pattern detection across runs."""

    def test_find_patterns_basic(self, tmp_path: Path):
        """Test basic pattern finding."""
        runtime = Runtime(tmp_path)
        create_successful_run(runtime, "goal_x")
        create_successful_run(runtime, "goal_x")
        create_failed_run(runtime, "goal_x")

        query = BuilderQuery(tmp_path)
        patterns = query.find_patterns("goal_x")

        assert patterns is not None
        assert patterns.goal_id == "goal_x"
        assert patterns.run_count == 3
        assert 0 < patterns.success_rate < 1  # 2/3 success

    def test_find_patterns_common_failures(self, tmp_path: Path):
        """Test finding common failures."""
        runtime = Runtime(tmp_path)
        # Create multiple runs with the same failure
        for _ in range(3):
            create_failed_run(runtime, "failing_goal")

        query = BuilderQuery(tmp_path)
        patterns = query.find_patterns("failing_goal")

        assert len(patterns.common_failures) > 0
        # "No data to process" should be a common failure
        failure_messages = [f[0] for f in patterns.common_failures]
        assert any("No data to process" in msg for msg in failure_messages)

    def test_find_patterns_problematic_nodes(self, tmp_path: Path):
        """Test finding problematic nodes."""
        runtime = Runtime(tmp_path)
        # Create runs where process-node always fails
        for _ in range(3):
            create_failed_run(runtime, "node_test")

        query = BuilderQuery(tmp_path)
        patterns = query.find_patterns("node_test")

        # process-node should be flagged as problematic
        problematic_node_ids = [n[0] for n in patterns.problematic_nodes]
        assert "process-node" in problematic_node_ids

    def test_compare_runs(self, tmp_path: Path):
        """Test comparing two runs."""
        runtime = Runtime(tmp_path)
        run1 = create_successful_run(runtime)
        run2 = create_failed_run(runtime)

        query = BuilderQuery(tmp_path)
        comparison = query.compare_runs(run1, run2)

        assert comparison["run_1"]["status"] == "completed"
        assert comparison["run_2"]["status"] == "failed"
        assert len(comparison["differences"]) > 0

    def test_compare_runs_with_conditions(self , tmp_path: Path) -> str:
        """Test comparing two runs for some conditions"""
        runtime = Runtime(tmp_path)
        run_id = runtime.start_run("goal_id", f"Test goal: {"goal_id"}")

        runtime.set_node("search-node")
        d1 = runtime.decide(
            intent="Search",
            options=[{"id": "web", "description": "Web"}],
            chosen="web",
            reasoning="Search",
        )
        runtime.record_outcome(d1, success=True)

        runtime.set_node("extra-node")  # 👈 this is the key difference
        d2 = runtime.decide(
            intent="Extra step",
            options=[{"id": "x", "description": "Extra"}],
            chosen="x",
            reasoning="Extra",
        )
        runtime.record_outcome(d2, success=True)

        runtime.end_run(success=True)

        query = BuilderQuery(tmp_path)

        run1 = create_successful_run(runtime)
        comparison = query.compare_runs(run1, run_id)

        diffs = comparison["differences"]

        assert any("Nodes only in run 1" in d for d in diffs)
        assert any("Nodes only in run 2" in d for d in diffs)

    def  test_compare_runs_different_len(self , tmp_path: Path):
        """Test comparing two runs having different lengths"""
        runtime = Runtime(tmp_path)
        run_id = runtime.start_run("goal_id", f"Test goal: {"goal_id"}")

        runtime.set_node("only-node")
        d1 = runtime.decide(
            intent="Only step",
            options=[{"id": "x", "description": "Only option"}],
            chosen="x",
            reasoning="Only decision",
        )
        runtime.record_outcome(d1, success=True)

        runtime.end_run(success=True)
        query = BuilderQuery(tmp_path)

        run1 = create_successful_run(runtime)

        comparison = query.compare_runs(run1, run_id)

        diffs = comparison["differences"]

        assert any(
        "Decision count:" in d
        for d in diffs
        )

    def test_compare_empty_run(self , tmp_path:Path):
        """Test comparing run when one of them is empty"""
        query = BuilderQuery(tmp_path)

        comparison = query.compare_runs("" , "")

        assert comparison is not None
        assert "error" in comparison
        assert "not found" in comparison["error"].lower()


    def test_compare_run_nodes(self, tmp_path: Path):
        """"Test analyze feature when two nodes aren't equal"""
        runtime = Runtime(tmp_path)
        run_id = runtime.start_run("goal_id", f"Test goal: {"goal_id"}")

        runtime.set_node("decision-node")
        d1 = runtime.decide(
            intent="Choose source",
            options=[
                {"id": "a", "description": "Option A"},
                {"id": "b", "description": "Option B"},
            ],
            chosen="a",
            reasoning="Picked A",
            constraints=["must_be_fast", "low_memory"],
        )

        runtime.record_outcome(
            d1,
            success=False,
            error="Choice failed",
        )

        runtime.end_run(success=False, narrative="Failure with alternatives")

        query = BuilderQuery(tmp_path)
        analysis = query.analyze_failure(run_id)

        assert analysis is not None
        assert len(analysis.suggestions) > 0

        assert any(
            "Consider alternative" in s
            for s in analysis.suggestions
        )




class TestImprovementSuggestions:
    """Test improvement suggestion generation."""

    def test_suggest_improvements(self, tmp_path: Path):
        """Test generating improvement suggestions."""
        runtime = Runtime(tmp_path)
        # Create runs with failures to trigger suggestions
        for _ in range(3):
            create_failed_run(runtime, "improve_goal")

        query = BuilderQuery(tmp_path)
        suggestions = query.suggest_improvements("improve_goal")

        assert len(suggestions) > 0
        # Should suggest improving the problematic node
        node_suggestions = [s for s in suggestions if s["type"] == "node_improvement"]
        assert len(node_suggestions) > 0

    def test_suggest_improvements_for_low_success_rate(self, tmp_path: Path):
        """Should suggest architecture review for low success rate."""
        runtime = Runtime(tmp_path)
        # 4 failures, 1 success = 20% success rate
        for _ in range(4):
            create_failed_run(runtime, "low_success")
        create_successful_run(runtime, "low_success")

        query = BuilderQuery(tmp_path)
        suggestions = query.suggest_improvements("low_success")

        arch_suggestions = [s for s in suggestions if s["type"] == "architecture"]
        assert len(arch_suggestions) > 0
        assert arch_suggestions[0]["priority"] == "high"

    def test_get_node_performance(self, tmp_path: Path):
        """Test getting performance metrics for a node."""
        runtime = Runtime(tmp_path)
        create_successful_run(runtime)
        create_successful_run(runtime)

        query = BuilderQuery(tmp_path)
        perf = query.get_node_performance("search-node")

        assert perf["node_id"] == "search-node"
        assert perf["total_decisions"] == 2
        assert perf["success_rate"] == 1.0
        assert perf["total_tokens"] == 100  # 50 tokens per run

    def test_suggest_improvements_returns_empty_when_no_runs(self, tmp_path: Path):
        query = BuilderQuery(tmp_path)

        suggestions = query.suggest_improvements("non_existent_goal")

        assert suggestions == []



class TestBuilderWorkflow:
    """Test complete Builder workflows."""

    def test_builder_investigation_workflow(self, tmp_path: Path):
        """Test a complete investigation workflow as Builder would use it."""
        runtime = Runtime(tmp_path)

        # Set up scenario: some successes, some failures
        for _ in range(2):
            create_successful_run(runtime, "customer_goal")
        for _ in range(2):
            create_failed_run(runtime, "customer_goal")

        query = BuilderQuery(tmp_path)

        # Step 1: Get overview of the goal
        summaries = query.list_runs_for_goal("customer_goal")
        assert len(summaries) == 4

        # Step 2: Find patterns
        patterns = query.find_patterns("customer_goal")
        assert patterns.success_rate == 0.5  # 2/4

        # Step 3: Get recent failures
        failures = query.get_recent_failures()
        assert len(failures) == 2

        # Step 4: Analyze a specific failure
        failure_id = failures[0].run_id
        analysis = query.analyze_failure(failure_id)
        assert analysis is not None
        assert len(analysis.suggestions) > 0

        # Step 5: Generate improvement suggestions
        suggestions = query.suggest_improvements("customer_goal")
        assert len(suggestions) > 0

        # Step 6: Check node performance
        perf = query.get_node_performance("process-node")
        assert perf["success_rate"] < 1.0  # process-node fails in failed runs

