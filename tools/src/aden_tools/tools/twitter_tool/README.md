# Twitter/X Tool

Integration with Twitter/X API v2 for posting, searching, and managing tweets.

## Overview

This tool enables Hive agents to interact with Twitter/X for:
- Posting tweets and replies
- Searching tweets and users
- Getting user information and followers
- Managing likes and retweets
- Managing bookmarks

## Available Tools

This integration provides 19 MCP tools for Twitter operations:

### Tweets
- `twitter_create_tweet` - Post a new tweet or reply
- `twitter_get_tweet` - Get a tweet by ID
- `twitter_delete_tweet` - Delete a tweet
- `twitter_search_tweets` - Search for recent tweets
- `twitter_get_user_tweets` - Get tweets from a specific user

### Likes
- `twitter_like_tweet` - Like a tweet
- `twitter_unlike_tweet` - Unlike a tweet
- `twitter_get_user_likes` - Get tweets a user has liked

### Retweets
- `twitter_retweet` - Retweet a tweet
- `twitter_unretweet` - Undo a retweet

### Users
- `twitter_get_me` - Get authenticated user's profile
- `twitter_get_user` - Get a user's profile by username
- `twitter_get_followers` - Get followers of a user
- `twitter_get_following` - Get users a user follows
- `twitter_follow_user` - Follow a user
- `twitter_unfollow_user` - Unfollow a user

### Bookmarks
- `twitter_bookmark_tweet` - Bookmark a tweet
- `twitter_remove_bookmark` - Remove a bookmark
- `twitter_get_bookmarks` - Get bookmarked tweets

## Setup

### 1. Get Twitter API Credentials

1. Apply for a developer account at [developer.x.com](https://developer.x.com/)
2. Create a project and app in the developer portal
3. Generate a **Bearer Token** (for App-only authentication)

### 2. Configure Environment Variables

```bash
export TWITTER_BEARER_TOKEN="your_bearer_token_here"
```

**Important:** Never commit your bearer token to version control.

## Usage

### twitter_create_tweet

```python
twitter_create_tweet(text="Hello from my AI agent!")
twitter_create_tweet(text="Great point!", reply_to_tweet_id="1234567890")
```

### twitter_search_tweets

```python
twitter_search_tweets(query="AI OR artificial intelligence", max_results=20)
```

### twitter_get_user

```python
twitter_get_user(username="elonmusk")
```

### twitter_get_followers

```python
twitter_get_followers(username="elonmusk", max_results=50)
```

### twitter_follow_user

```python
twitter_follow_user(username="aden")
```

## Authentication

Twitter uses Bearer token authentication. Set `TWITTER_BEARER_TOKEN` environment variable. For write operations (posting, liking, following), you'll need a project with elevated access.

## Error Handling

All tools return error dicts on failure:

```json
{
  "error": "Twitter credentials not configured"
}
```

Common errors:
- Invalid token - check TWITTER_BEARER_TOKEN is correct
- Rate limit - wait before making more requests
- Insufficient permissions - verify your app has correct scopes

## API Reference

- [Twitter API v2 Docs](https://developer.x.com/en/docs/twitter-api/migrate)
- [Bearer Token Guide](https://developer.x.com/en/docs/authentication/oauth-2-0)
