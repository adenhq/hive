"""Tests for MockLLMProvider."""

import pytest
from framework.llm.mock_provider import MockLLMProvider, create_mock_provider


def test_mock_provider_initialization() -> None:
    """Test that mock provider initializes correctly."""
    provider = MockLLMProvider(model="test-model")
    assert provider.model == "test-model"
    assert provider.call_count == 0


def test_mock_provider_generate() -> None:
    """Test basic generation."""
    provider = MockLLMProvider()
    
    messages = [
        {"role": "user", "content": "Hello, can you help me?"}
    ]
    
    response = provider.generate(messages)
    
    assert "content" in response
    assert response["role"] == "assistant"
    assert response["mock"] is True
    assert provider.call_count == 1


def test_mock_provider_contextual_responses() -> None:
    """Test that provider gives contextual responses."""
    provider = MockLLMProvider()
    
    # Test search query
    messages = [{"role": "user", "content": "Search for Python tutorials"}]
    response = provider.generate(messages)
    assert "search_results" in response["content"] or "Mock" in response["content"]
    
    # Test analysis query
    messages = [{"role": "user", "content": "Analyze this data"}]
    response = provider.generate(messages)
    assert "analysis" in response["content"].lower() or "mock" in response["content"].lower()


def test_mock_provider_stats() -> None:
    """Test statistics tracking."""
    provider = MockLLMProvider()
    
    # Make a few calls
    provider.generate([{"role": "user", "content": "Test 1"}])
    provider.generate([{"role": "user", "content": "Test 2"}])
    
    stats = provider.get_stats()
    assert stats["total_calls"] == 2
    assert len(stats["call_history"]) == 2


def test_mock_provider_reset() -> None:
    """Test reset functionality."""
    provider = MockLLMProvider()
    provider.generate([{"role": "user", "content": "Test"}])
    
    assert provider.call_count == 1
    
    provider.reset()
    assert provider.call_count == 0
    assert len(provider.call_history) == 0


def test_create_mock_provider() -> None:
    """Test convenience function."""
    provider = create_mock_provider(model="custom-mock")
    assert isinstance(provider, MockLLMProvider)
    assert provider.model == "custom-mock"


@pytest.mark.asyncio
async def test_mock_provider_async():
    """Test async generation."""
    provider = MockLLMProvider()
    
    messages = [{"role": "user", "content": "Async test"}]
    response = await provider.agenerate(messages)
    
    assert "content" in response
    assert response["mock"] is True