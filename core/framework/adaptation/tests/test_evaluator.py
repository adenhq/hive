"""Tests for Agent Evaluation System"""

import pytest
from datetime import datetime
from framework.adaptation.evaluator import AgentEvaluator, EvaluationMetrics, PerformanceTrend


def test_evaluation_metrics_score():
    """Test overall score calculation"""
    metrics = EvaluationMetrics(
        accuracy=0.90,
        success_rate=0.95,
        avg_latency_ms=1000,
        cost_per_run_usd=0.01,
        total_runs=100,
        failed_runs=5
    )
    
    score = metrics.get_score()
    assert 0 <= score <= 100
    assert score > 80  # Should be high with good metrics


def test_evaluator_initialization():
    """Test evaluator initialization"""
    evaluator = AgentEvaluator(agent_id="test-agent")
    
    assert evaluator.agent_id == "test-agent"
    assert len(evaluator.history) == 0
    assert len(evaluator.baselines) == 0


def test_evaluator_stores_history():
    """Test that evaluations are stored in history"""
    evaluator = AgentEvaluator(agent_id="test-agent")
    
    # Mock agent runner
    def mock_runner(input_data):
        class Result:
            success = True
            output = {"result": "ok"}
            metrics = {"total_cost_usd": 0.001}
        return Result()
    
    # Evaluate
    test_cases = [
        {"input": {"x": 1}, "expected": {"result": "ok"}},
        {"input": {"x": 2}, "expected": {"result": "ok"}},
    ]
    
    metrics = evaluator.evaluate(test_cases, mock_runner, version="v1.0")
    
    assert len(evaluator.history) == 1
    assert "v1.0" in evaluator.baselines
    assert metrics.total_runs == 2


def test_trend_detection():
    """Test performance trend analysis"""
    evaluator = AgentEvaluator(agent_id="test-agent")
    
    # Simulate degrading performance
    for i in range(5):
        accuracy = 0.95 - (i * 0.05)  # 95%, 90%, 85%, 80%, 75%
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            success_rate=0.90,
            avg_latency_ms=1000,
            cost_per_run_usd=0.01,
            total_runs=10,
            failed_runs=1,
            version=f"v1.{i}"
        )
        evaluator.history.append((datetime.now(), f"v1.{i}", metrics))
        evaluator.baselines[f"v1.{i}"] = metrics
    
    trend = evaluator.get_trend(lookback=5)
    assert trend == PerformanceTrend.DEGRADING


def test_version_comparison():
    """Test comparing two agent versions"""
    evaluator = AgentEvaluator(agent_id="test-agent")
    
    # Add two versions
    metrics_v1 = EvaluationMetrics(
        accuracy=0.80,
        success_rate=0.85,
        avg_latency_ms=1000,
        cost_per_run_usd=0.01,
        total_runs=10,
        failed_runs=2,
        version="v1.0"
    )
    
    metrics_v2 = EvaluationMetrics(
        accuracy=0.90,
        success_rate=0.95,
        avg_latency_ms=800,
        cost_per_run_usd=0.008,
        total_runs=10,
        failed_runs=1,
        version="v2.0"
    )
    
    evaluator.baselines["v1.0"] = metrics_v1
    evaluator.baselines["v2.0"] = metrics_v2
    
    comparison = evaluator.compare_versions("v1.0", "v2.0")
    
    assert comparison["improved"] == True
    assert comparison["accuracy_change"] > 0
    assert comparison["recommendation"] == "deploy_b"


def test_improvement_trigger():
    """Test should_trigger_improvement logic"""
    evaluator = AgentEvaluator(agent_id="test-agent")
    
    # Low accuracy metrics
    bad_metrics = EvaluationMetrics(
        accuracy=0.70,  # Below 80% threshold
        success_rate=0.75,
        avg_latency_ms=1000,
        cost_per_run_usd=0.01,
        total_runs=10,
        failed_runs=3,
        version="v1.0"
    )
    
    evaluator.history.append((datetime.now(), "v1.0", bad_metrics))
    
    should_improve, reason = evaluator.should_trigger_improvement()
    
    assert should_improve == True
    assert "Accuracy below threshold" in reason
