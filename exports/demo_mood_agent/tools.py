
import random
from core.framework.runner.tool_registry import tool

@tool(description="Suggest a mood based on a person's name")
def get_mood(name: str) -> str:
    moods = ["Energetic", "Zen", "Inspired", "Cheerful", "Mellow"]
    random.seed(sum(ord(c) for c in name))
    return random.choice(moods)

@tool(description="Format a mood string into a nice display message")
def display_mood(mood: str) -> str:
    return f"Today, you feel: **{mood}**! ✨"
