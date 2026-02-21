"""Twitter posting via Playwright — fully automated, session-persistent.

First run: browser opens visibly for manual login → session saved.
Subsequent runs: headless posting, no login needed.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

TwitterConfig = Any

SESSION_DIR = Path.home() / ".hive" / "twitter_session"
SESSION_MARKER = SESSION_DIR / ".logged_in"


def _is_logged_in() -> bool:
    """Check if a saved session exists."""
    return SESSION_MARKER.exists()


async def _post_thread_with_playwright(thread: dict) -> dict:
    """Post a single thread (list of tweets) using Playwright async API."""
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    tweets = thread.get("thread") or thread.get("tweets") or []
    title = thread.get("article_title") or thread.get("title", "Untitled")

    if not tweets:
        return {"title": title, "posted": 0, "error": "No tweets in thread"}

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    first_run = not _is_logged_in()

    print(f"\n{'=' * 60}")
    print(f"Thread: {title[:55]}{'...' if len(title) > 55 else ''}")
    print(f"Tweets: {len(tweets)}")
    print("=" * 60)

    if first_run:
        print("\n⚠️  FIRST RUN — Browser will open for manual login.")
        print("   Log in to X/Twitter, then press Enter here to continue.\n")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,          # Always headed — less bot detection
            slow_mo=80,              # Human-like timing
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            viewport={"width": 1280, "height": 800},
        )

        page = await context.new_page()

        # ── First run: let user log in ──────────────────────────────────────
        if first_run:
            await page.goto("https://x.com/login", wait_until="domcontentloaded")
            # Use asyncio-compatible input
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: input("   → Log in to X in the browser, then press Enter here: ")
            )
            # Verify we're actually logged in
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            if "login" in page.url or "i/flow" in page.url:
                await context.close()
                return {"title": title, "posted": 0, "error": "Login not detected. Please try again."}
            SESSION_MARKER.touch()
            print("   ✅ Session saved — future runs will be fully automatic!\n")

        # ── Post each tweet ─────────────────────────────────────────────────
        posted = 0
        first_tweet_url = None

        for i, tweet_text in enumerate(tweets):
            if isinstance(tweet_text, dict):
                tweet_text = tweet_text.get("text", "")
            tweet_text = tweet_text.strip()
            if not tweet_text:
                continue

            print(f"\n  Posting tweet {i + 1}/{len(tweets)}...")

            try:
                if i == 0:
                    # First tweet: open compose
                    await page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)

                    # Handle any login redirect
                    if "login" in page.url or "i/flow" in page.url:
                        SESSION_MARKER.unlink(missing_ok=True)
                        await context.close()
                        return {
                            "title": title,
                            "posted": posted,
                            "error": "Session expired. Delete ~/.hive/twitter_session and re-run.",
                        }

                    # Find the tweet textarea
                    textarea = page.locator(
                        "[data-testid='tweetTextarea_0'], "
                        "div[role='textbox'][data-testid='tweetTextarea_0'], "
                        "div.public-DraftEditor-content"
                    ).first
                    await textarea.wait_for(timeout=10000)
                    await textarea.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(tweet_text, delay=30)
                    await asyncio.sleep(0.8)

                    # Click the Post button
                    post_btn = page.locator(
                        "[data-testid='tweetButtonInline'], "
                        "[data-testid='tweetButton']"
                    ).first
                    await post_btn.wait_for(timeout=8000)
                    await post_btn.click()
                    await asyncio.sleep(2.5)

                    # Capture the URL of the posted tweet
                    first_tweet_url = page.url
                    posted += 1
                    print(f"  ✅ Tweet 1 posted")

                else:
                    # Reply tweets: navigate to the first tweet and reply
                    if first_tweet_url and "status" in first_tweet_url:
                        await page.goto(first_tweet_url, wait_until="domcontentloaded")
                        await asyncio.sleep(1.5)

                        # Click the Reply button
                        reply_btn = page.locator("[data-testid='reply']").first
                        await reply_btn.wait_for(timeout=8000)
                        await reply_btn.click()
                        await asyncio.sleep(1.0)
                    else:
                        # Fallback: use compose
                        await page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded")
                        await asyncio.sleep(1.5)

                    # Find reply textarea
                    textarea = page.locator(
                        "div[data-testid='tweetTextarea_0'], "
                        "div[role='textbox']"
                    ).last
                    await textarea.wait_for(timeout=10000)
                    await textarea.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(tweet_text, delay=30)
                    await asyncio.sleep(0.8)

                    # Click Post/Reply button
                    post_btn = page.locator(
                        "[data-testid='tweetButtonInline'], "
                        "[data-testid='tweetButton']"
                    ).first
                    await post_btn.wait_for(timeout=8000)
                    await post_btn.click()
                    await asyncio.sleep(2.5)

                    posted += 1
                    print(f"  ✅ Tweet {i + 1} posted")

            except PlaywrightTimeout as e:
                print(f"  ⚠️  Timeout on tweet {i + 1}: {e}")
            except Exception as e:
                print(f"  ❌ Error on tweet {i + 1}: {e}")

        await context.close()

    return {
        "title": title,
        "posted": posted,
        "total": len(tweets),
        "url": first_tweet_url,
    }


async def post_threads_impl(threads_json: str, config: TwitterConfig) -> str | dict[str, Any]:
    """
    Post threads to Twitter/X via Playwright automation.

    First run: opens browser for manual login, saves session.
    Subsequent runs: fully automatic.
    """
    try:
        threads = json.loads(threads_json)
    except (json.JSONDecodeError, TypeError) as e:
        return f"Invalid threads_json: {e!s}"

    if not isinstance(threads, list):
        return "threads_json must be a JSON array of thread objects."

    if not threads:
        return "No threads to post."

    results = []
    total_posted = 0

    for thread in threads:
        if not isinstance(thread, dict):
            continue
        result = await _post_thread_with_playwright(thread)
        results.append(result)
        total_posted += result.get("posted", 0)

    return {
        "success": True,
        "threads": results,
        "message": f"Posted {total_posted} tweets across {len(results)} threads",
    }


def register_twitter_tool(registry: Any, config: TwitterConfig) -> None:
    """Register the post_to_twitter tool."""
    from framework.llm.provider import Tool

    tool = Tool(
        name="post_to_twitter",
        description=(
            "Post threads to Twitter/X using Playwright automation. "
            "First run opens browser for login; subsequent runs are fully automatic."
        ),
        parameters={
            "type": "object",
            "properties": {
                "threads_json": {
                    "type": "string",
                    "description": "JSON string of the threads array.",
                },
            },
            "required": ["threads_json"],
        },
    )
    registry.register(
        "post_to_twitter",
        tool,
        lambda inputs: post_threads_impl(inputs["threads_json"], config),
    )
