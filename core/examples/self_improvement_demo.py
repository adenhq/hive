"""
Self-Improvement Demo
---------------------
Demonstrates the complete ADAPT pillar: evaluation, failure analysis, and improvement triggers.

This shows how agents can systematically improve themselves over time.

Run with:
    PYTHONPATH=core python core/examples/self_improvement_demo.py
"""

from framework.adaptation.evaluator import AgentEvaluator, EvaluationMetrics, PerformanceTrend
from framework.adaptation.failure_analyzer import FailureAnalyzer, FailureCategory
from framework.adaptation.improvement_trigger import ImprovementTrigger


class MockAgent:
    """Mock agent for demonstration"""
    def __init__(self, accuracy=0.85):
        self.accuracy = accuracy
        self.call_count = 0
        
    def run(self, input_data):
        """Simulate agent execution"""
        import random
        self.call_count += 1
        
        # Simulate success/failure based on accuracy
        success = random.random() < self.accuracy
        
        # Mock result
        class Result:
            def __init__(self, success):
                self.success = success
                self.output = {"result": "mock output"} if success else None
                self.metrics = {"total_cost_usd": 0.001}
        
        return Result(success)


def main():
    print("🚀 Self-Improvement System Demo\n")
    print("Demonstrating Aden's ADAPT pillar: Evaluation → Analysis → Improvement\n")
    
    # Initialize systems
    evaluator = AgentEvaluator(agent_id="demo-agent")
    failure_analyzer = FailureAnalyzer(agent_id="demo-agent")
    improvement_trigger = ImprovementTrigger(
        accuracy_threshold=0.80,
        success_threshold=0.85
    )
    
    # Test cases
    test_cases = [
        {"input": {"task": f"test_{i}"}, "expected": {"result": "mock output"}}
        for i in range(20)
    ]
    
    print("="*60)
    print("📊 SCENARIO 1: Well-Performing Agent")
    print("="*60)
    
    # Create good agent
    good_agent = MockAgent(accuracy=0.90)
    
    # Evaluate
    metrics_v1 = evaluator.evaluate(
        test_cases=test_cases,
        agent_runner=lambda x: good_agent.run(x),
        version="v1.0"
    )
    
    print(evaluator.generate_report())
    
    # Check if improvement needed
    trend = evaluator.get_trend()
    decision = improvement_trigger.decide(
        current_metrics=metrics_v1,
        previous_metrics=None,
        trend=trend,
        failure_analyzer=failure_analyzer
    )
    
    improvement_trigger.print_decision(decision)
    
    # Scenario 2: Degrading agent
    print("\n" + "="*60)
    print("📊 SCENARIO 2: Degrading Agent (Needs Improvement)")
    print("="*60)
    
    # Simulate degradation
    bad_agent = MockAgent(accuracy=0.65)  # Low accuracy
    
    metrics_v2 = evaluator.evaluate(
        test_cases=test_cases,
        agent_runner=lambda x: bad_agent.run(x),
        version="v2.0"
    )
    
    # Record some failures
    from datetime import datetime
    for i in range(7):
        try:
            raise ValueError("Input validation failed: missing required field")
        except Exception as e:
            failure_analyzer.record_failure(
                node_id="validator_node",
                error=e,
                input_data={"task": f"test_{i}"},
                timestamp=datetime.now()
            )
    
    print(evaluator.generate_report())
    
    # Analyze failures
    failure_analyzer.print_failure_report()
    
    # Make improvement decision
    trend = evaluator.get_trend(lookback=2)
    decision = improvement_trigger.decide(
        current_metrics=metrics_v2,
        previous_metrics=metrics_v1,
        trend=trend,
        failure_analyzer=failure_analyzer
    )
    
    improvement_trigger.print_decision(decision)
    
    # Show version comparison
    print("\n" + "="*60)
    print("📈 VERSION COMPARISON: v1.0 vs v2.0")
    print("="*60)
    
    comparison = evaluator.compare_versions("v1.0", "v2.0")
    
    print(f"\n🎯 ACCURACY: {comparison['accuracy_change']:+.1f}%")
    print(f"⏱️  LATENCY: {comparison['latency_change_ms']:+.2f}ms")
    print(f"💰 COST: ${comparison['cost_change_usd']:+.6f}")
    print(f"\n📊 SCORES: v1.0 = {comparison['score_a']:.1f}/100, v2.0 = {comparison['score_b']:.1f}/100")
    print(f"\n🎯 RECOMMENDATION: {comparison['recommendation'].upper()}")
    
    print("\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)
    print("\nThis demonstrates how Aden's ADAPT pillar enables:")
    print("  • Continuous performance evaluation")
    print("  • Automatic failure analysis") 
    print("  • Intelligent improvement triggers")
    print("  • Data-driven agent evolution")
    print("\n")


if __name__ == "__main__":
    main()
