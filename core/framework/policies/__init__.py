"""Policy-native guardrails for Aden Hive agent framework.

This package provides a policy-based guardrails system that integrates
with the Hive agent framework. Policies evaluate agent actions at key
interception points and return structured decisions.

Key components:
- PolicyEngine: Orchestrates policy evaluation
- Policy: Protocol/base class for defining policies
- PolicyEvent: Events that policies evaluate
- PolicyDecision: Decisions returned by policies
- ToolInterceptor: Creates policy events from tool calls

Built-in policies:
- HighRiskToolGatingPolicy: Require confirmation for high-risk tools
- DomainAllowlistPolicy: Control allowed network domains
- BudgetLimitPolicy: Enforce resource budgets
- InjectionGuardPolicy: Detect prompt injection attempts

Example:
    from framework.policies import (
        PolicyEngine,
        PolicyEvent,
        PolicyEventType,
        HighRiskToolGatingPolicy,
        DomainAllowlistPolicy,
        BudgetLimitPolicy,
        InjectionGuardPolicy,
    )

    # Create engine and register policies
    engine = PolicyEngine()
    engine.register_policy(HighRiskToolGatingPolicy())
    engine.register_policy(DomainAllowlistPolicy())
    engine.register_policy(BudgetLimitPolicy())
    engine.register_policy(InjectionGuardPolicy())

    # Create an event
    event = PolicyEvent.create(
        event_type=PolicyEventType.TOOL_CALL,
        payload={"tool_name": "file_delete", "args": {"path": "/tmp/x"}},
        execution_id="exec-123",
    )

    # Evaluate
    result = await engine.evaluate(event)
    print(f"Action: {result.final_action}")
"""

from framework.policies.base import BasePolicy, Policy
from framework.policies.builtin import (
    AllowlistMode,
    BudgetConfig,
    BudgetLimitPolicy,
    BudgetMode,
    DomainAllowlistPolicy,
    HighRiskToolGatingPolicy,
    InjectionGuardPolicy,
    InjectionMode,
)
from framework.policies.decisions import PolicyAction, PolicyDecision, Severity
from framework.policies.engine import AggregatedDecision, PolicyEngine
from framework.policies.events import PolicyEvent, PolicyEventType
from framework.policies.exceptions import (
    ConfirmationRequiredError,
    GuardrailsError,
    PolicyConfigurationError,
    PolicyRegistrationError,
    PolicyViolationError,
)
from framework.policies.interceptors import ToolInterceptor

__version__ = "0.1.0"

__all__ = [
    # Core
    "PolicyEngine",
    "AggregatedDecision",
    # Events
    "PolicyEvent",
    "PolicyEventType",
    # Decisions
    "PolicyDecision",
    "PolicyAction",
    "Severity",
    # Policies - Base
    "Policy",
    "BasePolicy",
    # Policies - Tool Gating
    "HighRiskToolGatingPolicy",
    # Policies - Domain Allowlist
    "DomainAllowlistPolicy",
    "AllowlistMode",
    # Policies - Budget Limits
    "BudgetLimitPolicy",
    "BudgetConfig",
    "BudgetMode",
    # Policies - Injection Guard
    "InjectionGuardPolicy",
    "InjectionMode",
    # Interceptors
    "ToolInterceptor",
    # Exceptions
    "GuardrailsError",
    "PolicyViolationError",
    "PolicyConfigurationError",
    "PolicyRegistrationError",
    "ConfirmationRequiredError",
    # Version
    "__version__",
]
