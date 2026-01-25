"""
A minimal example to help new contributors get started with Hive agents.
This script demonstrates how to define an agent, set a goal, and run it.
"""

from hive.core.agent import Agent

def main():
    # 1. Initialize a simple agent with a clear role and goal
    # This helps beginners understand the basic parameters
    support_agent = Agent(
        name="GuideBot",
        role="Onboarding Assistant",
        goal="Provide a friendly introduction to the Hive framework."
    )

    print("--- Starting Hive Onboarding Example ---")

    # 2. Define a simple prompt for the agent
    user_input = "Hello! I'm Abhishek, a new contributor. Can you briefly explain what you do?"

    try:
        # 3. Execute the agent and capture the result
        # We use a try-except block to handle potential API or setup errors gracefully
        print(f"User: {user_input}")
        
        response = support_agent.run(user_input)
        
        print("\n--- Agent's Response ---")
        print(response)
        
    except Exception as e:
        # If something goes wrong (like missing API keys), we give a helpful tip
        print(f"\n[Tip] Make sure your environment variables are set up correctly!")
        print(f"Detailed Error: {e}")

if __name__ == "__main__":
    main()
