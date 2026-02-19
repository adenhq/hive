"""Anthropic Claude LLM provider - backward compatible wrapper around LiteLLM."""

from base_provider import BaseLiteLLMProviderWrapper

class AnthropicProvider(BaseLiteLLMProviderWrapper):
            def __init__(self, api_key=None, model="claude-haiku-4-5-20251001"):
                self.api_key = api_key or get_api_key_from_credential_store("anthropic", "ANTHROPIC_API_KEY")
                if not self.api_key:
                    raise ValueError("API key required")
                self.model = model
                self._init_provider()
