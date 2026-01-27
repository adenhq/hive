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

from framework.schemas.decision import Decision, Option, Outcome, DecisionEvaluation
from framework.schemas.run import Run, RunSummary, Problem
from framework.runtime.core import Runtime
from framework.builder.query import BuilderQuery
from framework.llm import LLMProvider, get_available_providers
from framework.runner import AgentRunner, AgentOrchestrator

# Testing framework
from framework.testing import (
    Test,
    TestResult,
    TestSuiteResult,
    TestStorage,
    ApprovalStatus,
    ErrorCategory,
    DebugTool,
)

# Make LLM imports optional
_llm_providers = {}
try:
    from framework.llm import AnthropicProvider
    _llm_providers['anthropic'] = AnthropicProvider
except ImportError:
    pass

try:
    from framework.llm import LiteLLMProvider
    _llm_providers['litellm'] = LiteLLMProvider
except ImportError:
    pass

def get_llm_provider(name):
    """Get an LLM provider by name if available.
    
    Args:
        name: Name of the provider ('anthropic', 'litellm', etc.)
        
    Returns:
        The provider class if available, None otherwise
    """
    return _llm_providers.get(name)

__all__ = [
    # Schemas
    "Decision",
    "Option",
    "Outcome",
    "DecisionEvaluation",
    "Run",
    "RunSummary",
    # LLM
    "get_llm_provider",
    "get_available_providers",
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
    # Testing
    "Test",
    "TestResult",
    "TestSuiteResult",
    "TestStorage",
    "ApprovalStatus",
    "ErrorCategory",
    "DebugTool",
]
