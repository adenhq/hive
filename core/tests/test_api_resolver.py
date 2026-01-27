"""Tests for API key resolver."""

import pytest
from framework.llm.api_resolver import get_api_key_env_var, API_KEY_MAPPING


class TestGetApiKeyEnvVar:
    """Tests for get_api_key_env_var function."""

    def test_cerebras_models(self):
        """Test Cerebras model detection."""
        assert get_api_key_env_var("cerebras/zai-glm-4.7") == "CEREBRAS_API_KEY"
        assert get_api_key_env_var("cerebras/llama3") == "CEREBRAS_API_KEY"

    def test_openai_models(self):
        """Test OpenAI model detection."""
        assert get_api_key_env_var("openai/gpt-4") == "OPENAI_API_KEY"
        assert get_api_key_env_var("gpt-4o") == "OPENAI_API_KEY"
        assert get_api_key_env_var("gpt-3.5-turbo") == "OPENAI_API_KEY"

    def test_anthropic_models(self):
        """Test Anthropic model detection."""
        assert get_api_key_env_var("anthropic/claude-3") == "ANTHROPIC_API_KEY"
        assert get_api_key_env_var("claude-sonnet-4") == "ANTHROPIC_API_KEY"
        assert get_api_key_env_var("claude-opus-3") == "ANTHROPIC_API_KEY"

    def test_google_models(self):
        """Test Google model detection."""
        assert get_api_key_env_var("gemini/gemini-pro") == "GOOGLE_API_KEY"
        assert get_api_key_env_var("google/gemini-1.5") == "GOOGLE_API_KEY"

    def test_other_providers(self):
        """Test other provider models."""
        assert get_api_key_env_var("mistral/mistral-large") == "MISTRAL_API_KEY"
        assert get_api_key_env_var("groq/llama3-70b") == "GROQ_API_KEY"
        assert get_api_key_env_var("azure/gpt-4") == "AZURE_API_KEY"
        assert get_api_key_env_var("cohere/command") == "COHERE_API_KEY"
        assert get_api_key_env_var("replicate/llama-2") == "REPLICATE_API_KEY"
        assert get_api_key_env_var("together/llama-2") == "TOGETHER_API_KEY"

    def test_ollama_no_key(self):
        """Test Ollama models don't need API key."""
        assert get_api_key_env_var("ollama/llama3") is None
        assert get_api_key_env_var("ollama/mistral") is None

    def test_unknown_defaults_to_openai(self):
        """Test unknown models default to OpenAI."""
        assert get_api_key_env_var("unknown/model") == "OPENAI_API_KEY"
        assert get_api_key_env_var("custom-model") == "OPENAI_API_KEY"

    def test_case_insensitive(self):
        """Test model name matching is case-insensitive."""
        assert get_api_key_env_var("OPENAI/GPT-4") == "OPENAI_API_KEY"
        assert get_api_key_env_var("Claude-Sonnet-4") == "ANTHROPIC_API_KEY"
        assert get_api_key_env_var("GEMINI/GEMINI-PRO") == "GOOGLE_API_KEY"

    def test_api_key_mapping_completeness(self):
        """Test that API_KEY_MAPPING contains expected providers."""
        expected_providers = [
            "cerebras",
            "openai",
            "gpt",
            "anthropic",
            "claude",
            "gemini",
            "google",
            "mistral",
            "groq",
            "ollama",
            "azure",
            "cohere",
            "replicate",
            "together",
        ]
        for provider in expected_providers:
            assert provider in API_KEY_MAPPING, f"Missing provider: {provider}"