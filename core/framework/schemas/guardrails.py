"""
Guardrails Schema - Runtime policy enforcement for agent decisions.

Guardrails provide a safety layer that validates decisions before and after
execution, preventing common failure modes like:
- Tool call loops (same tool failing repeatedly)
- Token budget overruns
- Forbidden tool usage in specific environments
- Excessive retries

This integrates with the Eval System to record violations as Run.problems.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailAction(str, Enum):
    """Action to take when a guardrail condition is triggered."""

    ALLOW = "allow"  # Proceed with the decision
    WARN = "warn"  # Allow but record a warning in Run.problems
    BLOCK = "block"  # Prevent the decision and record a critical problem


class GuardrailSeverity(str, Enum):
    """Severity level for guardrail violations."""

    MINOR = "minor"
    WARNING = "warning"
    CRITICAL = "critical"


class ToolGuardConfig(BaseModel):
    """
    Configuration for tool-specific guardrails.

    Controls how often a tool can be called and whether it's allowed
    in the current environment.
    """

    tool_name: str = Field(description="Name of the tool to guard")
    max_calls_per_run: int | None = Field(
        default=None,
        description="Maximum times this tool can be called in a single run",
    )
    max_consecutive_failures: int = Field(
        default=3,
        description="Max consecutive failures before blocking (loop detection)",
    )
    forbidden: bool = Field(
        default=False,
        description="If True, any attempt to call this tool is blocked",
    )
    forbidden_reason: str = Field(
        default="",
        description="Explanation for why this tool is forbidden",
    )

    model_config = {"extra": "allow"}


class TokenGuardConfig(BaseModel):
    """
    Configuration for token budget guardrails.

    Enforces limits on LLM token usage to prevent cost overruns
    and runaway executions.
    """

    max_tokens_per_decision: int | None = Field(
        default=None,
        description="Maximum tokens for a single decision (WARN if exceeded)",
    )
    max_tokens_per_run: int | None = Field(
        default=None,
        description="Maximum total tokens for an entire run",
    )
    warn_threshold_percent: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Warn when this percentage of budget is reached",
    )

    model_config = {"extra": "allow"}


class RetryGuardConfig(BaseModel):
    """
    Configuration for retry behavior guardrails.

    Prevents infinite retry loops and enforces backoff policies.
    """

    max_retries_per_node: int = Field(
        default=3,
        description="Maximum retries for a single node before failing",
    )
    max_retries_per_run: int = Field(
        default=10,
        description="Maximum total retries across all nodes in a run",
    )

    model_config = {"extra": "allow"}


class LatencyGuardConfig(BaseModel):
    """
    Configuration for latency guardrails.

    Flags slow decisions that might indicate problems.
    """

    warn_latency_ms: int = Field(
        default=30000,
        description="Warn if a single decision takes longer than this (ms)",
    )
    max_latency_ms: int | None = Field(
        default=None,
        description="Block decisions that exceed this latency",
    )

    model_config = {"extra": "allow"}


class GuardrailConfig(BaseModel):
    """
    Complete guardrail configuration for an agent or run.

    This can be defined:
    - Per agent (in agent.json or programmatically)
    - Per environment (dev/staging/prod may have different rules)
    - Per run (override for specific executions)
    """

    enabled: bool = Field(
        default=True,
        description="Master switch to enable/disable all guardrails",
    )

    # Tool-specific rules
    tools: list[ToolGuardConfig] = Field(
        default_factory=list,
        description="Tool-specific guardrail configurations",
    )

    # Token budget rules
    tokens: TokenGuardConfig | None = Field(
        default=None,
        description="Token budget enforcement",
    )

    # Retry rules
    retries: RetryGuardConfig | None = Field(
        default=None,
        description="Retry behavior enforcement",
    )

    # Latency rules
    latency: LatencyGuardConfig | None = Field(
        default=None,
        description="Latency monitoring and enforcement",
    )

    # Global forbidden tools (convenience for environment-based blocking)
    forbidden_tools: list[str] = Field(
        default_factory=list,
        description="List of tool names that are completely forbidden",
    )

    # Default action for unspecified violations
    default_action: GuardrailAction = Field(
        default=GuardrailAction.WARN,
        description="Default action when a guardrail is triggered",
    )

    model_config = {"extra": "allow"}

    def get_tool_config(self, tool_name: str) -> ToolGuardConfig | None:
        """Get configuration for a specific tool."""
        for config in self.tools:
            if config.tool_name == tool_name:
                return config
        return None

    def is_tool_forbidden(self, tool_name: str) -> tuple[bool, str]:
        """
        Check if a tool is forbidden.

        Returns:
            Tuple of (is_forbidden, reason)
        """
        # Check global forbidden list
        if tool_name in self.forbidden_tools:
            return True, f"Tool '{tool_name}' is in the forbidden tools list"

        # Check tool-specific config
        tool_config = self.get_tool_config(tool_name)
        if tool_config and tool_config.forbidden:
            reason = tool_config.forbidden_reason or f"Tool '{tool_name}' is forbidden"
            return True, reason

        return False, ""


class GuardrailViolation(BaseModel):
    """
    A single guardrail violation that occurred.

    This is recorded and can be used to create Run.problems.
    """

    id: str = Field(description="Unique identifier for this violation")
    guardrail_type: str = Field(
        description="Type of guardrail: 'tool', 'token', 'retry', 'latency'"
    )
    action: GuardrailAction = Field(description="Action taken")
    severity: GuardrailSeverity = Field(description="Severity of the violation")
    description: str = Field(description="Human-readable description")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the violation",
    )
    suggested_fix: str | None = Field(
        default=None,
        description="Suggested fix for this violation",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"extra": "allow"}


class GuardrailResult(BaseModel):
    """
    Result of a guardrail check.

    Returned by GuardrailEngine.check_before_decision() and
    check_after_decision() methods.
    """

    action: GuardrailAction = Field(
        default=GuardrailAction.ALLOW,
        description="Action to take",
    )
    allowed: bool = Field(
        default=True,
        description="Whether the decision should proceed",
    )
    violations: list[GuardrailViolation] = Field(
        default_factory=list,
        description="List of violations detected",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages to log",
    )

    model_config = {"extra": "allow"}

    @property
    def has_violations(self) -> bool:
        """Check if any violations were detected."""
        return len(self.violations) > 0

    @property
    def blocked(self) -> bool:
        """Check if the decision should be blocked."""
        return self.action == GuardrailAction.BLOCK


class DecisionPlan(BaseModel):
    """
    A proposed decision before execution.

    This is passed to check_before_decision() so guardrails can
    evaluate the plan before it's executed.
    """

    node_id: str = Field(description="Node making the decision")
    intent: str = Field(description="What the decision aims to accomplish")
    tool_name: str | None = Field(
        default=None,
        description="Name of tool being called (if applicable)",
    )
    tool_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the tool call",
    )
    estimated_tokens: int = Field(
        default=0,
        description="Estimated token usage for this decision",
    )

    model_config = {"extra": "allow"}


class RunContext(BaseModel):
    """
    Current state of a run for guardrail evaluation.

    Provides the context needed to evaluate guardrails against
    cumulative run statistics.
    """

    run_id: str = Field(description="Current run ID")
    goal_id: str = Field(description="Goal being pursued")
    total_tokens_used: int = Field(
        default=0,
        description="Total tokens used so far in this run",
    )
    total_decisions: int = Field(
        default=0,
        description="Total decisions made in this run",
    )
    total_retries: int = Field(
        default=0,
        description="Total retries across all nodes",
    )
    tool_call_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of calls per tool in this run",
    )
    tool_failure_streaks: dict[str, int] = Field(
        default_factory=dict,
        description="Consecutive failures per tool",
    )
    node_retry_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Retry count per node",
    )

    model_config = {"extra": "allow"}

    def increment_tool_call(self, tool_name: str) -> int:
        """Increment and return the call count for a tool."""
        count = self.tool_call_counts.get(tool_name, 0) + 1
        self.tool_call_counts[tool_name] = count
        return count

    def record_tool_failure(self, tool_name: str) -> int:
        """Record a tool failure and return consecutive failure count."""
        streak = self.tool_failure_streaks.get(tool_name, 0) + 1
        self.tool_failure_streaks[tool_name] = streak
        return streak

    def reset_tool_failure_streak(self, tool_name: str) -> None:
        """Reset the failure streak for a tool (on success)."""
        self.tool_failure_streaks[tool_name] = 0

    def increment_node_retry(self, node_id: str) -> int:
        """Increment and return the retry count for a node."""
        count = self.node_retry_counts.get(node_id, 0) + 1
        self.node_retry_counts[node_id] = count
        self.total_retries += 1
        return count
