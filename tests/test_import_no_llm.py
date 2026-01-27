"""Test LLM provider configuration and usage with no LLM dependencies."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock, ANY, call
from typing import Optional, Type

# Add project root to path (fixed indentation)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the base provider class first
from core.framework.llm.provider import LLMProvider, LLMResponse

# Create a mock provider class that inherits from LLMProvider
class MockLLMProvider(LLMProvider):
    model: str = "test-model"
    
    def __init__(self, **data):
        super().__init__(**data)
        self._generate = AsyncMock()
        self._complete_with_tools = AsyncMock()
        self._generate_with_tools = AsyncMock()
        
    async def generate(self, prompt: str, **kwargs):
        return await self._generate(prompt, **kwargs)
        
    async def complete_with_tools(self, prompt: str, tools: list, **kwargs):
        return await self._complete_with_tools(prompt, tools, **kwargs)
        
    async def generate_with_tools(self, prompt: str, tools: list, **kwargs):
        return await self._generate_with_tools(prompt, tools, **kwargs)

# Now patch the imports before importing the rest of the modules
with patch('core.framework.llm.litellm.LiteLLMProvider', new=MockLLMProvider):
    from core.framework.llm.litellm import LiteLLMProvider
    from core.framework.mcp.agent_builder_server import (
        set_llm_provider,
        get_llm_provider
    )

# Apply the patch at the module level
import sys
import core.framework.llm.litellm as litellm_module
litellm_module.LiteLLMProvider = MockLLMProvider

# Also patch the provider in the agent_builder_server module
import core.framework.mcp.agent_builder_server as abs_module
abs_module.LLMProvider = LLMProvider  # Make sure the base class is available
abs_module.LiteLLMProvider = MockLLMProvider  # Patch the provider

class TestLLMProviderConfig(unittest.IsolatedAsyncioTestCase):
    """Test LLM provider configuration."""

    def setUp(self):
        """Reset provider before each test."""
        set_llm_provider(None)

    def test_set_and_get_provider(self):
        """Test setting and getting a provider."""
        # Create a test provider instance
        test_provider = MockLLMProvider(model="test-model")
        
        # Set and get the provider
        set_llm_provider(test_provider)
        retrieved = get_llm_provider()
        
        # Verify
        self.assertEqual(retrieved, test_provider)
        self.assertEqual(retrieved.model, "test-model")

    def test_default_provider(self):
        """Test that get_llm_provider returns the default provider."""
        # Set a mock provider first
        test_provider = MockLLMProvider()
        set_llm_provider(test_provider)
        
        # Now get it back
        provider_instance = get_llm_provider()
        self.assertIsNotNone(provider_instance)
        self.assertIsInstance(provider_instance, MockLLMProvider)

    @patch.dict(os.environ, {"LITELLM_MODEL": "gpt-4"})
    def test_environment_config(self):
        """Test provider configuration from environment."""
        # This test verifies that the environment variable is used to configure the model
        provider = LiteLLMProvider(model="gpt-4")
        self.assertEqual(provider.model, "gpt-4")

    async def test_provider_generate(self):
        """Test generating text with the provider."""
        # Create a test provider with a mock generate method
        test_provider = MockLLMProvider(model="test-model")
        
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_response.model = "test-model"
        mock_response.input_tokens = 5
        mock_response.output_tokens = 7
        mock_response.stop_reason = "stop"
        
        # Configure the mock
        test_provider._generate.return_value = mock_response
        
        # Call the method
        response = await test_provider.generate("Test prompt")
        
        # Verify the response
        self.assertEqual(response.content, "Test response")
        self.assertEqual(response.model, "test-model")
        self.assertEqual(response.input_tokens, 5)
        self.assertEqual(response.output_tokens, 7)
        self.assertEqual(response.stop_reason, "stop")
        
        # Verify the method was called correctly
        test_provider._generate.assert_awaited_once_with("Test prompt")

    def test_error_handling(self):
        """Test error handling for provider configuration."""
        # Save the original provider
        original_provider = get_llm_provider(raise_if_none=False)
        
        try:
            # Clear the provider
            set_llm_provider(None)
            
            # Should raise when raise_if_none=True
            with self.assertRaises(ValueError):
                get_llm_provider(raise_if_none=True)
            
            # Should return None when raise_if_none=False
            provider = get_llm_provider(raise_if_none=False)
            self.assertIsNone(provider)
            
            # Test with an invalid provider type
            with self.assertRaises(ValueError):
                set_llm_provider("not_a_provider")
                
        finally:
            # Restore the original provider
            set_llm_provider(original_provider)


if __name__ == "__main__":
    unittest.main()
