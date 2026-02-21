"""
Twitter/X Tool - Interact with Twitter/X API v2 for posting, searching, and managing tweets.

Supports:
- Bearer token authentication (TWITTER_BEARER_TOKEN)
- OAuth2 tokens via the credential store

Use Cases:
- Post tweets and replies
- Search tweets and users
- Get user information and followers
- Manage likes and retweets
- Get tweet metrics

API Reference: https://developer.x.com/en/docs/twitter-api/migrate
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

TWITTER_API_BASE = "https://api.twitter.com/2"


class _TwitterClient:
    """Internal client wrapping Twitter API v2 calls."""

    def __init__(self, bearer_token: str):
        self._token = bearer_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Twitter API response format."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Twitter API token"}
        if response.status_code == 403:
            return {"error": "Access forbidden. Check your API permissions."}
        if response.status_code == 429:
            return {"error": "Twitter API rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                error_data = response.json()
                return {"error": f"Twitter API error: {error_data}"}
            except Exception:
                return {"error": f"HTTP error {response.status_code}: {response.text}"}

        try:
            return response.json()
        except Exception:
            return {"error": "Failed to parse Twitter API response"}

    # --- Tweets ---

    def create_tweet(self, text: str, reply_to_id: str | None = None) -> dict[str, Any]:
        """Post a new tweet or reply."""
        body: dict[str, Any] = {"text": text}
        if reply_to_id:
            body["reply"] = {"in_reply_to_tweet_id": reply_to_id}

        response = httpx.post(
            f"{TWITTER_API_BASE}/tweets",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_tweet(self, tweet_id: str, expansions: str | None = None) -> dict[str, Any]:
        """Get a tweet by ID."""
        params: dict[str, Any] = {
            "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
        }
        if expansions:
            params["expansions"] = expansions

        response = httpx.get(
            f"{TWITTER_API_BASE}/tweets/{tweet_id}",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Delete a tweet."""
        response = httpx.delete(
            f"{TWITTER_API_BASE}/tweets/{tweet_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "deleted_tweet_id": tweet_id}
        return self._handle_response(response)

    def search_tweets(
        self, query: str, max_results: int = 10, since_id: str | None = None
    ) -> dict[str, Any]:
        """Search for recent tweets."""
        params: dict[str, Any] = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
        }
        if since_id:
            params["since_id"] = since_id

        response = httpx.get(
            f"{TWITTER_API_BASE}/tweets/search/recent",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_user_tweets(
        self, user_id: str, max_results: int = 10, since_id: str | None = None
    ) -> dict[str, Any]:
        """Get tweets from a specific user."""
        params: dict[str, Any] = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics",
        }
        if since_id:
            params["since_id"] = since_id

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    # --- Likes ---

    def like_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Like a tweet."""
        response = httpx.post(
            f"{TWITTER_API_BASE}/users/me/likes",
            headers=self._headers,
            json={"tweet_id": tweet_id},
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "liked_tweet_id": tweet_id}
        return self._handle_response(response)

    def unlike_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Unlike a tweet."""
        response = httpx.delete(
            f"{TWITTER_API_BASE}/users/me/likes/{tweet_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "unliked_tweet_id": tweet_id}
        return self._handle_response(response)

    def get_user_likes(self, user_id: str, max_results: int = 10) -> dict[str, Any]:
        """Get tweets a user has liked."""
        params: dict[str, Any] = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics",
        }

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}/liked_tweets",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    # --- Retweets ---

    def retweet(self, tweet_id: str) -> dict[str, Any]:
        """Retweet a tweet."""
        response = httpx.post(
            f"{TWITTER_API_BASE}/users/me/retweets",
            headers=self._headers,
            json={"tweet_id": tweet_id},
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "retweeted_tweet_id": tweet_id}
        return self._handle_response(response)

    def unretweet(self, tweet_id: str) -> dict[str, Any]:
        """Undo a retweet."""
        response = httpx.delete(
            f"{TWITTER_API_BASE}/users/me/retweets/{tweet_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "unretweeted_tweet_id": tweet_id}
        return self._handle_response(response)

    # --- Users ---

    def get_me(self) -> dict[str, Any]:
        """Get the authenticated user's profile."""
        response = httpx.get(
            f"{TWITTER_API_BASE}/users/me",
            headers=self._headers,
            params={"user.fields": "created_at,description,public_metrics"},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_user_by_username(self, username: str) -> dict[str, Any]:
        """Get a user by their username."""
        # Remove @ if present
        username = username.lstrip("@")

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            headers=self._headers,
            params={"user.fields": "created_at,description,public_metrics"},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a user by ID."""
        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}",
            headers=self._headers,
            params={"user.fields": "created_at,description,public_metrics"},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_user_followers(self, user_id: str, max_results: int = 10) -> dict[str, Any]:
        """Get followers of a user."""
        params: dict[str, Any] = {
            "max_results": min(max_results, 1000),
            "user.fields": "created_at,description,public_metrics",
        }

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}/followers",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_user_following(self, user_id: str, max_results: int = 10) -> dict[str, Any]:
        """Get users that a user follows."""
        params: dict[str, Any] = {
            "max_results": min(max_results, 1000),
            "user.fields": "created_at,description,public_metrics",
        }

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}/following",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def follow_user(self, user_id: str) -> dict[str, Any]:
        """Follow a user."""
        response = httpx.post(
            f"{TWITTER_API_BASE}/users/me/following",
            headers=self._headers,
            json={"target_user_id": user_id},
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "followed_user_id": user_id}
        return self._handle_response(response)

    def unfollow_user(self, user_id: str) -> dict[str, Any]:
        """Unfollow a user."""
        response = httpx.delete(
            f"{TWITTER_API_BASE}/users/me/following/{user_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "unfollowed_user_id": user_id}
        return self._handle_response(response)

    # --- Bookmarks ---

    def bookmark_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Bookmark a tweet."""
        response = httpx.post(
            f"{TWITTER_API_BASE}/users/me/bookmarks",
            headers=self._headers,
            json={"tweet_id": tweet_id},
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "bookmarked_tweet_id": tweet_id}
        return self._handle_response(response)

    def remove_bookmark(self, tweet_id: str) -> dict[str, Any]:
        """Remove a bookmark."""
        response = httpx.delete(
            f"{TWITTER_API_BASE}/users/me/bookmarks/{tweet_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if response.status_code == 200:
            return {"success": True, "removed_bookmark_tweet_id": tweet_id}
        return self._handle_response(response)

    def get_bookmarks(self, max_results: int = 10) -> dict[str, Any]:
        """Get user's bookmarks."""
        params: dict[str, Any] = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics",
        }

        response = httpx.get(
            f"{TWITTER_API_BASE}/users/me/bookmarks",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Twitter tools with the MCP server."""

    def _get_token() -> str | dict[str, str]:
        """Get Twitter bearer token from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("twitter")
            if token and isinstance(token, str):
                return token
        else:
            token = os.getenv("TWITTER_BEARER_TOKEN")
            if token:
                return token

        return {
            "error": "Twitter credentials not configured",
            "help": (
                "Set TWITTER_BEARER_TOKEN environment variable. "
                "Get your bearer token from https://developer.x.com/"
            ),
        }

    def _get_client() -> _TwitterClient | dict[str, str]:
        """Get a Twitter client, or return an error dict if no credentials."""
        token = _get_token()
        if isinstance(token, dict):
            return token
        return _TwitterClient(token)

    # --- Tweets ---

    @mcp.tool()
    def twitter_create_tweet(
        text: str,
        reply_to_tweet_id: str | None = None,
    ) -> dict:
        """
        Post a new tweet or reply to an existing tweet.

        Args:
            text: The text content of your tweet (max 280 characters)
            reply_to_tweet_id: Optional tweet ID to reply to

        Returns:
            Dict with tweet details or error

        Example:
            twitter_create_tweet(text="Hello from my AI agent!")
            twitter_create_tweet(text="Great point!", reply_to_tweet_id="1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not text or len(text.strip()) == 0:
            return {"error": "Tweet text cannot be empty"}
        if len(text) > 280:
            return {"error": "Tweet exceeds 280 characters"}

        try:
            result = client.create_tweet(text, reply_to_tweet_id)
            if "data" in result:
                return {
                    "success": True,
                    "tweet_id": result["data"]["id"],
                    "text": result["data"]["text"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_tweet(tweet_id: str) -> dict:
        """
        Get details of a specific tweet.

        Args:
            tweet_id: The tweet ID to retrieve

        Returns:
            Dict with tweet details or error

        Example:
            twitter_get_tweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            result = client.get_tweet(tweet_id)
            if "data" in result:
                return {
                    "success": True,
                    "tweet": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_delete_tweet(tweet_id: str) -> dict:
        """
        Delete a tweet you posted.

        Args:
            tweet_id: The tweet ID to delete

        Returns:
            Dict with success status or error

        Example:
            twitter_delete_tweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.delete_tweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_search_tweets(
        query: str,
        max_results: int = 10,
        since_tweet_id: str | None = None,
    ) -> dict:
        """
        Search for recent tweets matching a query.

        Args:
            query: Search query (supports Twitter's search operators)
            max_results: Number of results (1-100, default 10)
            since_tweet_id: Return tweets after this ID

        Returns:
            Dict with matching tweets or error

        Example:
            twitter_search_tweets(query="AI OR artificial intelligence", max_results=20)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not query or len(query.strip()) == 0:
            return {"error": "Search query is required"}

        try:
            result = client.search_tweets(query, max_results, since_tweet_id)
            if "data" in result:
                return {
                    "success": True,
                    "count": len(result["data"]),
                    "tweets": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_user_tweets(
        username: str,
        max_results: int = 10,
        since_tweet_id: str | None = None,
    ) -> dict:
        """
        Get recent tweets from a specific user.

        Args:
            username: Twitter username (without @)
            max_results: Number of tweets (1-100, default 10)
            since_tweet_id: Return tweets after this ID

        Returns:
            Dict with user's tweets or error

        Example:
            twitter_get_user_tweets(username="elonmusk", max_results=20)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # First get user ID from username
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            result = client.get_user_tweets(user_id, max_results, since_tweet_id)
            if "data" in result:
                return {
                    "success": True,
                    "username": username,
                    "count": len(result["data"]),
                    "tweets": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Likes ---

    @mcp.tool()
    def twitter_like_tweet(tweet_id: str) -> dict:
        """
        Like a tweet.

        Args:
            tweet_id: The tweet ID to like

        Returns:
            Dict with success status or error

        Example:
            twitter_like_tweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.like_tweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_unlike_tweet(tweet_id: str) -> dict:
        """
        Unlike a tweet.

        Args:
            tweet_id: The tweet ID to unlike

        Returns:
            Dict with success status or error

        Example:
            twitter_unlike_tweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.unlike_tweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_user_likes(username: str, max_results: int = 10) -> dict:
        """
        Get tweets a user has liked.

        Args:
            username: Twitter username (without @)
            max_results: Number of results (1-100, default 10)

        Returns:
            Dict with liked tweets or error

        Example:
            twitter_get_user_likes(username="elonmusk", max_results=20)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # First get user ID
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            result = client.get_user_likes(user_id, max_results)
            if "data" in result:
                return {
                    "success": True,
                    "username": username,
                    "count": len(result["data"]),
                    "tweets": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Retweets ---

    @mcp.tool()
    def twitter_retweet(tweet_id: str) -> dict:
        """
        Retweet a tweet.

        Args:
            tweet_id: The tweet ID to retweet

        Returns:
            Dict with success status or error

        Example:
            twitter_retweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.retweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_unretweet(tweet_id: str) -> dict:
        """
        Undo a retweet.

        Args:
            tweet_id: The original tweet ID to unretweet

        Returns:
            Dict with success status or error

        Example:
            twitter_unretweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.unretweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Users ---

    @mcp.tool()
    def twitter_get_me() -> dict:
        """
        Get the authenticated user's profile information.

        Returns:
            Dict with user profile or error

        Example:
            twitter_get_me()
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        try:
            result = client.get_me()
            if "data" in result:
                return {
                    "success": True,
                    "user": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_user(username: str) -> dict:
        """
        Get a user's profile information by username.

        Args:
            username: Twitter username (without @)

        Returns:
            Dict with user profile or error

        Example:
            twitter_get_user(username="elonmusk")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        try:
            result = client.get_user_by_username(username)
            if "data" in result:
                return {
                    "success": True,
                    "user": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_followers(username: str, max_results: int = 10) -> dict:
        """
        Get followers of a user.

        Args:
            username: Twitter username (without @)
            max_results: Number of results (1-1000, default 10)

        Returns:
            Dict with follower list or error

        Example:
            twitter_get_followers(username="elonmusk", max_results=50)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # Get user ID
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            result = client.get_user_followers(user_id, max_results)
            if "data" in result:
                return {
                    "success": True,
                    "username": username,
                    "count": len(result["data"]),
                    "followers": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_following(username: str, max_results: int = 10) -> dict:
        """
        Get users that a user follows.

        Args:
            username: Twitter username (without @)
            max_results: Number of results (1-1000, default 10)

        Returns:
            Dict with following list or error

        Example:
            twitter_get_following(username="elonmusk", max_results=50)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # Get user ID
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            result = client.get_user_following(user_id, max_results)
            if "data" in result:
                return {
                    "success": True,
                    "username": username,
                    "count": len(result["data"]),
                    "following": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_follow_user(username: str) -> dict:
        """
        Follow a user.

        Args:
            username: Twitter username to follow (without @)

        Returns:
            Dict with success status or error

        Example:
            twitter_follow_user(username="elonmusk")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # Get user ID
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            return client.follow_user(user_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_unfollow_user(username: str) -> dict:
        """
        Unfollow a user.

        Args:
            username: Twitter username to unfollow (without @)

        Returns:
            Dict with success status or error

        Example:
            twitter_unfollow_user(username="elonmusk")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not username:
            return {"error": "username is required"}

        # Get user ID
        user_result = client.get_user_by_username(username)
        if "error" in user_result:
            return user_result

        if "data" not in user_result:
            return {"error": f"User not found: {username}"}

        user_id = user_result["data"]["id"]

        try:
            return client.unfollow_user(user_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Bookmarks ---

    @mcp.tool()
    def twitter_bookmark_tweet(tweet_id: str) -> dict:
        """
        Bookmark a tweet for later.

        Args:
            tweet_id: The tweet ID to bookmark

        Returns:
            Dict with success status or error

        Example:
            twitter_bookmark_tweet("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.bookmark_tweet(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_remove_bookmark(tweet_id: str) -> dict:
        """
        Remove a bookmark.

        Args:
            tweet_id: The tweet ID to remove from bookmarks

        Returns:
            Dict with success status or error

        Example:
            twitter_remove_bookmark("1234567890")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not tweet_id:
            return {"error": "tweet_id is required"}

        try:
            return client.remove_bookmark(tweet_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def twitter_get_bookmarks(max_results: int = 10) -> dict:
        """
        Get your bookmarked tweets.

        Args:
            max_results: Number of results (1-100, default 10)

        Returns:
            Dict with bookmarked tweets or error

        Example:
            twitter_get_bookmarks(max_results=20)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        try:
            result = client.get_bookmarks(max_results)
            if "data" in result:
                return {
                    "success": True,
                    "count": len(result["data"]),
                    "bookmarks": result["data"],
                }
            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
