"""
Skincare Product Advisor - Evaluate beauty products for your skin.

Rates skincare and beauty products based on ingredient safety,
personalized skin compatibility, and aggregated user reviews.
Maintains persistent memory of your skincare routine and product reactions.
"""

from .agent import SkincareAdvisorAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "SkincareAdvisorAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
