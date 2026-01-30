"""
Aden Hive Framework: A goal-driven agent runtime optimized for Builder observability.

The runtime is designed around DECISIONS, not just actions. Every significant
choice the agent makes is captured with:
- What it was trying to do (intent)
- What options it considered
- What it chose and why
- What happened as a result
- Whether that was good or bad (evaluated post-hoc)

This gives the Builder LLM the information it needs to improve agent behavior.

## Testing Framework

The framework includes a Goal-Based Testing system (Goal → Agent → Eval):
- Generate tests from Goal success_criteria and constraints
- Mandatory user approval before tests are stored
- Parallel test execution with error categorization
- Debug tools with fix suggestions

See `framework.testing` for details.
"""

from framework.builder.query import BuilderQuery
from framework.llm import AnthropicProvider, LLMProvider
from framework.runner import AgentOrchestrator, AgentRunner
from framework.runner.runner import PolicyConfig
from framework.runtime.core import Runtime
from framework.schemas.decision import Decision, DecisionEvaluation, Option, Outcome
from framework.schemas.run import Problem, Run, RunSummary

# Testing framework
from framework.testing import (
    ApprovalStatus,
    DebugTool,
    ErrorCategory,
    Test,
    TestResult,
    TestStorage,
    TestSuiteResult,
)

# Policy framework (guardrails)
from framework.policies import (
    AggregatedDecision,
    AllowlistMode,
    BasePolicy,
    BudgetConfig,
    BudgetLimitPolicy,
    BudgetMode,
    ConfirmationRequiredError,
    DomainAllowlistPolicy,
    GuardrailsError,
    HighRiskToolGatingPolicy,
    InjectionGuardPolicy,
    InjectionMode,
    Policy,
    PolicyAction,
    PolicyConfigurationError,
    PolicyDecision,
    PolicyEngine,
    PolicyEvent,
    PolicyEventType,
    PolicyRegistrationError,
    PolicyViolationError,
    Severity,
    ToolInterceptor,
)

__all__ = [
    # Schemas
    "Decision",
    "Option",
    "Outcome",
    "DecisionEvaluation",
    "Run",
    "RunSummary",
    "Problem",
    # Runtime
    "Runtime",
    # Builder
    "BuilderQuery",
    # LLM
    "LLMProvider",
    "AnthropicProvider",
    # Runner
    "AgentRunner",
    "AgentOrchestrator",
    "PolicyConfig",
    # Testing
    "Test",
    "TestResult",
    "TestSuiteResult",
    "TestStorage",
    "ApprovalStatus",
    "ErrorCategory",
    "DebugTool",
    # Policy Framework (Guardrails)
    "PolicyEngine",
    "AggregatedDecision",
    "PolicyEvent",
    "PolicyEventType",
    "PolicyDecision",
    "PolicyAction",
    "Severity",
    "Policy",
    "BasePolicy",
    "HighRiskToolGatingPolicy",
    "DomainAllowlistPolicy",
    "AllowlistMode",
    "BudgetLimitPolicy",
    "BudgetConfig",
    "BudgetMode",
    "InjectionGuardPolicy",
    "InjectionMode",
    "ToolInterceptor",
    "GuardrailsError",
    "PolicyViolationError",
    "PolicyConfigurationError",
    "PolicyRegistrationError",
    "ConfirmationRequiredError",
]
