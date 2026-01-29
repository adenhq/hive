# Customer Support Agent (Interactive + Voice)

This is a runnable, interactive customer support agent built using the
Aden Hive framework.

The agent demonstrates how outcome-driven AI agents can:
- Accept real-time user input
- Classify intent
- Escalate sensitive issues to humans
- Respond using both text and voice

---

## Features

- Interactive terminal-based chat
- Voice (text-to-speech) responses
- Intent classification (refund, complaint, greeting, general)
- Human-in-the-loop escalation
- Demo-first and production-friendly design

---

## Requirements

- Python 3.11+
- Offline Text-to-Speech support via `pyttsx3`

Install dependency:

```bash
##pip install pyttsx3



## Example Interaction
'''
👤 You: I want a refund

🤖 Agent:
- Intent: human_escalation
- Response: This issue requires human support. I am escalating it now.
- Escalated: true'''