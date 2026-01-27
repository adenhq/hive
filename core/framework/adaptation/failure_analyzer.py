"""
Failure Analysis System - Categorizes and patterns agent failures for targeted improvement.

This enables the self-improvement loop by understanding WHY agents fail.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from collections import Counter


class FailureCategory(Enum):
    """Types of agent failures"""
    INPUT_VALIDATION = "input_validation"      # Bad input data
    LOGIC_ERROR = "logic_error"                # Bug in agent code
    EXTERNAL_API = "external_api"              # Third-party API failure
    TIMEOUT = "timeout"                        # Execution timeout
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # Memory/compute limits
    CONSTRAINT_VIOLATION = "constraint_violation"  # Business rule violated
    UNKNOWN = "unknown"                        # Unclassified


@dataclass
class FailurePattern:
    """Represents a recurring failure pattern"""
    category: FailureCategory
    error_message: str
    node_id: str
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    impact_score: float  # 0-1, how critical this failure is
    
    def get_description(self) -> str:
        """Human-readable description"""
        return f"{self.category.value} in node '{self.node_id}': {self.error_message[:100]}"


class FailureAnalyzer:
    """
    Analyzes agent failures to identify patterns and root causes.
    
    Critical for self-improvement: Can't fix what you don't understand.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.failures: list[dict] = []
        self.patterns: dict[str, FailurePattern] = {}
        
    def record_failure(
        self,
        node_id: str,
        error: Exception,
        input_data: Any,
        timestamp: datetime | None = None
    ):
        """Record a failure for analysis"""
        timestamp = timestamp or datetime.now()
        
        # Categorize failure
        category = self._categorize_error(error)
        
        failure_record = {
            'timestamp': timestamp,
            'node_id': node_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': category,
            'input_data': str(input_data)[:200]  # Truncate for storage
        }
        
        self.failures.append(failure_record)
        
        # Update patterns
        pattern_key = f"{category.value}_{node_id}_{type(error).__name__}"
        
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            pattern.occurrence_count += 1
            pattern.last_seen = timestamp
        else:
            self.patterns[pattern_key] = FailurePattern(
                category=category,
                error_message=str(error),
                node_id=node_id,
                occurrence_count=1,
                first_seen=timestamp,
                last_seen=timestamp,
                impact_score=self._calculate_impact(category)
            )
    
    def _categorize_error(self, error: Exception) -> FailureCategory:
        """Categorize error type"""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Input validation errors
        if 'validation' in error_str or 'invalid' in error_str:
            return FailureCategory.INPUT_VALIDATION
        
        # API/Network errors
        if any(x in error_str for x in ['connection', 'timeout', 'api', 'request', 'http']):
            if 'timeout' in error_str:
                return FailureCategory.TIMEOUT
            return FailureCategory.EXTERNAL_API
        
        # Resource errors
        if any(x in error_str for x in ['memory', 'resource', 'limit']):
            return FailureCategory.RESOURCE_EXHAUSTION
        
        # Logic errors
        if any(x in error_type for x in ['AttributeError', 'TypeError', 'ValueError', 'KeyError']):
            return FailureCategory.LOGIC_ERROR
        
        return FailureCategory.UNKNOWN
    
    def _calculate_impact(self, category: FailureCategory) -> float:
        """Calculate severity/impact of failure type"""
        severity_map = {
            FailureCategory.LOGIC_ERROR: 1.0,           # Most critical - agent broken
            FailureCategory.CONSTRAINT_VIOLATION: 0.9,  # Business rules violated
            FailureCategory.INPUT_VALIDATION: 0.6,      # User error, less critical
            FailureCategory.EXTERNAL_API: 0.7,          # External dependency
            FailureCategory.TIMEOUT: 0.8,               # Performance issue
            FailureCategory.RESOURCE_EXHAUSTION: 0.85,  # Scaling problem
            FailureCategory.UNKNOWN: 0.5                # Need investigation
        }
        return severity_map.get(category, 0.5)
    
    def get_top_patterns(self, limit: int = 5) -> list[FailurePattern]:
        """Get most critical failure patterns"""
        patterns = list(self.patterns.values())
        
        # Sort by impact * occurrence
        patterns.sort(
            key=lambda p: p.impact_score * p.occurrence_count,
            reverse=True
        )
        
        return patterns[:limit]
    
    def get_failure_summary(self) -> dict:
        """Get summary of all failures"""
        if not self.failures:
            return {"total_failures": 0, "categories": {}, "patterns": []}
        
        # Count by category
        category_counts = Counter(f['category'].value for f in self.failures)
        
        # Most affected nodes
        node_counts = Counter(f['node_id'] for f in self.failures)
        
        top_patterns = self.get_top_patterns(5)
        
        return {
            "total_failures": len(self.failures),
            "categories": dict(category_counts),
            "most_affected_nodes": dict(node_counts.most_common(5)),
            "top_patterns": [
                {
                    "description": p.get_description(),
                    "occurrences": p.occurrence_count,
                    "impact": p.impact_score,
                    "first_seen": p.first_seen.isoformat(),
                    "last_seen": p.last_seen.isoformat()
                }
                for p in top_patterns
            ]
        }
    
    def generate_improvement_suggestions(self) -> list[str]:
        """Generate actionable improvement suggestions based on failure patterns"""
        suggestions = []
        top_patterns = self.get_top_patterns(3)
        
        for pattern in top_patterns:
            if pattern.category == FailureCategory.LOGIC_ERROR:
                suggestions.append(
                    f"Fix logic error in node '{pattern.node_id}': {pattern.error_message[:100]}"
                )
            elif pattern.category == FailureCategory.INPUT_VALIDATION:
                suggestions.append(
                    f"Add input validation for node '{pattern.node_id}' to handle: {pattern.error_message[:100]}"
                )
            elif pattern.category == FailureCategory.EXTERNAL_API:
                suggestions.append(
                    f"Add retry logic for external API calls in node '{pattern.node_id}'"
                )
            elif pattern.category == FailureCategory.TIMEOUT:
                suggestions.append(
                    f"Optimize or add timeout handling in node '{pattern.node_id}'"
                )
        
        return suggestions
    
    def print_failure_report(self):
        """Print beautiful failure analysis report"""
        summary = self.get_failure_summary()
        suggestions = self.generate_improvement_suggestions()
        
        print("\n" + "="*60)
        print("🔍 FAILURE ANALYSIS REPORT")
        print("="*60)
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Failures: {summary['total_failures']}")
        
        if summary['categories']:
            print(f"\n📂 FAILURES BY CATEGORY:")
            for category, count in summary['categories'].items():
                print(f"   • {category}: {count}")
        
        if summary['most_affected_nodes']:
            print(f"\n🎯 MOST AFFECTED NODES:")
            for node, count in summary['most_affected_nodes'].items():
                print(f"   • {node}: {count} failures")
        
        if summary['top_patterns']:
            print(f"\n🔥 TOP FAILURE PATTERNS:")
            for i, pattern in enumerate(summary['top_patterns'], 1):
                print(f"\n   {i}. {pattern['description']}")
                print(f"      Occurrences: {pattern['occurrences']}")
                print(f"      Impact: {pattern['impact']:.0%}")
        
        if suggestions:
            print(f"\n💡 IMPROVEMENT SUGGESTIONS:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
        
        print("\n" + "="*60 + "\n")
