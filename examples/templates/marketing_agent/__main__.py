
"""CLI entry point for GTM Marketing Agent."""

import argparse
import asyncio
import os
import sys

from .agent import MarketingAgent


async def run_agent(model: str = None):
    """Run the agent interactively."""
    agent = MarketingAgent()
    if model:
        agent.config.model = model

    print(f"[*] Starting {agent.info()['name']}...")
    print(f"Goal: {agent.info()['goal']['description']}")

    # Start the agent
    await agent.start()

    session_state = {}
    input_data = {}

    try:
        # First turn (Intake)
        result = await agent.trigger_and_wait("start", input_data, session_state=session_state)
        
        # Simple loop for human-in-the-loop if needed
        # (This is a simplified CLI runner logic)
        while result and result.paused_at:
            # For this specific agent, if it pauses, it's likely asking for user input
            user_input = input("\n> User Input: ")
            result = await agent.trigger_and_wait(
                "resume", 
                {"user_response": user_input}, 
                session_state=session_state
            )

        if result and result.success:
            print("\n[+] Agent completed successfully!")
            # Print final outputs
            for key, value in result.output.items():
                print(f"\n--- Output: {key} ---")
                print(value)
        else:
            print(f"\n[-] Agent failed: {result.error if result else 'Unknown error'}")

    finally:
        await agent.stop()


def main():
    parser = argparse.ArgumentParser(description="Run GTM Marketing Agent")
    parser.add_argument("--model", type=str, help="LLM model to use (e.g., gpt-4o)")
    args = parser.parse_args()

    asyncio.run(run_agent(args.model))


if __name__ == "__main__":
    main()
