"""Runtime configuration."""
from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    model: str = "ollama/llama3.2"
    temperature: float = 0.3  # Lower = more precise for financial analysis
    max_tokens: int = 4096


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Invoice Analyzer Agent"
    version: str = "1.0.0"
    description: str = "Analyzes invoices to detect hidden charges, unusual fees, and potential overcharges. Works offline with Ollama."


metadata = AgentMetadata()
