"""
Tests for schema validation.

Tests the Pydantic models in framework.schemas to ensure they work correctly.
"""

import pytest
from datetime import datetime
from framework.schemas.decision import Decision, DecisionType, Option, Outcome, DecisionEvaluation
from framework.schemas.run import Run, RunStatus, Problem, RunMetrics, RunSummary


class TestDecisionType:
    """Tests for DecisionType enum."""
    
    def test_decision_type_values(self):
        """Test that DecisionType has expected values."""
        assert DecisionType.TOOL_SELECTION == "tool_selection"
        assert DecisionType.PARAMETER_CHOICE == "parameter_choice"
        assert DecisionType.PATH_CHOICE == "path_choice"
        assert DecisionType.OUTPUT_FORMAT == "output_format"
        assert DecisionType.RETRY_STRATEGY == "retry_strategy"
        assert DecisionType.DELEGATION == "delegation"
        assert DecisionType.TERMINATION == "termination"
        assert DecisionType.CUSTOM == "custom"


class TestOption:
    """Tests for Option model."""
    
    def test_option_creation(self):
        """Test creating a basic Option."""
        option = Option(
            id="opt1",
            description="Test option",
            action_type="tool_call"
        )
        
        assert option.id == "opt1"
        assert option.description == "Test option"
        assert option.action_type == "tool_call"
        assert option.confidence == 0.5  # default
        assert option.pros == []
        assert option.cons == []
        assert option.action_params == {}

    def test_option_with_all_fields(self):
        """Test Option with all fields populated."""
        option = Option(
            id="opt2",
            description="Complex option",
            action_type="generate",
            action_params={"model": "gpt-4"},
            pros=["Fast", "Accurate"],
            cons=["Expensive"],
            confidence=0.9
        )
        
        assert option.id == "opt2"
        assert option.pros == ["Fast", "Accurate"]
        assert option.cons == ["Expensive"]
        assert option.confidence == 0.9


class TestOutcome:
    """Tests for Outcome model."""
    
    def test_outcome_success(self):
        """Test successful outcome."""
        outcome = Outcome(
            success=True,
            result="Test result",
            tokens_used=100,
            latency_ms=500,
            summary="Operation completed successfully"
        )
        
        assert outcome.success is True
        assert outcome.result == "Test result"
        assert outcome.error is None
        assert outcome.tokens_used == 100
        assert outcome.latency_ms == 500

    def test_outcome_failure(self):
        """Test failed outcome."""
        outcome = Outcome(
            success=False,
            error="Something went wrong",
            tokens_used=50,
            latency_ms=200
        )
        
        assert outcome.success is False
        assert outcome.error == "Something went wrong"
        assert outcome.result is None


class TestDecisionEvaluation:
    """Tests for DecisionEvaluation model."""
    
    def test_decision_evaluation_creation(self):
        """Test creating a DecisionEvaluation."""
        eval = DecisionEvaluation(
            goal_aligned=True,
            alignment_score=0.8,
            better_option_existed=False,
            outcome_quality=0.9,
            contributed_to_success=True,
            explanation="Good decision"
        )
        
        assert eval.goal_aligned is True
        assert eval.alignment_score == 0.8
        assert eval.better_option_existed is False
        assert eval.outcome_quality == 0.9

    def test_decision_evaluation_validation(self):
        """Test validation constraints."""
        # alignment_score should be between 0 and 1
        with pytest.raises(ValueError):
            DecisionEvaluation(alignment_score=-0.1)
        
        with pytest.raises(ValueError):
            DecisionEvaluation(alignment_score=1.1)
        
        # outcome_quality should be between 0 and 1
        with pytest.raises(ValueError):
            DecisionEvaluation(outcome_quality=-0.1)
        
        with pytest.raises(ValueError):
            DecisionEvaluation(outcome_quality=1.1)


class TestDecision:
    """Tests for Decision model."""
    
    def test_decision_creation(self):
        """Test creating a basic Decision."""
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Test intent",
            decision_type=DecisionType.TOOL_SELECTION,
            options=[
                Option(id="opt1", description="Option 1", action_type="tool_call")
            ],
            chosen_option_id="opt1",
            reasoning="Test reasoning"
        )
        
        assert decision.id == "dec1"
        assert decision.node_id == "node1"
        assert decision.intent == "Test intent"
        assert decision.decision_type == DecisionType.TOOL_SELECTION
        assert len(decision.options) == 1
        assert decision.chosen_option_id == "opt1"
        assert decision.reasoning == "Test reasoning"

    def test_decision_computed_properties(self):
        """Test computed properties."""
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Test",
            options=[
                Option(id="opt1", description="Good option", action_type="tool_call"),
                Option(id="opt2", description="Bad option", action_type="generate")
            ],
            chosen_option_id="opt1"
        )
        
        # Test chosen_option property
        chosen = decision.chosen_option
        assert chosen is not None
        assert chosen.id == "opt1"
        assert chosen.description == "Good option"
        
        # Test was_successful (no outcome yet)
        assert decision.was_successful is False
        
        # Test was_good_decision (no evaluation yet)
        assert decision.was_good_decision is False

    def test_decision_with_outcome(self):
        """Test decision with outcome."""
        outcome = Outcome(success=True, result="Success")
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Test",
            options=[Option(id="opt1", description="Option", action_type="tool_call")],
            chosen_option_id="opt1",
            outcome=outcome
        )
        
        assert decision.was_successful is True
        assert decision.was_good_decision is True  # defaults to successful when no evaluation

    def test_decision_summary_for_builder(self):
        """Test summary generation."""
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Process data",
            options=[Option(id="opt1", description="Use tool", action_type="tool_call")],
            chosen_option_id="opt1"
        )
        
        summary = decision.summary_for_builder()
        assert "node1" in summary
        assert "Process data" in summary
        assert "Use tool" in summary


class TestRunStatus:
    """Tests for RunStatus enum."""
    
    def test_run_status_values(self):
        """Test RunStatus enum values."""
        assert RunStatus.RUNNING == "running"
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.STUCK == "stuck"
        assert RunStatus.CANCELLED == "cancelled"


class TestProblem:
    """Tests for Problem model."""
    
    def test_problem_creation(self):
        """Test creating a Problem."""
        problem = Problem(
            id="prob1",
            severity="critical",
            description="Test problem",
            root_cause="Test cause",
            suggested_fix="Test fix"
        )
        
        assert problem.id == "prob1"
        assert problem.severity == "critical"
        assert problem.description == "Test problem"
        assert problem.root_cause == "Test cause"
        assert problem.suggested_fix == "Test fix"


class TestRunMetrics:
    """Tests for RunMetrics model."""
    
    def test_run_metrics_creation(self):
        """Test creating RunMetrics."""
        metrics = RunMetrics(
            total_decisions=10,
            successful_decisions=8,
            failed_decisions=2,
            total_tokens=1000,
            total_latency_ms=5000,
            nodes_executed=["node1", "node2"],
            edges_traversed=["edge1"]
        )
        
        assert metrics.total_decisions == 10
        assert metrics.successful_decisions == 8
        assert metrics.failed_decisions == 2
        assert metrics.success_rate == 0.8

    def test_run_metrics_empty(self):
        """Test empty RunMetrics."""
        metrics = RunMetrics()
        
        assert metrics.total_decisions == 0
        assert metrics.success_rate == 0.0


class TestRun:
    """Tests for Run model."""
    
    def test_run_creation(self):
        """Test creating a basic Run."""
        run = Run(
            id="run1",
            goal_id="goal1",
            goal_description="Test goal",
            input_data={"input": "test"}
        )
        
        assert run.id == "run1"
        assert run.goal_id == "goal1"
        assert run.status == RunStatus.RUNNING
        assert run.completed_at is None
        assert len(run.decisions) == 0
        assert len(run.problems) == 0

    def test_run_add_decision(self):
        """Test adding decisions to a run."""
        run = Run(id="run1", goal_id="goal1")
        
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Test",
            options=[Option(id="opt1", description="Option", action_type="tool_call")],
            chosen_option_id="opt1"
        )
        
        run.add_decision(decision)
        
        assert len(run.decisions) == 1
        assert run.metrics.total_decisions == 1
        assert "node1" in run.metrics.nodes_executed

    def test_run_record_outcome(self):
        """Test recording outcomes."""
        run = Run(id="run1", goal_id="goal1")
        
        decision = Decision(
            id="dec1",
            node_id="node1",
            intent="Test",
            options=[Option(id="opt1", description="Option", action_type="tool_call")],
            chosen_option_id="opt1"
        )
        
        run.add_decision(decision)
        
        outcome = Outcome(success=True, tokens_used=100, latency_ms=500)
        run.record_outcome("dec1", outcome)
        
        assert run.metrics.successful_decisions == 1
        assert run.metrics.total_tokens == 100
        assert run.metrics.total_latency_ms == 500

    def test_run_add_problem(self):
        """Test adding problems."""
        run = Run(id="run1", goal_id="goal1")
        
        problem_id = run.add_problem(
            severity="critical",
            description="Test problem",
            root_cause="Test cause",
            suggested_fix="Test fix"
        )
        
        assert len(run.problems) == 1
        assert run.problems[0].id == problem_id
        assert run.problems[0].severity == "critical"

    def test_run_complete(self):
        """Test completing a run."""
        run = Run(id="run1", goal_id="goal1")
        
        run.complete(RunStatus.COMPLETED, "Test narrative")
        
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None
        assert run.narrative == "Test narrative"

    def test_run_duration(self):
        """Test duration calculation."""
        run = Run(id="run1", goal_id="goal1")
        
        # Not completed yet
        assert run.duration_ms == 0
        
        # Complete the run
        run.complete(RunStatus.COMPLETED)
        assert run.duration_ms >= 0


class TestRunSummary:
    """Tests for RunSummary model."""
    
    def test_run_summary_creation(self):
        """Test creating a RunSummary."""
        summary = RunSummary(
            run_id="run1",
            goal_id="goal1",
            status=RunStatus.COMPLETED,
            duration_ms=1000,
            decision_count=5,
            success_rate=0.8,
            problem_count=2,
            narrative="Test narrative"
        )
        
        assert summary.run_id == "run1"
        assert summary.status == RunStatus.COMPLETED
        assert summary.duration_ms == 1000
        assert summary.decision_count == 5
        assert summary.success_rate == 0.8

    def test_run_summary_from_run(self):
        """Test creating summary from run."""
        run = Run(id="run1", goal_id="goal1", goal_description="Test goal")
        
        # Add some decisions
        decision1 = Decision(
            id="dec1",
            node_id="node1",
            intent="Test decision",
            options=[Option(id="opt1", description="Option", action_type="tool_call")],
            chosen_option_id="opt1",
            outcome=Outcome(success=True, summary="Success")
        )
        
        decision2 = Decision(
            id="dec2",
            node_id="node2",
            intent="Failed decision",
            options=[Option(id="opt1", description="Option", action_type="tool_call")],
            chosen_option_id="opt1",
            outcome=Outcome(success=False, summary="Failed")
        )
        
        run.add_decision(decision1)
        run.add_decision(decision2)
        run.record_outcome("dec1", decision1.outcome)
        run.record_outcome("dec2", decision2.outcome)
        
        # Add a problem
        run.add_problem("critical", "Test problem")
        
        # Complete run
        run.complete(RunStatus.COMPLETED)
        
        # Create summary
        summary = RunSummary.from_run(run)
        
        assert summary.run_id == "run1"
        assert summary.status == RunStatus.COMPLETED
        assert summary.decision_count == 2
        assert summary.success_rate == 0.5
        assert summary.problem_count == 1
        assert len(summary.successes) > 0
        assert len(summary.key_decisions) > 0