import asyncio
from core.framework.runner import AgentRunner

async def main():
    runner = AgentRunner.load("./examples/templates/research_summarizer_agent")


    result = await runner.run({
        "topic": "latest AI news"
    })

    print(result)

asyncio.run(main())