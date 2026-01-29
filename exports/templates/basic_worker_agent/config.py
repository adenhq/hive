from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    # Required by GraphSpec even if mock_mode=True
    model: str = "mock"
    max_tokens: int = 1024


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Basic Worker Agent"
    version: str = "0.1.0"
    description: str = "Minimal noop worker agent template"


metadata = AgentMetadata()
