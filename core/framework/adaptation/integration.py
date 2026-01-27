"""
Integration hooks for ADAPT pillar with GraphExecutor

Allows automatic evaluation during agent execution.
"""

from typing import Any
from framework.adaptation.evaluator import AgentEvaluator
from framework.adaptation.failure_analyzer import FailureAnalyzer


class AdaptiveExecutionWrapper:
    """
    Wraps GraphExecutor to add automatic evaluation and failure tracking.
    
    Usage:
        from framework.graph.executor import GraphExecutor
        from framework.adaptation.integration import AdaptiveExecutionWrapper
        
        executor = GraphExecutor(...)
        adaptive_executor = AdaptiveExecutionWrapper(executor, agent_id="my-agent")
        
        result = await adaptive_executor.execute(graph, goal, input_data)
        
        # Metrics automatically tracked!
        print(adaptive_executor.get_health_status())
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
        """Execute graph with automatic evaluation"""
        import time
        from datetime import datetime
        
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
                "timestamp": datetime.now(),
                "input": input_data,
                "output": result.output if result.success else None,
                "success": result.success,
                "error": result.error,
                "latency_ms": latency_ms,
                "expected": expected_output,
                "path": result.path
            })
            
            # Track failures
            if not result.success and result.error:
                failed_node = result.path[-1] if result.path else "unknown"
                
                self.failure_analyzer.record_failure(
                    node_id=failed_node,
                    error=Exception(result.error),
                    input_data=input_data,
                    timestamp=datetime.now()
                )
            
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Record failure
            self.execution_history.append({
                "timestamp": datetime.now(),
                "input": input_data,
                "output": None,
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
                "expected": expected_output,
                "path": []
            })
            
            # Analyze failure
            self.failure_analyzer.record_failure(
                node_id="unknown",
                error=e,
                input_data=input_data,
                timestamp=datetime.now()
            )
            
            raise
    
    def get_health_status(self) -> dict:
        """Get current agent health status"""
        if not self.evaluator.history:
            # Evaluate recent runs if we have execution history
            if self.execution_history:
                self._auto_evaluate()
        
        if not self.evaluator.history:
            return {
                "status": "unknown",
                "message": "No evaluation data yet",
                "total_executions": len(self.execution_history)
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
            "score": latest_metrics.get_score(),
            "trend": trend.value,
            "needs_improvement": should_improve,
            "improvement_reason": reason if should_improve else None,
            "total_evaluations": len(self.evaluator.history),
            "total_executions": len(self.execution_history),
            "total_failures": len(self.failure_analyzer.failures)
        }
    
    def _auto_evaluate(self):
        """Automatically evaluate recent executions"""
        if not self.execution_history:
            return
        
        # Create test cases from execution history
        test_cases = [
            {
                "input": run["input"],
                "expected": run.get("expected")
            }
            for run in self.execution_history
        ]
        
        # Create mock runner from history
        run_index = 0
        def mock_runner(input_data):
            nonlocal run_index
            if run_index >= len(self.execution_history):
                run_index = 0
            
            run_data = self.execution_history[run_index]
            run_index += 1
            
            class MockResult:
                def __init__(self, data):
                    self.success = data["success"]
                    self.output = data["output"]
                    self.metrics = {"total_cost_usd": 0.001}
            
            return MockResult(run_data)
        
        # Run evaluation
        self.evaluator.evaluate(
            test_cases=test_cases,
            agent_runner=mock_runner,
            version=f"auto-eval-{len(self.evaluator.history) + 1}"
        )
