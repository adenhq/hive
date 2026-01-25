"""
Goal-Based Testing Framework

A framework where tests are written based on success_criteria and constraints,
then run with pytest and debugged with LLM assistance.
... (Mantenha o restante da docstring original da main) ...
"""

# Schemas existentes
from framework.testing.test_case import (
    ApprovalStatus,
    TestType,
    Test,
)
from framework.testing.test_result import (
    ErrorCategory,
    TestResult,
    TestSuiteResult,
)

# Storage existente
from framework.testing.test_storage import TestStorage

# New: Failure Recording (Sua contribuição)
from .failure_record import FailureRecord, FailureSeverity
from .failure_storage import FailureStorage

# Approval
from framework.testing.approval_types import (
    ApprovalAction,
    ApprovalRequest,
    ApprovalResult,
    BatchApprovalRequest,
    BatchApprovalResult,
)
from framework.testing.approval_cli import interactive_approval, batch_approval

# Outros componentes da main
from framework.testing.categorizer import ErrorCategorizer
from framework.testing.llm_judge import LLMJudge
from framework.testing.debug_tool import DebugTool, DebugInfo
from framework.testing.cli import register_testing_commands

__all__ = [
    # Schemas
    "ApprovalStatus",
    "TestType",
    "Test",
    "ErrorCategory",
    "TestResult",
    "TestSuiteResult",
    # Storage
    "TestStorage",
    # Failure Recording (Adicionado)
    "FailureRecord",
    "FailureSeverity",
    "FailureStorage",
    # Approval types
    "ApprovalAction",
    "ApprovalRequest",
    "ApprovalResult",
    "BatchApprovalRequest",
    "BatchApprovalResult",
    "interactive_approval",
    "batch_approval",
    # Error categorization
    "ErrorCategorizer",
    # LLM Judge
    "LLMJudge",
    # Debug
    "DebugTool",
    "DebugInfo",
    # CLI
    "register_testing_commands",
]