import json
import sys
from typing import Dict
from datetime import datetime, timezone

import pyttsx3


class VoiceEngine:
    """
    Offline Text-to-Speech engine wrapper.
    """

    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 170)   # speaking speed
        self.engine.setProperty("volume", 1.0) # max volume

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()


class CustomerSupportAgent:
    """
    Production-style Customer Support Agent for Aden Hive.

    Capabilities:
    - Interactive terminal input
    - Intent classification
    - Text + Voice response
    - Human escalation logic
    """

    ESCALATION_KEYWORDS = [
        "refund",
        "complaint",
        "angry",
        "cancel",
        "fraud",
        "chargeback",
        "not happy",
    ]

    def __init__(self):
        self.voice = VoiceEngine()

    def run(self, input: Dict) -> Dict:
        query = input.get("query", "").strip().lower()

        if not query:
            return self._response(
                intent="invalid",
                message="No input provided. Please type a customer query.",
                escalated=False,
                confidence=0.0,
            )

        if self._needs_escalation(query):
            return self._response(
                intent="human_escalation",
                message="This issue requires human support. I am escalating it now.",
                escalated=True,
                confidence=0.93,
            )

        if any(word in query for word in ["hi", "hello", "hey"]):
            return self._response(
                intent="greeting",
                message="Hello! How can I assist you today?",
                escalated=False,
                confidence=0.85,
            )

        return self._response(
            intent="auto_resolved",
            message="Your query has been handled automatically. Let me know if you need anything else.",
            escalated=False,
            confidence=0.78,
        )

    def _needs_escalation(self, query: str) -> bool:
        return any(keyword in query for keyword in self.ESCALATION_KEYWORDS)

    def _response(
        self,
        intent: str,
        message: str,
        escalated: bool,
        confidence: float,
    ) -> Dict:
        response = {
            "intent": intent,
            "response": message,
            "escalated": escalated,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        #  Voice output
        self.voice.speak(message)

        return response


def interactive_mode():
    """
    Interactive terminal experience.
    """
    agent = CustomerSupportAgent()

    print("\n🟢 Customer Support Agent (Interactive Mode)")
    print("Type your query and press Enter.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input(" You: ").strip()

        if user_input.lower() in ["exit", "quit"]:
            print("\n👋 Goodbye!")
            break

        output = agent.run({"query": user_input})

        print("\n🤖 Agent Response:")
        print(json.dumps(output, indent=2))
        print("-" * 50)


#  Entry Point
if __name__ == "__main__":
    """
    Behavior:
    - python agent.py        → Interactive mode (recommended demo)
    - python agent.py JSON   → Single-run mode
    """

    if len(sys.argv) == 1:
        interactive_mode()
        sys.exit(0)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(
            json.dumps(
                {
                    "error": "Invalid JSON input",
                    "example": 'python agent.py \'{"query": "I want a refund"}\'',
                },
                indent=2,
            )
        )
        sys.exit(1)

    agent = CustomerSupportAgent()
    output = agent.run(input_data)
    print(json.dumps(output, indent=2))
