"""
Improvement Trigger System - Decides when agents should evolve.

This automates the self-improvement loop by systematically determining
when an agent needs to be evolved vs when it's performing well enough.
"""

from dataclasses import dataclass
from enum import Enum
from .evaluator import EvaluationMetrics, PerformanceTrend
from .failure_analyzer import FailureAnalyzer


class TriggerCondition(Enum):
    """Conditions that trigger agent improvement"""
    ACCURACY_THRESHOLD = "accuracy_below_threshold"
    SUCCESS_RATE_LOW = "success_rate_too_low"
    PERFORMANCE_DEGRADING = "performance_degrading"
    COST_EXPLOSION = "cost_explosion"
    HIGH_FAILURE_RATE = "high_failure_rate"
    REPEATED_PATTERN = "repeated_failure_pattern"


@dataclass
class ImprovementDecision:
    """Decision about whether to improve agent"""
    should_improve: bool
    trigger_conditions: list[TriggerCondition]
    reasons: list[str]
    priority: str  # "critical", "high", "medium", "low"
    suggested_actions: list[str]


class ImprovementTrigger:
    """
    Automated decision system for triggering agent improvements.
    
    This is the "brain" of the ADAPT pillar - decides WHEN to evolve agents.
    """
    
    def __init__(
        self,
        accuracy_threshold: float = 0.80,
        success_threshold: float = 0.85,
        cost_multiplier_threshold: float = 2.0,
        failure_pattern_threshold: int = 5
    ):
        self.accuracy_threshold = accuracy_threshold
        self.success_threshold = success_threshold
        self.cost_multiplier_threshold = cost_multiplier_threshold
        self.failure_pattern_threshold = failure_pattern_threshold
    
    def decide(
        self,
        current_metrics: EvaluationMetrics,
        previous_metrics: EvaluationMetrics | None,
        trend: PerformanceTrend,
        failure_analyzer: FailureAnalyzer
    ) -> ImprovementDecision:
        """
        Decide if agent should be improved.
        
        Returns detailed decision with reasons and suggested actions.
        """
        triggers = []
        reasons = []
        actions = []
        
        # Check 1: Accuracy threshold
        if current_metrics.accuracy < self.accuracy_threshold:
            triggers.append(TriggerCondition.ACCURACY_THRESHOLD)
            reasons.append(
                f"Accuracy {current_metrics.accuracy:.1%} below threshold {self.accuracy_threshold:.1%}"
            )
            actions.append("Review failed test cases and add error handling")
        
        # Check 2: Success rate
        if current_metrics.success_rate < self.success_threshold:
            triggers.append(TriggerCondition.SUCCESS_RATE_LOW)
            reasons.append(
                f"Success rate {current_metrics.success_rate:.1%} below threshold {self.success_threshold:.1%}"
            )
            actions.append("Add error handling and input validation")
        
        # Check 3: Performance degradation
        if trend == PerformanceTrend.DEGRADING:
            triggers.append(TriggerCondition.PERFORMANCE_DEGRADING)
            reasons.append("Performance degrading over recent evaluations")
            actions.append("Analyze recent changes and consider rollback")
        
        # Check 4: Cost explosion
        if previous_metrics:
            cost_ratio = current_metrics.cost_per_run_usd / max(previous_metrics.cost_per_run_usd, 0.000001)
            if cost_ratio > self.cost_multiplier_threshold:
                triggers.append(TriggerCondition.COST_EXPLOSION)
                reasons.append(
                    f"Cost increased {cost_ratio:.1f}x: ${previous_metrics.cost_per_run_usd:.4f} → ${current_metrics.cost_per_run_usd:.4f}"
                )
                actions.append("Review prompt lengths and use cheaper models where possible")
        
        # Check 5: Repeated failure patterns
        top_patterns = failure_analyzer.get_top_patterns(3)
        for pattern in top_patterns:
            if pattern.occurrence_count >= self.failure_pattern_threshold:
                triggers.append(TriggerCondition.REPEATED_PATTERN)
                reasons.append(
                    f"Repeated failure pattern: {pattern.get_description()} ({pattern.occurrence_count}x)"
                )
                actions.extend(failure_analyzer.generate_improvement_suggestions())
                break
        
        # Determine priority
        priority = self._calculate_priority(triggers, current_metrics)
        
        # Make decision
        should_improve = len(triggers) > 0
        
        return ImprovementDecision(
            should_improve=should_improve,
            trigger_conditions=triggers,
            reasons=reasons,
            priority=priority,
            suggested_actions=list(set(actions))  # Remove duplicates
        )
    
    def _calculate_priority(
        self,
        triggers: list[TriggerCondition],
        metrics: EvaluationMetrics
    ) -> str:
        """Calculate improvement priority level"""
        
        # Critical: Multiple triggers or very low accuracy
        if len(triggers) >= 3 or metrics.accuracy < 0.60:
            return "critical"
        
        # High: Accuracy or success rate issues
        if (TriggerCondition.ACCURACY_THRESHOLD in triggers or
            TriggerCondition.SUCCESS_RATE_LOW in triggers):
            return "high"
        
        # Medium: Cost or performance issues
        if (TriggerCondition.COST_EXPLOSION in triggers or
            TriggerCondition.PERFORMANCE_DEGRADING in triggers):
            return "medium"
        
        # Low: Isolated patterns
        return "low"
    
    def print_decision(self, decision: ImprovementDecision):
        """Print formatted improvement decision"""
        print("\n" + "="*60)
        print("🤖 SELF-IMPROVEMENT DECISION")
        print("="*60)
        
        if decision.should_improve:
            print(f"\n🔴 IMPROVEMENT NEEDED - Priority: {decision.priority.upper()}")
            
            print(f"\n📋 TRIGGERED BY:")
            for i, reason in enumerate(decision.reasons, 1):
                print(f"   {i}. {reason}")
            
            print(f"\n💡 SUGGESTED ACTIONS:")
            for i, action in enumerate(decision.suggested_actions, 1):
                print(f"   {i}. {action}")
        else:
            print(f"\n✅ AGENT PERFORMING WELL - No improvement needed")
        
        print("\n" + "="*60 + "\n")
