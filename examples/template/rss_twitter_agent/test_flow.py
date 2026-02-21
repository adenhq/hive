#!/usr/bin/env python
"""Test the full RSS-to-Twitter agent flow with simulated approval."""

import asyncio
import json
import sys

sys.path.insert(0, "core")

APPROVED_COUNT = 1


def mock_approve_threads(threads_json: str) -> str:
    """Mock approval that auto-approves the first thread."""
    threads = json.loads(threads_json) if threads_json else []
    if not threads:
        return json.dumps([])

    print("\n" + "=" * 60)
    print("GENERATED TWEET THREADS")
    print("=" * 60 + "\n")

    for i, thread in enumerate(threads, 1):
        title = thread.get("title", "Untitled")
        tweets = thread.get("tweets", [])

        print(f"\n--- Thread {i}: {title[:50]}{'...' if len(title) > 50 else ''} ---\n")

        for j, tweet in enumerate(tweets, 1):
            prefix = "🧵" if j == 1 else f"{j}/"
            print(
                f"  {prefix} {tweet[:80]}..."
                if len(tweet) > 80
                else f"  {prefix} {tweet}"
            )

    approved = threads[:APPROVED_COUNT]
    print("\n" + "=" * 60)
    print(f"AUTO-APPROVED: {len(approved)}/{len(threads)} threads (simulated)")
    print("=" * 60 + "\n")

    return json.dumps(approved)


async def test_full_flow():
    """Test the complete agent flow."""
    from rss_twitter_agent.agent import RSSTwitterAgent
    from rss_twitter_agent import fetch

    original_approve = fetch.approve_threads
    fetch.approve_threads = mock_approve_threads

    print("=== FULL AGENT FLOW TEST ===\n")

    agent = RSSTwitterAgent()
    await agent.start()

    print("Running agent pipeline...")
    print("  1. fetch -> 2. process -> 3. generate -> 4. approve -> 5. post\n")

    result = await agent.trigger_and_wait("start", {}, timeout=120)

    if result:
        print(f"\nSuccess: {result.success}")
        if result.error:
            print(f"Error: {result.error}")

        if result.output:
            print(f"\nOutput keys: {list(result.output.keys())}")

            if "articles_json" in result.output:
                articles = json.loads(result.output["articles_json"])
                print(f"  - Articles fetched: {len(articles)}")

            if "processed_json" in result.output:
                processed = json.loads(result.output["processed_json"])
                print(f"  - Articles processed: {len(processed)}")

            if "threads_json" in result.output:
                threads = json.loads(result.output["threads_json"])
                print(f"  - Threads generated: {len(threads)}")

            if "approved_json" in result.output:
                approved = json.loads(result.output["approved_json"])
                print(f"  - Threads approved: {len(approved)}")

            if "results_json" in result.output:
                results = json.loads(result.output["results_json"])
                if isinstance(results, dict):
                    print(
                        f"  - Posting result: {results.get('posted', 0)} threads posted"
                    )

        print("\n=== FLOW TEST COMPLETE ===")

    else:
        print("No result returned")

    await agent.stop()
    fetch.approve_threads = original_approve


if __name__ == "__main__":
    sys.path.insert(0, "examples/template")
    asyncio.run(test_full_flow())
