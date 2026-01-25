"""Tests for LLM cost tracking functionality."""

import pytest
from framework.llm.cost import LLMCostCalculator
from framework.llm.provider import LLMResponse
from framework.graph.node import NodeResult
from framework.graph.executor import ExecutionResult


class TestLLMCostCalculator:
    """Test the LLM cost calculator utility."""

    def test_calculate_returns_positive_cost_for_known_models(self):
        """Test that cost calculation returns positive values for known models."""
        models = [
            "gpt-5.2",
            "gpt-5-mini",
            "gpt-4o",
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
        ]
        
        for model in models:
            cost = LLMCostCalculator.calculate(
                model=model,
                input_tokens=1000,
                output_tokens=500,
            )
            assert cost > 0, f"Model {model} should have positive cost"
            assert isinstance(cost, float), f"Model {model} should return float cost"

    def test_calculate_unknown_model_returns_zero(self):
        """Test that unknown models return zero cost."""
        cost = LLMCostCalculator.calculate(
            model="unknown-model-xyz-12345",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost == 0.0

    def test_calculate_with_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = LLMCostCalculator.calculate(
            model="gpt-5.2",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0

    def test_calculate_scales_with_tokens(self):
        """Test that cost scales proportionally with token count."""
        model = "gpt-5-mini"
        
        # Small request
        cost_small = LLMCostCalculator.calculate(
            model=model,
            input_tokens=100,
            output_tokens=50,
        )
        
        # Large request (10x tokens)
        cost_large = LLMCostCalculator.calculate(
            model=model,
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert cost_small > 0
        assert cost_large > 0
        assert cost_large > cost_small, "More tokens should cost more"
        
        # Should scale roughly 10x (allowing for rounding)
        ratio = cost_large / cost_small
        assert 9.5 < ratio < 10.5, f"Expected ~10x cost, got {ratio:.2f}x"

    def test_more_expensive_models_cost_more(self):
        """Test that premium models cost more than economy models."""
        tokens = (5000, 2000)  # Same token counts
        
        # Economy model
        cost_mini = LLMCostCalculator.calculate("gpt-5-mini", *tokens)
        
        # Premium model
        cost_pro = LLMCostCalculator.calculate("gpt-5.2-pro", *tokens)
        
        assert cost_mini > 0
        assert cost_pro > 0
        assert cost_pro > cost_mini, "Pro model should cost more than mini"

    def test_output_tokens_cost_more_than_input(self):
        """Test that output tokens typically cost more than input tokens."""
        model = "gpt-5.2"
        
        # More input tokens
        cost_input_heavy = LLMCostCalculator.calculate(
            model=model,
            input_tokens=10000,
            output_tokens=1000,
        )
        
        # More output tokens (same total)
        cost_output_heavy = LLMCostCalculator.calculate(
            model=model,
            input_tokens=1000,
            output_tokens=10000,
        )
        
        assert cost_input_heavy > 0
        assert cost_output_heavy > 0
        assert cost_output_heavy > cost_input_heavy, "Output tokens typically cost more"

    def test_format_cost_small(self):
        """Test formatting small costs."""
        assert LLMCostCalculator.format_cost(0.0042) == "$0.0042"
        assert LLMCostCalculator.format_cost(0.0001) == "$0.0001"

    def test_format_cost_medium(self):
        """Test formatting medium costs."""
        assert LLMCostCalculator.format_cost(0.123) == "$0.123"
        assert LLMCostCalculator.format_cost(0.99) == "$0.990"

    def test_format_cost_large(self):
        """Test formatting large costs."""
        assert LLMCostCalculator.format_cost(1.23) == "$1.23"
        assert LLMCostCalculator.format_cost(45.67) == "$45.67"


class TestLLMResponseCostTracking:
    """Test that LLMResponse includes cost information."""

    def test_llm_response_has_cost_fields(self):
        """Test that LLMResponse has cost fields."""
        response = LLMResponse(
            content="test",
            model="gpt-5.2",
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.0015,
            cost_breakdown={"input_tokens": 100, "output_tokens": 50, "model": "gpt-5.2"},
        )
        
        assert response.estimated_cost_usd == 0.0015
        assert response.cost_breakdown["input_tokens"] == 100
        assert response.cost_breakdown["output_tokens"] == 50
        assert response.cost_breakdown["model"] == "gpt-5.2"

    def test_llm_response_defaults_to_zero_cost(self):
        """Test that LLMResponse defaults to zero cost."""
        response = LLMResponse(
            content="test",
            model="gpt-5.2",
        )
        
        assert response.estimated_cost_usd == 0.0
        assert response.cost_breakdown == {}


class TestNodeResultCostTracking:
    """Test that NodeResult includes cost information."""

    def test_node_result_has_cost_fields(self):
        """Test that NodeResult has cost fields."""
        result = NodeResult(
            success=True,
            output={"result": "test"},
            tokens_used=150,
            latency_ms=500,
            cost_usd=0.002,
            llm_model="gpt-5.2",
        )
        
        assert result.cost_usd == 0.002
        assert result.llm_model == "gpt-5.2"

    def test_node_result_defaults_to_zero_cost(self):
        """Test that NodeResult defaults to zero cost."""
        result = NodeResult(
            success=True,
            output={"result": "test"},
        )
        
        assert result.cost_usd == 0.0
        assert result.llm_model is None


class TestExecutionResultCostTracking:
    """Test that ExecutionResult includes cost information."""

    def test_execution_result_has_cost_fields(self):
        """Test that ExecutionResult has cost fields."""
        result = ExecutionResult(
            success=True,
            output={"final": "output"},
            steps_executed=3,
            total_tokens=500,
            total_cost_usd=0.015,
            cost_by_model={"gpt-5.2": 0.010, "gpt-5-mini": 0.005},
        )
        
        assert result.total_cost_usd == 0.015
        assert result.cost_by_model["gpt-5.2"] == 0.010
        assert result.cost_by_model["gpt-5-mini"] == 0.005

    def test_execution_result_defaults_to_zero_cost(self):
        """Test that ExecutionResult defaults to zero cost."""
        result = ExecutionResult(
            success=True,
            output={"final": "output"},
        )
        
        assert result.total_cost_usd == 0.0
        assert result.cost_by_model == {}


class TestCostCalculationBehavior:
    """Test cost calculation behavior across different scenarios."""

    def test_realistic_conversation_cost_is_reasonable(self):
        """Test that realistic conversation costs are in expected range."""
        # Typical user message: ~50 tokens input, ~200 tokens output
        cost = LLMCostCalculator.calculate(
            model="gpt-5-mini",
            input_tokens=50,
            output_tokens=200,
        )
        assert cost > 0, "Cost should be positive"
        assert cost < 0.01, "Single message should cost less than $0.01"

    def test_long_document_processing_cost(self):
        """Test cost for processing a long document."""
        # Long document: ~50k tokens input, ~2k tokens summary output
        cost = LLMCostCalculator.calculate(
            model="claude-haiku-4-5-20251001",
            input_tokens=50000,
            output_tokens=2000,
        )
        assert cost > 0, "Cost should be positive"
        assert cost < 1.0, "Long document should cost less than $1.00"

    def test_premium_model_workflow_cost(self):
        """Test cost for a multi-step agent workflow with premium models."""
        total_cost = 0.0
        
        # Step 1: Understand request (small)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-5-mini",
            input_tokens=100,
            output_tokens=50,
        )
        
        # Step 2: Deep reasoning (large)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-5.2",
            input_tokens=5000,
            output_tokens=2000,
        )
        
        # Step 3: Format response (small)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-5-mini",
            input_tokens=200,
            output_tokens=100,
        )
        
        assert total_cost > 0, "Total cost should be positive"
        assert total_cost < 1.0, "3-step workflow should cost less than $1.00"

    def test_cost_calculation_handles_edge_cases(self):
        """Test that cost calculation handles edge cases gracefully."""
        # Very large token counts
        cost = LLMCostCalculator.calculate(
            model="gpt-5.2",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        assert cost > 0, "Should handle large token counts"
        
        # Single token
        cost = LLMCostCalculator.calculate(
            model="gpt-5.2",
            input_tokens=1,
            output_tokens=1,
        )
        assert cost > 0, "Should handle single tokens"
