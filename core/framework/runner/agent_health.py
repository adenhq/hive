"""
Agent Health Analyzer - Analyze agent performance and provide health insights.

Provides:
- Success rate analysis
- Performance metrics
- Error pattern detection
- Health recommendations
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from framework.schemas.run import Run, RunStatus
from framework.storage.backend import FileStorage


@dataclass
class HealthMetrics:
    """Health metrics for an agent."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    total_duration_ms: int = 0
    avg_decisions: float = 0.0
    total_cost_usd: float = 0.0
    recent_runs: int = 0  # Runs in last 24 hours
    recent_success_rate: float = 0.0
    common_errors: dict[str, int] = field(default_factory=dict)
    node_usage: dict[str, int] = field(default_factory=dict)
    status_distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete health report for an agent."""
    agent_name: str
    storage_path: Path
    metrics: HealthMetrics
    health_status: str  # "healthy", "degraded", "unhealthy"
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    last_run: datetime | None = None
    analyzed_at: datetime = field(default_factory=datetime.now)


class AgentHealth:
    """
    Analyzer for agent health and performance.

    Example:
        health = AgentHealth(agent_path)
        report = health.analyze()
        print(report.health_status)
    """

    def __init__(self, storage_path: Path | str):
        """
        Initialize health analyzer.

        Args:
            storage_path: Path to agent storage directory
        """
        self.storage_path = Path(storage_path)
        self._storage = FileStorage(self.storage_path)

    def analyze(self, days: int = 7) -> HealthReport:
        """
        Analyze agent health over the specified time period.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            HealthReport with metrics and recommendations
        """
        # Get all runs
        all_runs = self._get_all_runs()

        if not all_runs:
            return HealthReport(
                agent_name=self.storage_path.name,
                storage_path=self.storage_path,
                metrics=HealthMetrics(),
                health_status="unknown",
                issues=["No runs found - agent has not been executed"],
                recommendations=["Run the agent to generate health data"],
            )

        # Filter by time period
        cutoff = datetime.now() - timedelta(days=days)
        recent_runs = [
            run for run in all_runs
            if run.started_at and run.started_at >= cutoff
        ]

        # Calculate metrics
        metrics = self._calculate_metrics(all_runs, recent_runs)

        # Determine health status
        health_status = self._determine_health_status(metrics)

        # Identify issues
        issues = self._identify_issues(metrics, all_runs)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, issues)

        # Get last run time
        last_run = None
        if all_runs:
            last_run = max(
                (run.started_at for run in all_runs if run.started_at),
                default=None
            )

        return HealthReport(
            agent_name=self.storage_path.name,
            storage_path=self.storage_path,
            metrics=metrics,
            health_status=health_status,
            issues=issues,
            recommendations=recommendations,
            last_run=last_run,
        )

    def _get_all_runs(self) -> list[Run]:
        """Get all runs from storage."""
        runs = []
        runs_dir = self.storage_path / "runs"

        if not runs_dir.exists():
            return runs

        for run_file in runs_dir.glob("*.json"):
            try:
                with open(run_file) as f:
                    run_data = json.load(f)
                    runs.append(Run.model_validate(run_data))
            except Exception:
                # Skip invalid run files
                continue

        # Sort by started_at (most recent first)
        runs.sort(
            key=lambda r: r.started_at if r.started_at else datetime.min,
            reverse=True
        )

        return runs

    def _calculate_metrics(
        self,
        all_runs: list[Run],
        recent_runs: list[Run],
    ) -> HealthMetrics:
        """Calculate health metrics from runs."""
        metrics = HealthMetrics()

        metrics.total_runs = len(all_runs)
        metrics.recent_runs = len(recent_runs)

        if not all_runs:
            return metrics

        # Success/failure counts
        successful = [r for r in all_runs if r.status == RunStatus.COMPLETED]
        failed = [r for r in all_runs if r.status == RunStatus.FAILED]

        metrics.successful_runs = len(successful)
        metrics.failed_runs = len(failed)
        if metrics.total_runs > 0:
            metrics.success_rate = len(successful) / metrics.total_runs
        else:
            metrics.success_rate = 0.0

        # Recent success rate
        recent_successful = [r for r in recent_runs if r.status == RunStatus.COMPLETED]
        metrics.recent_success_rate = (
            len(recent_successful) / len(recent_runs) if recent_runs else 0.0
        )

        # Duration metrics (use Run.duration_ms computed property)
        durations = [
            r.duration_ms
            for r in all_runs
            if r.duration_ms > 0
        ]
        if durations:
            metrics.total_duration_ms = sum(durations)
            metrics.avg_duration_ms = sum(durations) / len(durations)

        # Decision metrics
        decision_counts = [
            r.metrics.total_decisions
            for r in all_runs
            if r.metrics and r.metrics.total_decisions > 0
        ]
        if decision_counts:
            metrics.avg_decisions = sum(decision_counts) / len(decision_counts)

        # Cost metrics (not directly in RunMetrics, skip for now)
        # Costs would need to be calculated from decisions/outcomes
        metrics.total_cost_usd = 0.0  # Placeholder - would need to calculate from decisions

        # Status distribution
        for run in all_runs:
            status = run.status.value if run.status else "unknown"
            metrics.status_distribution[status] = metrics.status_distribution.get(status, 0) + 1

        # Common errors
        for run in failed:
            if run.problems:
                for problem in run.problems:
                    error_key = problem.description[:100]  # Truncate long errors
                    metrics.common_errors[error_key] = metrics.common_errors.get(error_key, 0) + 1

        # Node usage
        for run in all_runs:
            if run.metrics and run.metrics.nodes_executed:
                for node_id in run.metrics.nodes_executed:
                    metrics.node_usage[node_id] = metrics.node_usage.get(node_id, 0) + 1

        return metrics

    def _determine_health_status(self, metrics: HealthMetrics) -> str:
        """Determine overall health status."""
        if metrics.total_runs == 0:
            return "unknown"

        # Check success rate
        if metrics.success_rate < 0.5:
            return "unhealthy"
        elif metrics.success_rate < 0.8:
            return "degraded"
        else:
            return "healthy"

    def _identify_issues(self, metrics: HealthMetrics, runs: list[Run]) -> list[str]:
        """Identify potential issues."""
        issues = []

        # Low success rate
        if metrics.success_rate < 0.8 and metrics.total_runs >= 5:
            issues.append(f"Low success rate: {metrics.success_rate:.1%} (target: >80%)")

        # Recent degradation
        if metrics.recent_runs >= 3:
            if metrics.recent_success_rate < metrics.success_rate - 0.2:
                issues.append(
                    f"Recent performance degradation: "
                    f"{metrics.recent_success_rate:.1%} vs overall {metrics.success_rate:.1%}"
                )

        # High failure rate
        if metrics.failed_runs > metrics.successful_runs and metrics.total_runs >= 10:
            issues.append("More failures than successes - agent may need debugging")

        # No recent runs
        if metrics.recent_runs == 0 and metrics.total_runs > 0:
            issues.append("No runs in the last 24 hours - agent may be inactive")

        # High cost
        if metrics.total_cost_usd > 10.0:
            issues.append(f"High total cost: ${metrics.total_cost_usd:.2f}")

        # Common errors
        if metrics.common_errors:
            top_error = max(metrics.common_errors.items(), key=lambda x: x[1])
            if top_error[1] >= 3:
                error_msg = f"Recurring error: {top_error[0][:80]}... ({top_error[1]} occurrences)"
                issues.append(error_msg)

        return issues

    def _generate_recommendations(
        self,
        metrics: HealthMetrics,
        issues: list[str],
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Success rate recommendations
        if metrics.success_rate < 0.8:
            recommendations.append("Review failed runs to identify common failure patterns")
            recommendations.append("Consider improving error handling in agent nodes")

        # Performance recommendations
        if metrics.avg_duration_ms > 30000:  # > 30 seconds
            recommendations.append(
                "Average execution time is high - consider optimizing slow nodes"
            )

        # Cost recommendations
        if metrics.total_cost_usd > 5.0 and metrics.avg_decisions > 10:
            recommendations.append("High cost per execution - consider optimizing LLM usage")

        # Error recommendations
        if metrics.common_errors:
            recommendations.append("Address recurring errors to improve reliability")

        # Node usage recommendations
        unused_nodes = []
        if len(metrics.node_usage) < 5:  # Assuming agent has more nodes
            recommendations.append("Some nodes may be underutilized - review workflow")

        # General recommendations
        if metrics.total_runs < 5:
            recommendations.append("Run more tests to get reliable health metrics")

        return recommendations
