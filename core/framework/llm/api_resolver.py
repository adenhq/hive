"""API Key resolver for different LLM providers."""

from typing import Optional


API_KEY_MAPPING = {
    "cerebras": "CEREBRAS_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gpt": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "ollama": None,
    "azure": "AZURE_API_KEY",
    "cohere": "COHERE_API_KEY",
    "replicate": "REPLICATE_API_KEY",
    "together": "TOGETHER_API_KEY",
}


def get_api_key_env_var(model: str) -> Optional[str]:
    """
    Get the environment variable name for API key based on model name.
    
    Args:
        model: LLM model identifier (e.g., "gpt-4", "claude-sonnet-4")
        
    Returns:
        Environment variable name or None for local models
        
    Examples:
        >>> get_api_key_env_var("gpt-4")
        'OPENAI_API_KEY'
        >>> get_api_key_env_var("claude-sonnet-4")
        'ANTHROPIC_API_KEY'
        >>> get_api_key_env_var("ollama/llama3")
        None
    """
    model_lower = model.lower()
    
    for prefix, env_var in API_KEY_MAPPING.items():
        if model_lower.startswith(f"{prefix}/") or model_lower.startswith(prefix):
            return env_var
    
    return "OPENAI_API_KEY"