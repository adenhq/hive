"""Tests for LLM cost tracking functionality."""

import pytest
from framework.llm.cost import LLMCostCalculator
from framework.llm.provider import LLMResponse
from framework.llm.litellm import LiteLLMProvider
from framework.graph.node import NodeResult
from framework.graph.executor import ExecutionResult


class TestLLMCostCalculator:
    """Test the LLM cost calculator utility."""

    def test_calculate_gpt4o_cost(self):
        """Test cost calculation for GPT-4o."""
        cost = LLMCostCalculator.calculate(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )
        # 1000 * 2.50 / 1M + 500 * 10.00 / 1M = 0.0025 + 0.005 = 0.0075
        assert cost == pytest.approx(0.0075, abs=0.0001)

    def test_calculate_gpt4o_mini_cost(self):
        """Test cost calculation for GPT-4o-mini."""
        cost = LLMCostCalculator.calculate(
            model="gpt-4o-mini",
            input_tokens=10000,
            output_tokens=2000,
        )
        # 10000 * 0.15 / 1M + 2000 * 0.60 / 1M = 0.0015 + 0.0012 = 0.0027
        assert cost == pytest.approx(0.0027, abs=0.0001)

    def test_calculate_claude_sonnet_cost(self):
        """Test cost calculation for Claude 3.5 Sonnet."""
        cost = LLMCostCalculator.calculate(
            model="claude-3-5-sonnet-20241022",
            input_tokens=5000,
            output_tokens=1000,
        )
        # 5000 * 3.00 / 1M + 1000 * 15.00 / 1M = 0.015 + 0.015 = 0.03
        assert cost == pytest.approx(0.03, abs=0.0001)

    def test_calculate_claude_haiku_cost(self):
        """Test cost calculation for Claude 3.5 Haiku."""
        cost = LLMCostCalculator.calculate(
            model="claude-3-5-haiku-20241022",
            input_tokens=10000,
            output_tokens=5000,
        )
        # 10000 * 0.80 / 1M + 5000 * 4.00 / 1M = 0.008 + 0.02 = 0.028
        assert cost == pytest.approx(0.028, abs=0.0001)

    def test_calculate_gemini_flash_cost(self):
        """Test cost calculation for Gemini 1.5 Flash."""
        cost = LLMCostCalculator.calculate(
            model="gemini-1.5-flash",
            input_tokens=100000,
            output_tokens=10000,
        )
        # 100000 * 0.075 / 1M + 10000 * 0.30 / 1M = 0.0075 + 0.003 = 0.0105
        assert cost == pytest.approx(0.0105, abs=0.0001)

    def test_calculate_unknown_model_returns_zero(self):
        """Test that unknown models return zero cost."""
        cost = LLMCostCalculator.calculate(
            model="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost == 0.0

    def test_calculate_with_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = LLMCostCalculator.calculate(
            model="gpt-4o",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0

    def test_calculate_large_token_counts(self):
        """Test cost calculation with large token counts."""
        cost = LLMCostCalculator.calculate(
            model="gpt-4o-mini",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=500_000,   # 0.5M tokens
        )
        # 1M * 0.15 / 1M + 0.5M * 0.60 / 1M = 0.15 + 0.30 = 0.45
        assert cost == pytest.approx(0.45, abs=0.001)

    def test_get_pricing_known_model(self):
        """Test getting pricing for a known model."""
        pricing = LLMCostCalculator.get_pricing("gpt-4o")
        assert pricing == (2.50, 10.00)

    def test_get_pricing_unknown_model(self):
        """Test getting pricing for an unknown model."""
        pricing = LLMCostCalculator.get_pricing("unknown-model")
        assert pricing is None

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

    def test_all_models_have_valid_pricing(self):
        """Test that all models in the pricing table have valid values."""
        for model, (input_cost, output_cost) in LLMCostCalculator.PRICING.items():
            assert input_cost >= 0, f"Model {model} has negative input cost"
            assert output_cost >= 0, f"Model {model} has negative output cost"
            assert isinstance(input_cost, (int, float)), f"Model {model} has invalid input cost type"
            assert isinstance(output_cost, (int, float)), f"Model {model} has invalid output cost type"


class TestLLMResponseCostTracking:
    """Test that LLMResponse includes cost information."""

    def test_llm_response_has_cost_fields(self):
        """Test that LLMResponse has cost fields."""
        response = LLMResponse(
            content="test",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.0015,
            cost_breakdown={"input_tokens": 100, "output_tokens": 50, "model": "gpt-4o"},
        )
        
        assert response.estimated_cost_usd == 0.0015
        assert response.cost_breakdown["input_tokens"] == 100
        assert response.cost_breakdown["output_tokens"] == 50
        assert response.cost_breakdown["model"] == "gpt-4o"

    def test_llm_response_defaults_to_zero_cost(self):
        """Test that LLMResponse defaults to zero cost."""
        response = LLMResponse(
            content="test",
            model="gpt-4o",
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
            llm_model="gpt-4o",
        )
        
        assert result.cost_usd == 0.002
        assert result.llm_model == "gpt-4o"

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
            cost_by_model={"gpt-4o": 0.010, "gpt-4o-mini": 0.005},
        )
        
        assert result.total_cost_usd == 0.015
        assert result.cost_by_model["gpt-4o"] == 0.010
        assert result.cost_by_model["gpt-4o-mini"] == 0.005

    def test_execution_result_defaults_to_zero_cost(self):
        """Test that ExecutionResult defaults to zero cost."""
        result = ExecutionResult(
            success=True,
            output={"final": "output"},
        )
        
        assert result.total_cost_usd == 0.0
        assert result.cost_by_model == {}


class TestCostCalculationAccuracy:
    """Test accuracy of cost calculations against known values."""

    def test_realistic_conversation_cost(self):
        """Test cost for a realistic conversation."""
        # Typical user message: ~50 tokens input, ~200 tokens output
        cost = LLMCostCalculator.calculate(
            model="gpt-4o-mini",
            input_tokens=50,
            output_tokens=200,
        )
        # 50 * 0.15 / 1M + 200 * 0.60 / 1M = 0.0000075 + 0.00012 = 0.0001275
        assert cost == pytest.approx(0.0001275, abs=0.00001)
        assert cost < 0.001, "Single message should cost less than $0.001"

    def test_long_document_processing_cost(self):
        """Test cost for processing a long document."""
        # Long document: ~50k tokens input, ~2k tokens summary output
        cost = LLMCostCalculator.calculate(
            model="claude-3-5-haiku-20241022",
            input_tokens=50000,
            output_tokens=2000,
        )
        # 50000 * 0.80 / 1M + 2000 * 4.00 / 1M = 0.04 + 0.008 = 0.048
        assert cost == pytest.approx(0.048, abs=0.001)
        assert cost < 0.10, "Long document should cost less than $0.10"

    def test_agent_workflow_cost(self):
        """Test cost for a multi-step agent workflow."""
        # Agent workflow: 3 LLM calls
        total_cost = 0.0
        
        # Step 1: Understand request (small)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
        )
        
        # Step 2: Process (medium)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-4o",
            input_tokens=500,
            output_tokens=300,
        )
        
        # Step 3: Format response (small)
        total_cost += LLMCostCalculator.calculate(
            model="gpt-4o-mini",
            input_tokens=200,
            output_tokens=100,
        )
        
        assert total_cost < 0.01, "3-step workflow should cost less than $0.01"
