#!/usr/bin/env python
"""RSS-to-Twitter Agent - Automated posting via Playwright."""

import asyncio
import json
import sys

sys.path.insert(0, "core")


async def main():
    from rss_twitter_agent.agent import RSSTwitterAgent

    print("=" * 60)
    print("RSS-to-Twitter Agent")
    print("=" * 60 + "\n")

    print("Generates tweets from RSS feeds and posts automatically.\n")
    print("Uses Playwright for browser automation.\n")


    agent = RSSTwitterAgent()
    await agent.start()

    # Step 1: Fetch RSS
    print("1. Fetching RSS...")
    from rss_twitter_agent.fetch import fetch_rss

    articles_json = fetch_rss()
    articles = json.loads(articles_json)
    print(f"   Fetched {len(articles)} articles\n")

    # Step 2: Summarize
    print("2. Summarizing articles...")
    from rss_twitter_agent.fetch import summarize_articles

    summaries_json = summarize_articles(articles_json)
    summaries = json.loads(summaries_json)
    print(f"   Summarized {len(summaries)} articles\n")

    # Steps 3-5: Generate → Approve → Post, one thread at a time
    from rss_twitter_agent.fetch import _generate_thread_for_article, post_to_twitter

    total_posted = 0

    for i, summary in enumerate(summaries):
        article_title = summary.get("title", "Untitled")

        print(f"\n{'=' * 60}")
        print(f"Article {i + 1}/{len(summaries)}: {article_title[:50]}{'...' if len(article_title) > 50 else ''}")
        print("=" * 60)

        # Generate thread for this article
        print("  Generating thread...")
        thread = _generate_thread_for_article(summary)
        if not thread:
            print("  ⚠️  Could not generate thread, skipping.")
            continue

        tweets = thread.get("tweets", [])

        # Display the thread
        print()
        for j, tweet in enumerate(tweets, 1):
            tweet_text = tweet.get("text", tweet) if isinstance(tweet, dict) else tweet
            prefix = "🧵" if j == 1 else f"{j}/"
            print(f"  {prefix} {tweet_text}")
            if len(tweet_text) > 280:
                print(f"     ⚠️  {len(tweet_text)} chars (over 280)")

        # Ask for approval
        print()
        try:
            response = input("Post this thread? (y/n/q): ").strip().lower()
        except EOFError:
            response = "n"

        if response == "q":
            print("  Quitting...")
            break
        elif response == "y":
            print("  Posting...\n")
            result_json = await post_to_twitter(json.dumps([thread]))
            result = json.loads(result_json)
            if isinstance(result, dict) and result.get("success"):
                total_posted += 1
                print(f"  ✅ Posted!")
            else:
                err = result.get("error", "Unknown error") if isinstance(result, dict) else result
                print(f"  ❌ Error: {err}")

            if i < len(summaries) - 1:
                try:
                    input("\nPress Enter for next thread...")
                except EOFError:
                    pass
        else:
            print("  ❌ Skipped")

    print(f"\n{'=' * 60}")
    print(f"Done! Posted {total_posted}/{len(summaries)} threads.")
    print("=" * 60)

    await agent.stop()


if __name__ == "__main__":
    sys.path.insert(0, "examples/template")
    asyncio.run(main())
