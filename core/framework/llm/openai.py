"""OpenAI LLM provider - backward compatible wrapper around LiteLLM."""

from base_provider import BaseLiteLLMProviderWrapper

class OpenAIProvider(BaseLiteLLMProviderWrapper):
            def __init__(self, api_key=None, model="gpt-4o-mini"):
                self.api_key = api_key or get_api_key_from_credential_store("openai", "OPENAI_API_KEY")
                if not self.api_key:
                    raise ValueError("API key required")
                self.model = model
                self._init_provider()
