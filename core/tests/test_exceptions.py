"""
Test structured exception hierarchy and handling in WorkerNode.
"""

import unittest
from unittest.mock import MagicMock
import asyncio

from framework.graph.plan import PlanStep, ActionSpec, ActionType
from framework.graph.worker_node import WorkerNode
from framework.runtime.core import Runtime
from framework.llm.provider import LLMProvider
from framework.exceptions import (
    HiveExecutionError,
    LLMError,
    RateLimitError,
    ConfigurationError,
    ToolExecutionError,
)


class TestExceptionHierarchy(unittest.TestCase):
    def test_hierarchy(self):
        """Verify exception inheritance."""
        self.assertTrue(issubclass(RateLimitError, LLMError))
        self.assertTrue(issubclass(LLMError, HiveExecutionError))
        self.assertTrue(issubclass(ToolExecutionError, HiveExecutionError))
        self.assertTrue(issubclass(ConfigurationError, HiveExecutionError))


class TestWorkerExceptions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_runtime = MagicMock(spec=Runtime)
        self.mock_runtime.decide.return_value = "decision_123"
        self.mock_llm = MagicMock(spec=LLMProvider)
        self.worker = WorkerNode(runtime=self.mock_runtime, llm=self.mock_llm)
        
        self.llm_step = PlanStep(
            id="step_1",
            description="Test LLM step",
            action=ActionSpec(
                action_type=ActionType.LLM_CALL,
                prompt="Hello",
            ),
            status="pending",
        )

    async def test_worker_catches_llm_error(self):
        """Test that generic LLM errors are caught and mapped."""
        # Mock LLM to raise generic exception
        self.mock_llm.complete.side_effect = ValueError("Something went wrong")

        result = await self.worker.execute(self.llm_step, {})

        self.assertFalse(result.success)
        self.assertIn("LLM call failed: Something went wrong", result.error)
        self.assertEqual(result.error_type, "llm_error")

    async def test_worker_catches_rate_limit_error(self):
        """Test that rate limit errors are caught and mapped."""
        # Mock LLM to raise exception containing 'rate'
        self.mock_llm.complete.side_effect = RuntimeError("429 Rate limit exceeded")

        result = await self.worker.execute(self.llm_step, {})

        self.assertFalse(result.success)
        self.assertIn("LLM rate limit exceeded", result.error)
        self.assertEqual(result.error_type, "rate_limit")

    async def test_worker_catches_configuration_error(self):
        """Test that configuration errors (missing LLM) are caught."""
        # Worker without LLM
        worker_no_llm = WorkerNode(runtime=self.mock_runtime, llm=None)

        result = await worker_no_llm.execute(self.llm_step, {})

        self.assertFalse(result.success)
        self.assertIn("No LLM provider configured", result.error)
        self.assertEqual(result.error_type, "configuration")

    async def test_worker_catches_tool_error(self):
        """Test that tool execution errors are caught."""
        step = PlanStep(
            id="step_tool",
            description="Test tool step",
            action=ActionSpec(
                action_type=ActionType.TOOL_USE,
                tool_name="missing_tool",
            ),
            status="pending",
        )

        result = await self.worker.execute(step, {})

        self.assertFalse(result.success)
        self.assertIn("Tool 'missing_tool' not found", result.error)
        # ConfigurationError is raised for missing tool in Registry
        self.assertEqual(result.error_type, "configuration")
