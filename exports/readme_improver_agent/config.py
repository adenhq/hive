"""Runtime configuration for README Improver Agent."""

from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    model: str = "anthropic/claude-3-haiku-20240307"
    temperature: float = 0.3  # Lower temperature for more consistent formatting
    max_tokens: int = 4096
    api_key: str | None = None
    api_base: str | None = None


default_config = RuntimeConfig()


# Agent metadata
@dataclass
class AgentMetadata:
    name: str = "README Improver Agent"
    version: str = "1.0.0"
    description: str = "Accept a file path to a text file or draft README, read the content, fix spelling errors, improve formatting to professional Markdown, and return the polished text."


metadata = AgentMetadata()
