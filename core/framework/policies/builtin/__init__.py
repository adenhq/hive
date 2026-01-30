"""Built-in policies for common guardrail patterns.

These policies provide out-of-the-box protection for common
agent safety concerns.

Available policies:
- HighRiskToolGatingPolicy: Require confirmation for high-risk tools
- DomainAllowlistPolicy: Control allowed network domains
- BudgetLimitPolicy: Enforce resource budgets
- InjectionGuardPolicy: Detect prompt injection attempts
"""

from framework.policies.builtin.budget_limits import BudgetConfig, BudgetLimitPolicy, BudgetMode
from framework.policies.builtin.domain_allowlist import AllowlistMode, DomainAllowlistPolicy
from framework.policies.builtin.injection_guard import InjectionGuardPolicy, InjectionMode
from framework.policies.builtin.tool_gating import HighRiskToolGatingPolicy

__all__ = [
    # Tool gating
    "HighRiskToolGatingPolicy",
    # Domain allowlist
    "DomainAllowlistPolicy",
    "AllowlistMode",
    # Budget limits
    "BudgetLimitPolicy",
    "BudgetConfig",
    "BudgetMode",
    # Injection guard
    "InjectionGuardPolicy",
    "InjectionMode",
]
