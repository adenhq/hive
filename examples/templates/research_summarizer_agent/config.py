"""Runtime configuration."""

from dataclasses import dataclass
from framework.config import RuntimeConfig

default_config = RuntimeConfig()

@dataclass
class AgentMetadata:
    name: str = "Research and Summarization Agent"
    version: str = "1.0.0"
    description: str = (
        "Research any topic from the web and generate a clear structured summary "
        "with key insights and references."
    )
    intro_message: str = (
        "Hi! I'm your research assistant. Give me any topic and I'll research it "
        "from the web and produce a structured summary with key insights."
    )

metadata = AgentMetadata()
