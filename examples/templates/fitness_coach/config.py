"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Fitness Coach Agent"
    version: str = "1.0.0"
    description: str = (
        "Conversational fitness coach that tracks daily calorie intake and burn "
        "via Google Sheets, generates personalized workout plans, and sends "
        "scheduled check-ins for meals and exercise reminders."
    )
    intro_message: str = (
        "Hey! I'm your personal fitness coach. Let's start by getting to know you — "
        "your goals, fitness level, diet preferences, and what equipment you have access to. "
        "Once we're set up, I'll track your meals and workouts in a Google Sheet and "
        "check in with you at meal times and every few hours for exercise. Ready?"
    )


metadata = AgentMetadata()
