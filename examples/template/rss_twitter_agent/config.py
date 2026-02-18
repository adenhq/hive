"""Runtime configuration for RSS-to-Twitter Agent with Ollama."""

from __future__ import annotations

import httpx
from dataclasses import dataclass, field

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "ollama/llama3.1:8b"


def _check_ollama_running() -> bool:
    """Check if Ollama is running locally."""
    try:
        with httpx.Client() as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
            return resp.status_code == 200
    except Exception:
        return False


def _get_model() -> str:
    """Get the model, defaulting to Ollama."""
    return DEFAULT_MODEL


@dataclass
class RuntimeConfig:
    model: str = field(default_factory=_get_model)
    temperature: float = 0.7
    max_tokens: int = 8000
    api_key: str | None = None
    api_base: str | None = None


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "RSS-to-Twitter Agent"
    version: str = "1.0.0"
    description: str = (
        "Automated content repurposing from RSS feeds to Twitter threads. "
        "Uses Ollama (llama3.1:8b) for free local LLM inference and Playwright "
        "for fully automated posting — no paid APIs required."
    )


metadata = AgentMetadata()


def validate_ollama() -> tuple[bool, str]:
    """
    Validate that Ollama is running and accessible.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not _check_ollama_running():
        return (
            False,
            "\n"
            "ERROR: Ollama is not running!\n"
            "\n"
            "This agent requires Ollama to be running locally. "
            "Please install and start Ollama:\n"
            "\n"
            "  # Install Ollama (macOS)\n"
            "  brew install ollama\n"
            "\n"
            "  # Start the Ollama server\n"
            "  ollama serve\n"
            "\n"
            "  # Pull the llama3.1:8b model (in a new terminal)\n"
            "  ollama pull llama3.1:8b\n"
            "\n"
            "Once Ollama is running, try again.\n",
        )
    return True, ""
