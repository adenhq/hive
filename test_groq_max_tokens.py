#!/usr/bin/env python3
"""Quick test to verify Groq max_tokens constraint."""

import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

from framework.llm.litellm import LiteLLMProvider


def test_groq_max_tokens_constraint():
    """Test that Groq models constrain max_tokens to 16384."""
    # Test with Groq model
    provider = LiteLLMProvider(model="groq/llama3-70b-8192")
    
    # Test values that should be constrained
    test_cases = [
        (32000, 16384),  # Should be constrained to 16384
        (64000, 16384),  # Should be constrained to 16384
        (16384, 16384),  # Should stay at 16384
        (8192, 8192),    # Should stay at 8192
        (1024, 1024),    # Should stay at 1024
    ]
    
    print("Testing Groq max_tokens constraint...")
    for input_val, expected in test_cases:
        result = provider._constrain_max_tokens(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} max_tokens={input_val} -> {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("\nTesting other providers (should not constrain)...")
    # Test with non-Groq models
    openai_provider = LiteLLMProvider(model="openai/gpt-4o-mini")
    result = openai_provider._constrain_max_tokens(32000)
    print(f"  ✓ OpenAI max_tokens=32000 -> {result} (no constraint)")
    assert result == 32000, "OpenAI should not be constrained"
    
    anthropic_provider = LiteLLMProvider(model="anthropic/claude-3-5-sonnet")
    result = anthropic_provider._constrain_max_tokens(64000)
    print(f"  ✓ Anthropic max_tokens=64000 -> {result} (no constraint)")
    assert result == 64000, "Anthropic should not be constrained"
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_groq_max_tokens_constraint()
