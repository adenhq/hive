"""High-risk tool gating policy.

This policy requires human confirmation before executing tools
that perform destructive, sensitive, or irreversible actions.
"""

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Optional

from framework.policies.base import BasePolicy
from framework.policies.decisions import PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType


# Default patterns for high-risk tools
DEFAULT_HIGH_RISK_PATTERNS = [
    # Destructive operations
    "*_delete",
    "*_remove",
    "*_drop",
    "*_truncate",
    "*_destroy",
    # Write operations
    "*_write",
    "*_create",
    "*_update",
    "*_modify",
    "*_set",
    # Execution
    "*_execute",
    "*_run",
    "*_eval",
    "shell_*",
    "bash_*",
    "exec_*",
    # Network/communication
    "*_send",
    "*_post",
    "*_email",
    "*_notify",
    "*_publish",
    # Credentials/auth (match both *_credential* and credential_*)
    "*credential*",
    "*secret*",
    "*password*",
    "token_*",
    "*_token",
    "*_key",
    "key_*",
    "*auth*",
    # Specific high-risk tools
    "file_write",
    "file_delete",
    "database_query",
    "http_request",
    "subprocess_run",
]

# Default patterns for always-allowed (safe) tools
DEFAULT_SAFE_PATTERNS = [
    "*_read",
    "*_get",
    "*_list",
    "*_search",
    "*_find",
    "*_fetch",
    "*_query",  # Read-only queries
    "*_describe",
    "*_info",
    "*_status",
    "*_check",
    "*_validate",
    "*_parse",
    "*_format",
    "*_convert",
]


@dataclass
class HighRiskToolGatingPolicy(BasePolicy):
    """Policy that requires confirmation for high-risk tool calls.

    This policy evaluates tool calls against configurable patterns
    to determine if human confirmation is required. Tools matching
    high-risk patterns trigger REQUIRE_CONFIRM, while tools matching
    safe patterns are allowed.

    The policy uses glob-style patterns (fnmatch) for matching tool names.

    Attributes:
        high_risk_patterns: Patterns that trigger REQUIRE_CONFIRM
        safe_patterns: Patterns that are always allowed
        default_action: Action for tools matching neither pattern
        severity: Severity level for REQUIRE_CONFIRM decisions

    Example:
        policy = HighRiskToolGatingPolicy(
            high_risk_patterns=["*_delete", "*_execute"],
            safe_patterns=["*_read", "*_list"],
        )
        engine.register_policy(policy)
    """

    high_risk_patterns: list[str] = field(
        default_factory=lambda: DEFAULT_HIGH_RISK_PATTERNS.copy()
    )
    safe_patterns: list[str] = field(
        default_factory=lambda: DEFAULT_SAFE_PATTERNS.copy()
    )
    default_action: str = "allow"  # "allow", "confirm", or "block"
    severity: Severity = Severity.HIGH

    # Policy metadata
    _id: str = "high-risk-tool-gating"
    _name: str = "High-Risk Tool Gating"
    _description: str = (
        "Requires human confirmation for tools that perform destructive, "
        "sensitive, or irreversible actions."
    )

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def event_types(self) -> list[PolicyEventType]:
        return [PolicyEventType.TOOL_CALL]

    def _matches_pattern(self, tool_name: str, patterns: list[str]) -> bool:
        """Check if tool name matches any of the given patterns.

        Args:
            tool_name: The tool name to check
            patterns: List of glob patterns to match against

        Returns:
            True if the tool matches any pattern
        """
        tool_lower = tool_name.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(tool_lower, pattern.lower()):
                return True
        return False

    def _get_matching_pattern(
        self, tool_name: str, patterns: list[str]
    ) -> Optional[str]:
        """Get the first pattern that matches the tool name.

        Args:
            tool_name: The tool name to check
            patterns: List of glob patterns to match against

        Returns:
            The first matching pattern, or None
        """
        tool_lower = tool_name.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(tool_lower, pattern.lower()):
                return pattern
        return None

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate a tool call event.

        Args:
            event: The TOOL_CALL event to evaluate

        Returns:
            PolicyDecision indicating ALLOW or REQUIRE_CONFIRM
        """
        tool_name = event.payload.get("tool_name", "")
        args = event.payload.get("args", {})

        # Check safe patterns first (allow-list)
        if self._matches_pattern(tool_name, self.safe_patterns):
            return PolicyDecision.allow(
                policy_id=self.id,
                reason=f"Tool '{tool_name}' matches safe pattern",
                metadata={
                    "tool_name": tool_name,
                    "matched_pattern": self._get_matching_pattern(
                        tool_name, self.safe_patterns
                    ),
                },
            )

        # Check high-risk patterns
        if self._matches_pattern(tool_name, self.high_risk_patterns):
            matched_pattern = self._get_matching_pattern(
                tool_name, self.high_risk_patterns
            )
            return PolicyDecision.require_confirm(
                policy_id=self.id,
                reason=(
                    f"Tool '{tool_name}' is high-risk (matches '{matched_pattern}'). "
                    f"Human confirmation required."
                ),
                severity=self.severity,
                tags=["high-risk-tool", "requires-confirmation"],
                metadata={
                    "tool_name": tool_name,
                    "args": args,
                    "matched_pattern": matched_pattern,
                },
            )

        # Default action for unmatched tools
        if self.default_action == "confirm":
            return PolicyDecision.require_confirm(
                policy_id=self.id,
                reason=(
                    f"Tool '{tool_name}' requires confirmation "
                    f"(no explicit safe pattern match)"
                ),
                severity=Severity.MEDIUM,
                tags=["unknown-tool", "requires-confirmation"],
                metadata={"tool_name": tool_name, "args": args},
            )
        elif self.default_action == "block":
            return PolicyDecision.block(
                policy_id=self.id,
                reason=f"Tool '{tool_name}' is not in the allowed list",
                severity=Severity.HIGH,
                tags=["blocked-tool"],
                metadata={"tool_name": tool_name, "args": args},
            )
        else:  # default: allow
            return PolicyDecision.allow(
                policy_id=self.id,
                reason=f"Tool '{tool_name}' does not match any high-risk pattern",
                metadata={"tool_name": tool_name},
            )

    def add_high_risk_pattern(self, pattern: str) -> None:
        """Add a pattern to the high-risk list.

        Args:
            pattern: Glob pattern to add
        """
        if pattern not in self.high_risk_patterns:
            self.high_risk_patterns.append(pattern)

    def add_safe_pattern(self, pattern: str) -> None:
        """Add a pattern to the safe list.

        Args:
            pattern: Glob pattern to add
        """
        if pattern not in self.safe_patterns:
            self.safe_patterns.append(pattern)

    def remove_high_risk_pattern(self, pattern: str) -> None:
        """Remove a pattern from the high-risk list.

        Args:
            pattern: Glob pattern to remove
        """
        if pattern in self.high_risk_patterns:
            self.high_risk_patterns.remove(pattern)

    def remove_safe_pattern(self, pattern: str) -> None:
        """Remove a pattern from the safe list.

        Args:
            pattern: Glob pattern to remove
        """
        if pattern in self.safe_patterns:
            self.safe_patterns.remove(pattern)
