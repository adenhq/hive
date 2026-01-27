from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Set


class GuardrailViolation(Exception):
    """Raised when a guardrail blocks an action."""


TextFilter = Callable[[str], str]


@dataclass
class GuardrailsConfig:
    """
    Configuration for system-level guardrails.

    This is intentionally minimal and framework-agnostic so it can be used
    from the runtime, orchestrator, tools, or external hosts.
    """

    # Tool-level controls
    allowed_tools: Optional[Set[str]] = None
    blocked_tools: Set[str] = field(default_factory=set)

    # Simple budget controls (host is responsible for calling check_budget)
    max_cost_usd: Optional[float] = None

    # Optional text filters (can be used for prompt / response filtering)
    input_filters: Iterable[TextFilter] = field(default_factory=list)
    output_filters: Iterable[TextFilter] = field(default_factory=list)


class GuardrailsManager:
    """
    Central coordinator for guardrails.

    Responsibilities:
    - Enforce simple tool allow/deny lists
    - Track and enforce a coarse-grained budget
    - Provide hooks for content filtering (pre/post LLM or tool calls)

    This class does NOT talk directly to specific LLM providers, sandboxes,
    or tools. Instead, it exposes small methods that other parts of the
    framework can call at the right points in their workflows.
    """

    def __init__(self, config: Optional[GuardrailsConfig] = None) -> None:
        self.config = config or GuardrailsConfig()
        self._cost_spent_usd: float = 0.0

    # ------------------------------------------------------------------
    # Tool guardrails
    # ------------------------------------------------------------------
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Return True if a tool is allowed to execute under current policy.

        Policy:
        - If allowed_tools is set: tool must be in that set.
        - If blocked_tools contains the tool: it is always blocked.
        - Otherwise: allowed.
        """
        # Deny if explicitly blocked
        if tool_name in self.config.blocked_tools:
            return False

        # If there is an allow-list, tool must be present
        if self.config.allowed_tools is not None:
            return tool_name in self.config.allowed_tools

        # Default allow
        return True

    def ensure_tool_allowed(self, tool_name: str) -> None:
        """
        Raise GuardrailViolation if the tool is not allowed.
        """
        if not self.is_tool_allowed(tool_name):
            raise GuardrailViolation(f"Tool '{tool_name}' is not allowed by guardrails policy.")

    # ------------------------------------------------------------------
    # Budget / cost guardrails
    # ------------------------------------------------------------------
    @property
    def cost_spent_usd(self) -> float:
        return self._cost_spent_usd

    def check_budget(self, cost_delta_usd: float) -> None:
        """
        Check whether adding `cost_delta_usd` would exceed the configured budget.

        If max_cost_usd is not set, this is a no-op other than accumulating cost.
        """
        if cost_delta_usd < 0:
            # Do not support negative adjustment semantics here
            raise ValueError("cost_delta_usd must be non-negative")

        new_total = self._cost_spent_usd + cost_delta_usd

        if self.config.max_cost_usd is not None and new_total > self.config.max_cost_usd:
            raise GuardrailViolation(
                f"Budget exceeded: attempted {new_total:.4f} USD "
                f"with max {self.config.max_cost_usd:.4f} USD."
            )

        self._cost_spent_usd = new_total

    # ------------------------------------------------------------------
    # Content filtering guardrails
    # ------------------------------------------------------------------
    def filter_input_text(self, text: str) -> str:
        """
        Apply all configured input filters in order.
        """
        for flt in self.config.input_filters:
            text = flt(text)
        return text

    def filter_output_text(self, text: str) -> str:
        """
        Apply all configured output filters in order.
        """
        for flt in self.config.output_filters:
            text = flt(text)
        return text

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    @classmethod
    def with_tool_allowlist(cls, tools: Iterable[str]) -> "GuardrailsManager":
        """
        Convenience constructor for a manager with an allow-list-only policy.
        """
        config = GuardrailsConfig(allowed_tools=set(tools))
        return cls(config=config)

    @classmethod
    def with_budget(cls, max_cost_usd: float) -> "GuardrailsManager":
        """
        Convenience constructor for a manager with only a budget limit.
        """
        config = GuardrailsConfig(max_cost_usd=max_cost_usd)
        return cls(config=config)

