"""Injection guard policy for detecting prompt injection attempts.

This policy analyzes tool outputs and other untrusted content for
patterns that may indicate prompt injection attacks, where malicious
content attempts to hijack agent behavior.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from framework.policies.base import BasePolicy
from framework.policies.decisions import PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType


class InjectionMode(Enum):
    """Operating modes for injection detection."""

    PERMISSIVE = "permissive"
    """Flag suspicious patterns but allow (SUGGEST)."""

    BALANCED = "balanced"
    """Require confirmation for high-confidence detections."""

    STRICT = "strict"
    """Block any detected injection patterns."""


# Patterns that may indicate prompt injection attempts
# These are intentionally broad to catch variations
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)", "instruction_override", Severity.HIGH),
    (r"disregard\s+(all\s+)?(previous|prior|above)", "instruction_override", Severity.HIGH),
    (r"forget\s+(everything|all|what)\s+(you|i)\s+(said|told|instructed)", "instruction_override", Severity.HIGH),
    (r"new\s+instructions?:", "instruction_override", Severity.MEDIUM),
    (r"system\s*:\s*you\s+are", "role_injection", Severity.HIGH),

    # Role/persona hijacking
    (r"you\s+are\s+now\s+(a|an|the)", "role_injection", Severity.MEDIUM),
    (r"act\s+as\s+(a|an|if|though)", "role_injection", Severity.LOW),
    (r"pretend\s+(to\s+be|you\s+are)", "role_injection", Severity.MEDIUM),
    (r"from\s+now\s+on,?\s+you", "role_injection", Severity.MEDIUM),

    # Jailbreak attempts
    (r"developer\s+mode", "jailbreak", Severity.HIGH),
    (r"dan\s+mode", "jailbreak", Severity.HIGH),
    (r"jailbreak", "jailbreak", Severity.CRITICAL),
    (r"bypass\s+(safety|security|filter|restriction)", "jailbreak", Severity.HIGH),

    # Data exfiltration attempts
    (r"(send|post|upload|transmit)\s+(to|this|the|all)\s+(url|endpoint|server|webhook)", "exfiltration", Severity.HIGH),
    (r"curl\s+(-X\s+POST|--data)", "exfiltration", Severity.MEDIUM),
    (r"base64\s+encode", "obfuscation", Severity.LOW),

    # Hidden instruction markers
    (r"\[INST\]", "hidden_instruction", Severity.MEDIUM),
    (r"<\|im_start\|>", "hidden_instruction", Severity.MEDIUM),
    (r"###\s*(Human|Assistant|System):", "hidden_instruction", Severity.MEDIUM),
    (r"```system", "hidden_instruction", Severity.MEDIUM),

    # Encoded/obfuscated commands
    (r"eval\s*\(", "code_execution", Severity.HIGH),
    (r"exec\s*\(", "code_execution", Severity.HIGH),
    (r"__import__", "code_execution", Severity.HIGH),

    # Privilege escalation
    (r"sudo\s+", "privilege_escalation", Severity.HIGH),
    (r"chmod\s+[0-7]{3,4}", "privilege_escalation", Severity.MEDIUM),
    (r"rm\s+-rf\s+/", "destructive_command", Severity.CRITICAL),
]

# Benign patterns that might trigger false positives
FALSE_POSITIVE_CONTEXTS = [
    r"how\s+to\s+prevent",
    r"example\s+of",
    r"what\s+is\s+(a\s+)?prompt\s+injection",
    r"security\s+(research|testing|audit)",
    r"documentation",
    r"tutorial",
]


@dataclass
class InjectionGuardPolicy(BasePolicy):
    """Policy that detects potential prompt injection in tool outputs.

    This policy analyzes content from tool results and other untrusted
    sources for patterns that may indicate prompt injection attacks.

    Operating modes:
    - permissive: Flag suspicious patterns but allow (SUGGEST)
    - balanced: Require confirmation for high-confidence detections
    - strict: Block any detected injection patterns

    The policy labels tool outputs as "data" rather than "instructions"
    by flagging content that appears to contain instruction-like patterns.

    Attributes:
        mode: Operating mode (permissive, balanced, strict)
        custom_patterns: Additional patterns to detect
        ignore_patterns: Patterns to ignore (reduce false positives)
        min_severity: Minimum severity to act on

    Example:
        policy = InjectionGuardPolicy(
            mode=InjectionMode.BALANCED,
            custom_patterns=[
                (r"my_custom_attack", "custom", Severity.HIGH),
            ],
        )
        engine.register_policy(policy)
    """

    mode: InjectionMode = InjectionMode.PERMISSIVE
    custom_patterns: list[tuple[str, str, Severity]] = field(default_factory=list)
    ignore_patterns: list[str] = field(
        default_factory=lambda: FALSE_POSITIVE_CONTEXTS.copy()
    )
    min_severity: Severity = Severity.LOW

    # Policy metadata
    _id: str = "injection-guard"
    _name: str = "Injection Guard"
    _description: str = (
        "Detects potential prompt injection attempts in tool outputs "
        "and other untrusted content."
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
        return [PolicyEventType.TOOL_RESULT]

    def _get_all_patterns(self) -> list[tuple[str, str, Severity]]:
        """Get all detection patterns including custom ones."""
        return INJECTION_PATTERNS + self.custom_patterns

    def _extract_content(self, payload: dict) -> str:
        """Extract text content from tool result payload."""
        result = payload.get("result", "")

        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Try to extract text from common keys
            for key in ["text", "content", "body", "output", "data", "message"]:
                if key in result and isinstance(result[key], str):
                    return str(result[key])
            # Fall back to string representation
            return str(result)
        elif isinstance(result, list):
            # Join list items
            return " ".join(str(item) for item in result)
        else:
            return str(result)

    def _is_false_positive_context(self, content: str) -> bool:
        """Check if content appears to be in a benign context."""
        content_lower = content.lower()
        for pattern in self.ignore_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False

    def _severity_value(self, severity: Severity) -> int:
        """Convert severity to numeric value for comparison."""
        return {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }[severity]

    def _detect_patterns(
        self, content: str
    ) -> list[tuple[str, str, Severity, str]]:
        """Detect injection patterns in content.

        Returns:
            List of (pattern, category, severity, matched_text) tuples
        """
        detections = []
        content_lower = content.lower()

        for pattern, category, severity in self._get_all_patterns():
            # Skip if below minimum severity
            if self._severity_value(severity) < self._severity_value(self.min_severity):
                continue

            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                matched_text = match.group(0)
                detections.append((pattern, category, severity, matched_text))

        return detections

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate tool output for injection patterns.

        Args:
            event: The TOOL_RESULT event to evaluate

        Returns:
            PolicyDecision based on injection detection
        """
        tool_name = event.payload.get("tool_name", "unknown")
        content = self._extract_content(event.payload)

        if not content:
            return PolicyDecision.allow(
                policy_id=self.id,
                reason="No content to analyze",
                metadata={"tool_name": tool_name},
            )

        # Check for false positive context
        if self._is_false_positive_context(content):
            return PolicyDecision.allow(
                policy_id=self.id,
                reason="Content appears to be in educational/documentation context",
                metadata={"tool_name": tool_name, "false_positive_context": True},
            )

        # Detect patterns
        detections = self._detect_patterns(content)

        if not detections:
            return PolicyDecision.allow(
                policy_id=self.id,
                reason="No injection patterns detected",
                metadata={"tool_name": tool_name},
            )

        # Aggregate detections
        categories = list(set(d[1] for d in detections))
        # Find max severity using helper to compare enum values
        max_severity = max(
            (d[2] for d in detections),
            key=lambda s: self._severity_value(s)
        )
        matched_texts = [d[3][:50] for d in detections[:3]]  # First 3, truncated

        metadata: dict[str, Any] = {
            "tool_name": tool_name,
            "detection_count": len(detections),
            "categories": categories,
            "max_severity": max_severity.value,
            "matched_samples": matched_texts,
        }

        reason = (
            f"Detected {len(detections)} potential injection pattern(s) "
            f"in output from '{tool_name}': {', '.join(categories)}"
        )

        # Decide action based on mode and severity
        if self.mode == InjectionMode.PERMISSIVE:
            return PolicyDecision.suggest(
                policy_id=self.id,
                reason=reason + ". Review tool output before using.",
                severity=max_severity,
                tags=["injection", "security"] + categories,
                metadata=metadata,
            )

        elif self.mode == InjectionMode.BALANCED:
            if max_severity in (Severity.HIGH, Severity.CRITICAL):
                return PolicyDecision.require_confirm(
                    policy_id=self.id,
                    reason=reason + ". Confirm before proceeding.",
                    severity=max_severity,
                    tags=["injection", "security", "requires-confirmation"] + categories,
                    metadata=metadata,
                )
            else:
                return PolicyDecision.suggest(
                    policy_id=self.id,
                    reason=reason + ". Low confidence - review if concerned.",
                    severity=max_severity,
                    tags=["injection", "security"] + categories,
                    metadata=metadata,
                )

        else:  # STRICT
            if max_severity in (Severity.HIGH, Severity.CRITICAL):
                return PolicyDecision.block(
                    policy_id=self.id,
                    reason=reason + ". Blocked in strict mode.",
                    severity=max_severity,
                    tags=["injection", "security", "blocked"] + categories,
                    metadata=metadata,
                )
            else:
                return PolicyDecision.require_confirm(
                    policy_id=self.id,
                    reason=reason + ". Confirm to proceed in strict mode.",
                    severity=max_severity,
                    tags=["injection", "security", "requires-confirmation"] + categories,
                    metadata=metadata,
                )

    def add_pattern(
        self, pattern: str, category: str, severity: Severity = Severity.MEDIUM
    ) -> None:
        """Add a custom detection pattern.

        Args:
            pattern: Regex pattern to detect
            category: Category name for the pattern
            severity: Severity level for detections
        """
        self.custom_patterns.append((pattern, category, severity))

    def add_ignore_pattern(self, pattern: str) -> None:
        """Add a pattern to reduce false positives.

        Args:
            pattern: Regex pattern for benign contexts
        """
        if pattern not in self.ignore_patterns:
            self.ignore_patterns.append(pattern)

    def set_min_severity(self, severity: Severity) -> None:
        """Set minimum severity threshold for detections.

        Args:
            severity: Minimum severity to report
        """
        self.min_severity = severity
