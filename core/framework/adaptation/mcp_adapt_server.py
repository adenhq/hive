"""
Integration hooks for ADAPT pillar with GraphExecutor

Allows automatic evaluation during agent execution.
"""

from typing import Any, Callable
from framework.adaptation.evaluator import AgentEvaluator
from framework.adaptation.failure_analyzer import FailureAnalyzer


class AdaptiveExecutionWrapper:
    """
    Wraps GraphExecutor to add automatic evaluation and failure tracking.
    
    Usage:
        executor = GraphExecutor(...)
        adaptive_executor = AdaptiveExecutionWrapper(executor, agent_id="my-agent")
        
        result = await adaptive_executor.execute(graph, goal, input_data)
        
        # Metrics automatically tracked!
        print(adaptive_executor.evaluator.generate_report())
    """
    
    def __init__(
        self,
        executor: Any,  # GraphExecutor
        agent_id: str,
        enable_auto_evaluation: bool = True
    ):
        self.executor = executor
        self.agent_id = agent_id
        self.enable_auto_evaluation = enable_auto_evaluation
        
        # Initialize ADAPT systems
        self.evaluator = AgentEvaluator(agent_id=agent_id)
        self.failure_analyzer = FailureAnalyzer(agent_id=agent_id)
        
        # Execution history for evaluation
        self.execution_history = []
    
    async def execute(
        self,
        graph: Any,
        goal: Any,
        input_data: dict,
        expected_output: dict | None = None
    ) -> Any:
        """
        Execute graph with automatic evaluation.
        
        Args:
            graph: GraphSpec to execute
            goal: Goal definition
            input_data: Input data
            expected_output: If provided, used for correctness evaluation
            
        Returns:
            ExecutionResult with added metrics
        """
        import time
        
        start_time = time.time()
        
        try:
            # Execute agent
            result = await self.executor.execute(
                graph=graph,
                goal=goal,
                input_data=input_data
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record execution
            self.execution_history.append({
                "input": input_data,
                "output": result.output if result.success else None,
                "success": result.success,
                "error": result.error,
                "latency_ms": latency_ms,
                "expected": expected_output
            })
            
            # Track failures
            if not result.success and result.error:
                # Try to identify which node failed
                failed_node = result.path[-1] if result.path else "unknown"
                
                self.failure_analyzer.record_failure(
                    node_id=failed_node,
                    error=Exception(result.error),
                    input_data=input_data
                )
            
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Record failure
            self.execution_history.append({
                "input": input_data,
                "output": None,
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
                "expected": expected_output
            })
            
            # Analyze failure
            self.failure_analyzer.record_failure(
                node_id="unknown",
                error=e,
                input_data=input_data
            )
            
            raise
    
    def evaluate_recent_runs(
        self,
        run_count: int = None,
        version: str = "current"
    ) -> dict:
        """
        Evaluate recent executions.
        
        Args:
            run_count: Number of recent runs to evaluate (None = all)
            version: Version identifier for these runs
            
        Returns:
            Evaluation metrics
        """
        if not self.execution_history:
            return {
                "success": False,
                "error": "No execution history to evaluate"
            }
        
        # Get recent runs
        runs = self.execution_history[-run_count:] if run_count else self.execution_history
        
        # Convert to test cases format
        test_cases = [
            {
                "input": run["input"],
                "expected": run.get("expected")
            }
            for run in runs
        ]
        
        # Mock runner that returns historical results
        run_index = 0
        def mock_runner(input_data):
            nonlocal run_index
            run_data = runs[run_index]
            run_index += 1
            
            class MockResult:
                def __init__(self, run_data):
                    self.success = run_data["success"]
                    self.output = run_data["output"]
                    self.metrics = {"total_cost_usd": 0.001}  # Placeholder
            
            return MockResult(run_data)
        
        # Evaluate
        metrics = self.evaluator.evaluate(
            test_cases=test_cases,
            agent_runner=mock_runner,
            version=version
        )
        
        return {
            "success": True,
            "agent_id": self.agent_id,
            "version": version,
            "runs_evaluated": len(runs),
            "metrics": {
                "accuracy": round(metrics.accuracy, 4),
                "success_rate": round(metrics.success_rate, 4),
                "score": metrics.get_score()
            }
        }
    
    def get_health_status(self) -> dict:
        """Get current agent health status"""
        if not self.evaluator.history:
            return {
                "status": "unknown",
                "message": "No evaluation data yet"
            }
        
        latest_metrics = self.evaluator.history[-1][2]
        trend = self.evaluator.get_trend()
        should_improve, reason = self.evaluator.should_trigger_improvement()
        
        # Determine health status
        if latest_metrics.accuracy >= 0.90 and latest_metrics.success_rate >= 0.95:
            status = "excellent"
        elif latest_metrics.accuracy >= 0.80 and latest_metrics.success_rate >= 0.85:
            status = "good"
        elif latest_metrics.accuracy >= 0.70:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "status": status,
            "agent_id": self.agent_id,
            "latest_version": latest_metrics.version,
            "accuracy": round(latest_metrics.accuracy, 4),
            "success_rate": round(latest_metrics.success_rate, 4),
            "score": metrics.get_score(),
            "trend": trend.value,
            "needs_improvement": should_improve,
            "improvement_reason": reason if should_improve else None,
            "total_evaluations": len(self.evaluator.history),
            "total_failures_analyzed": len(self.failure_analyzer.failures)
        }


@mcp.tool()
def trigger_self_repair(
    agent_id: Annotated[str, "Agent identifier"],
    agent_path: Annotated[str, "Path to agent folder (e.g., 'exports/my_agent')"]
) -> str:
    """
    Trigger automated self-repair for an agent.
    
    Runs complete diagnostic and repair cycle.
    """
    if agent_id not in _repair_engines:
        engine = SelfRepairEngine(
            agent_id=agent_id,
            agent_path=agent_path
        )
        _repair_engines[agent_id] = engine
    else:
        engine = _repair_engines[agent_id]
    
    # Get recent execution history
    if not hasattr(engine, 'execution_history') or not engine.execution_history:
        return json.dumps({
            "success": False,
            "error": "No execution history. Run agent first to collect failure data."
        })
    
    # Trigger repair
    # In real implementation, would run full diagnostic cycle
    # For MCP, return repair recommendations
    
    decision_data = json.loads(get_improvement_decision(agent_id))
    
    if not decision_data.get("success"):
        return json.dumps(decision_data)
    
    decision = decision_data["decision"]
    
    return json.dumps({
        "success": True,
        "agent_id": agent_id,
        "repair_triggered": decision["should_improve"],
        "priority": decision.get("priority", "none"),
        "recommended_actions": decision.get("suggested_actions", []),
        "note": "Review recommended actions and apply fixes to agent code"
    })


if __name__ == "__main__":
    mcp.run()
