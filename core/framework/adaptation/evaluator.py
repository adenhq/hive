"""
Agent Evaluation System - Measures agent performance and tracks improvement over time.

This is the foundation of the ADAPT pillar - without evaluation, there's no self-improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from enum import Enum


class PerformanceTrend(Enum):
    """Performance trend direction"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"


@dataclass
class EvaluationMetrics:
    """Complete metrics for agent evaluation"""
    
    # Core metrics
    accuracy: float                    # % of correct outputs (0-1)
    success_rate: float                # % without errors (0-1)
    avg_latency_ms: float             # Average response time
    cost_per_run_usd: float           # Average cost
    
    # Quality metrics
    precision: float = 0.0            # For classification tasks
    recall: float = 0.0               # For classification tasks
    f1_score: float = 0.0             # Harmonic mean
    
    # User feedback
    user_satisfaction: float = 0.0    # 0-1 scale
    
    # Metadata
    total_runs: int = 0
    failed_runs: int = 0
    evaluation_date: datetime = field(default_factory=datetime.now)
    version: str = "v0.0.1"
    
    def get_score(self) -> float:
        """Overall quality score (0-100)"""
        weights = {
            'accuracy': 0.4,
            'success_rate': 0.3,
            'speed': 0.2,  # Inverse of latency
            'cost': 0.1    # Inverse of cost
        }
        
        # Normalize latency (assume 1000ms is baseline)
        speed_score = min(1.0, 1000 / max(self.avg_latency_ms, 1))
        
        # Normalize cost (assume $0.01 is baseline)
        cost_score = min(1.0, 0.01 / max(self.cost_per_run_usd, 0.001))
        
        score = (
            self.accuracy * weights['accuracy'] +
            self.success_rate * weights['success_rate'] +
            speed_score * weights['speed'] +
            cost_score * weights['cost']
        )
        
        return round(score * 100, 2)


class AgentEvaluator:
    """
    Evaluates agent performance over time and triggers improvements.
    
    This is the core of the ADAPT pillar - enables continuous improvement.
    """
    
    def __init__(self, agent_id: str, storage_path: str = "./evaluations"):
        self.agent_id = agent_id
        self.storage_path = storage_path
        self.history: list[tuple[datetime, str, EvaluationMetrics]] = []
        self.baselines: dict[str, EvaluationMetrics] = {}
        
    def evaluate(
        self,
        test_cases: list[dict],
        agent_runner: Any,
        version: str = "latest"
    ) -> EvaluationMetrics:
        """
        Run agent on test cases and calculate performance metrics.
        
        Args:
            test_cases: List of {"input": ..., "expected": ...} dicts
            agent_runner: Function that runs agent with input
            version: Agent version identifier
            
        Returns:
            EvaluationMetrics with complete performance data
        """
        import time
        
        results = []
        total_latency = 0.0
        total_cost = 0.0
        failed = 0
        
        for test in test_cases:
            start_time = time.time()
            
            try:
                # Run agent
                result = agent_runner(test['input'])
                latency_ms = (time.time() - start_time) * 1000
                
                # Check correctness
                correct = self._check_correctness(result.output, test.get('expected'))
                
                results.append({
                    'correct': correct,
                    'success': result.success,
                    'latency_ms': latency_ms,
                    'cost': result.metrics.get('total_cost_usd', 0) if hasattr(result, 'metrics') else 0
                })
                
                total_latency += latency_ms
                if hasattr(result, 'metrics'):
                    total_cost += result.metrics.get('total_cost_usd', 0)
                if not result.success:
                    failed += 1
                    
            except Exception as e:
                # Count as failure
                failed += 1
                results.append({
                    'correct': False,
                    'success': False,
                    'latency_ms': (time.time() - start_time) * 1000,
                    'cost': 0
                })
        
        # Calculate metrics
        total_runs = len(test_cases)
        successful_runs = total_runs - failed
        correct_runs = sum(1 for r in results if r.get('correct', False))
        
        metrics = EvaluationMetrics(
            accuracy=correct_runs / max(total_runs, 1),
            success_rate=successful_runs / max(total_runs, 1),
            avg_latency_ms=total_latency / max(total_runs, 1),
            cost_per_run_usd=total_cost / max(total_runs, 1),
            total_runs=total_runs,
            failed_runs=failed,
            evaluation_date=datetime.now(),
            version=version
        )
        
        # Store in history
        self.history.append((datetime.now(), version, metrics))
        self.baselines[version] = metrics
        
        return metrics
    
    def _check_correctness(self, output: Any, expected: Any) -> bool:
        """Check if agent output matches expected result"""
        if expected is None:
            return True  # No expected output to check
        
        # Simple equality check (can be enhanced)
        return output == expected
    
    def compare_versions(self, version_a: str, version_b: str) -> dict:
        """Compare two agent versions"""
        if version_a not in self.baselines or version_b not in self.baselines:
            raise ValueError(f"Version not found in baselines")
        
        a = self.baselines[version_a]
        b = self.baselines[version_b]
        
        accuracy_delta = b.accuracy - a.accuracy
        latency_delta = b.avg_latency_ms - a.avg_latency_ms
        cost_delta = b.cost_per_run_usd - a.cost_per_run_usd
        
        # Determine if improvement
        improved = (
            accuracy_delta > 0 or
            (accuracy_delta == 0 and latency_delta < 0) or
            (accuracy_delta == 0 and latency_delta == 0 and cost_delta < 0)
        )
        
        return {
            "version_a": version_a,
            "version_b": version_b,
            "accuracy_change": round(accuracy_delta * 100, 2),  # As percentage
            "latency_change_ms": round(latency_delta, 2),
            "cost_change_usd": round(cost_delta, 6),
            "score_a": a.get_score(),
            "score_b": b.get_score(),
            "improved": improved,
            "recommendation": "deploy_b" if improved else "keep_a"
        }
    
    def get_trend(self, lookback: int = 5) -> PerformanceTrend:
        """Analyze performance trend over recent evaluations"""
        if len(self.history) < 2:
            return PerformanceTrend.UNKNOWN
        
        recent = self.history[-lookback:]
        accuracies = [m[2].accuracy for m in recent]
        
        # Simple linear trend
        if len(accuracies) < 2:
            return PerformanceTrend.UNKNOWN
        
        first_half_avg = sum(accuracies[:len(accuracies)//2]) / max(len(accuracies)//2, 1)
        second_half_avg = sum(accuracies[len(accuracies)//2:]) / max(len(accuracies) - len(accuracies)//2, 1)
        
        delta = second_half_avg - first_half_avg
        
        if delta > 0.02:  # 2% improvement
            return PerformanceTrend.IMPROVING
        elif delta < -0.02:  # 2% degradation
            return PerformanceTrend.DEGRADING
        else:
            return PerformanceTrend.STABLE
    
    def should_trigger_improvement(self) -> tuple[bool, str]:
        """
        Decide if agent needs improvement.
        
        Returns:
            (should_improve: bool, reason: str)
        """
        if not self.history:
            return False, "No evaluation history"
        
        latest = self.history[-1][2]
        
        # Check absolute thresholds
        if latest.accuracy < 0.80:
            return True, f"Accuracy below threshold: {latest.accuracy:.1%} < 80%"
        
        if latest.success_rate < 0.85:
            return True, f"Success rate below threshold: {latest.success_rate:.1%} < 85%"
        
        # Check trend
        trend = self.get_trend()
        if trend == PerformanceTrend.DEGRADING:
            return True, "Performance degrading over recent runs"
        
        # Check cost explosion
        if len(self.history) >= 2:
            prev_cost = self.history[-2][2].cost_per_run_usd
            curr_cost = latest.cost_per_run_usd
            if curr_cost > prev_cost * 2:  # Cost doubled
                return True, f"Cost doubled: ${prev_cost:.4f} → ${curr_cost:.4f}"
        
        return False, "Performance acceptable"
    
    def generate_report(self) -> str:
        """Generate human-readable evaluation report"""
        if not self.history:
            return "No evaluations yet"
        
        latest = self.history[-1][2]
        trend = self.get_trend()
        should_improve, reason = self.should_trigger_improvement()
        
        report = f"""
{'='*60}
🎯 AGENT EVALUATION REPORT
{'='*60}

Agent: {self.agent_id}
Version: {latest.version}
Evaluated: {latest.evaluation_date.strftime('%Y-%m-%d %H:%M:%S')}

📊 PERFORMANCE METRICS:
   Accuracy: {latest.accuracy:.1%}
   Success Rate: {latest.success_rate:.1%}
   Overall Score: {latest.get_score()}/100

⏱️  EFFICIENCY:
   Avg Latency: {latest.avg_latency_ms:.2f}ms
   Cost per Run: ${latest.cost_per_run_usd:.6f}

📈 TREND: {trend.value.upper()}

🔍 RUNS ANALYZED:
   Total: {latest.total_runs}
   Successful: {latest.total_runs - latest.failed_runs}
   Failed: {latest.failed_runs}

{'🔴 IMPROVEMENT NEEDED' if should_improve else '✅ PERFORMING WELL'}
{f'Reason: {reason}' if should_improve else ''}

{'='*60}
"""
        return report
