"""
Fitness Coach Agent — Track calories, generate workouts, stay on schedule.

Conversational fitness coach that tracks daily calorie intake and burn via
Google Sheets, generates personalized workout plans, and sends scheduled
check-ins for meals and exercise reminders.
"""

from .agent import (
    FitnessCoachAgent,
    default_agent,
    goal,
    nodes,
    edges,
    loop_config,
    async_entry_points,
    entry_node,
    entry_points,
    pause_nodes,
    terminal_nodes,
    conversation_mode,
    identity_prompt,
)
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "FitnessCoachAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "loop_config",
    "async_entry_points",
    "entry_node",
    "entry_points",
    "pause_nodes",
    "terminal_nodes",
    "conversation_mode",
    "identity_prompt",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
