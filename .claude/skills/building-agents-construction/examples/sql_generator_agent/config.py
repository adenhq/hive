"""Runtime configuration."""
from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    model: str = "ollama/llama3.2"  # Local model (or use gemini/gemini-2.0-flash)
    temperature: float = 0.2  # Low = more precise SQL
    max_tokens: int = 4096


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "SQL Generator Agent"
    version: str = "1.0.0"
    description: str = "Generates SQL queries from natural language questions."


metadata = AgentMetadata()
