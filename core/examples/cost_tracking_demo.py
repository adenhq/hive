"""
Demo script showing LLM cost tracking in action.

This example shows how cost tracking works across the framework.
"""

from framework.llm.litellm import LiteLLMProvider
from framework.llm.cost import LLMCostCalculator


def demo_basic_cost_calculation():
    """Show basic cost calculation for different models."""
    print("=" * 60)
    print("DEMO: Basic Cost Calculation")
    print("=" * 60)
    
    examples = [
        ("gpt-4o-mini", 1000, 500, "Quick chat response"),
        ("gpt-4o", 5000, 2000, "Complex reasoning task"),
        ("claude-3-5-haiku-20241022", 10000, 3000, "Fast document analysis"),
        ("claude-3-5-sonnet-20241022", 20000, 5000, "High-quality content generation"),
    ]
    
    total_cost = 0.0
    
    for model, input_tokens, output_tokens, description in examples:
        cost = LLMCostCalculator.calculate(model, input_tokens, output_tokens)
        total_cost += cost
        
        print(f"\n{description}:")
        print(f"  Model: {model}")
        print(f"  Tokens: {input_tokens:,} in + {output_tokens:,} out")
        print(f"  Cost: {LLMCostCalculator.format_cost(cost)}")
    
    print(f"\n{'─' * 60}")
    print(f"Total cost: {LLMCostCalculator.format_cost(total_cost)}")
    print()


def demo_llm_response_with_costs():
    """Show how LLMResponse includes cost information."""
    print("=" * 60)
    print("DEMO: LLM Response Cost Tracking")
    print("=" * 60)
    
    # Note: This is a conceptual demo - actual API calls would require API keys
    print("\nWhen you call an LLM provider, the response includes cost info:\n")
    
    print("Example response structure:")
    print("""
    LLMResponse(
        content="The answer is 42",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.000045,  # Automatically calculated!
        cost_breakdown={
            "input_tokens": 100,
            "output_tokens": 50,
            "model": "gpt-4o-mini"
        }
    )
    """)
    
    print("\nThe cost is calculated automatically based on:")
    print("  • Model pricing (kept up-to-date in LLMCostCalculator.PRICING)")
    print("  • Input token count")
    print("  • Output token count")
    print()


def demo_agent_execution_costs():
    """Show how costs accumulate during agent execution."""
    print("=" * 60)
    print("DEMO: Agent Execution Cost Tracking")
    print("=" * 60)
    
    print("\nDuring agent execution, costs are tracked per-node and accumulated:\n")
    
    # Simulate a multi-step agent workflow
    steps = [
        ("understand-request", "gpt-4o-mini", 200, 100, "Parse user input"),
        ("research", "gpt-4o", 3000, 1500, "Research topic"),
        ("analyze", "claude-3-5-sonnet-20241022", 5000, 2000, "Deep analysis"),
        ("format-output", "gpt-4o-mini", 500, 300, "Format results"),
    ]
    
    total_cost = 0.0
    cost_by_model = {}
    
    print("Step-by-step execution:\n")
    
    for step_name, model, input_tok, output_tok, description in steps:
        cost = LLMCostCalculator.calculate(model, input_tok, output_tok)
        total_cost += cost
        
        if model not in cost_by_model:
            cost_by_model[model] = 0.0
        cost_by_model[model] += cost
        
        print(f"  {step_name}: {description}")
        print(f"    Model: {model}")
        print(f"    Tokens: {input_tok + output_tok:,}")
        print(f"    Cost: {LLMCostCalculator.format_cost(cost)}")
        print()
    
    print(f"{'─' * 60}")
    print(f"\nExecution Summary:")
    print(f"  Total steps: {len(steps)}")
    print(f"  Total cost: {LLMCostCalculator.format_cost(total_cost)}")
    print(f"\n  Cost by model:")
    for model, cost in cost_by_model.items():
        print(f"    {model}: {LLMCostCalculator.format_cost(cost)}")
    print()
    
    print("This information is available in ExecutionResult:")
    print("  result.total_cost_usd = 0.189")
    print("  result.cost_by_model = {...}")
    print()


def demo_cost_comparison():
    """Compare costs across different models for the same task."""
    print("=" * 60)
    print("DEMO: Cost Comparison Across Models")
    print("=" * 60)
    
    # Same task with different models
    input_tokens = 5000
    output_tokens = 2000
    
    models = [
        ("gpt-4o-mini", "Fastest, most economical"),
        ("gpt-4o", "Balanced quality/cost"),
        ("claude-3-5-haiku-20241022", "Fast Claude"),
        ("claude-3-5-sonnet-20241022", "High-quality Claude"),
    ]
    
    print(f"\nTask: Process {input_tokens:,} input tokens, generate {output_tokens:,} output tokens\n")
    
    costs = []
    for model, description in models:
        cost = LLMCostCalculator.calculate(model, input_tokens, output_tokens)
        costs.append((model, cost, description))
    
    # Sort by cost
    costs.sort(key=lambda x: x[1])
    
    print("Model comparison (cheapest to most expensive):\n")
    for i, (model, cost, description) in enumerate(costs, 1):
        print(f"{i}. {model}")
        print(f"   {description}")
        print(f"   Cost: {LLMCostCalculator.format_cost(cost)}")
        if i > 1:
            multiplier = cost / costs[0][1]
            print(f"   {multiplier:.1f}x more expensive than cheapest")
        print()


if __name__ == "__main__":
    demo_basic_cost_calculation()
    demo_llm_response_with_costs()
    demo_agent_execution_costs()
    demo_cost_comparison()
    
    print("=" * 60)
    print("Cost tracking is now built into the framework!")
    print("=" * 60)
    print("\nKey features:")
    print("  ✓ Automatic cost calculation for all LLM calls")
    print("  ✓ Support for 30+ models (OpenAI, Anthropic, Gemini, etc.)")
    print("  ✓ Per-node cost tracking in agents")
    print("  ✓ Cost breakdown by model in execution results")
    print("  ✓ Easy-to-update pricing table")
    print()
