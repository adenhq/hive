from dataclasses import dataclass

@dataclass
class AgentConfig:
    model: str = "gpt-4o"
    max_tokens: int = 4096
    api_key: str | None = None
    api_base: str | None = None

default_config = AgentConfig()

@dataclass
class AgentMetadata:
    name: str = "GTM Marketing Agent"
    version: str = "0.1.0"
    description: str = "Analyzes competitors and drafts marketing content strategies."

metadata = AgentMetadata()
