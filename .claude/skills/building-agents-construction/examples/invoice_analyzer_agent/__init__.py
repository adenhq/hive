"""
Invoice Analyzer Agent - Detect hidden charges in invoices.

Works offline with Ollama - no API keys required.
"""

from .agent import InvoiceAnalyzerAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "InvoiceAnalyzerAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
