"""
README Improver Agent

Accept a file path to a text file or draft README, read the content,
fix spelling errors, improve formatting to professional Markdown
(adding headers and bullet points), and return the polished text.
"""

from .agent import ReadmeImproverAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "ReadmeImproverAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
