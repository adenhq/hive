"""Centralized constants for LLM provider behavior."""

# Preferred key order from litellm.get_model_info() for output token limits.
# We prioritize explicit output/completion fields over generic max_tokens.
MODEL_OUTPUT_TOKEN_LIMIT_KEYS: tuple[str, ...] = (
    "max_output_tokens",
    "max_completion_tokens",
    "max_tokens",
)

# Fallback provider caps used only when dynamic model metadata is unavailable.
# These are conservative safety defaults to avoid provider-side validation errors.
PROVIDER_FALLBACK_MAX_TOKENS: dict[str, int] = {
    "groq": 16384,
    "cerebras": 8192,
    "together": 8192,
}
