# Messaging Tool

Send messages to Slack and Discord from Hive agents.

## Description

A unified messaging interface for integrating Hive agents with popular team communication platforms. Supports:

- **Slack**: Full integration via Bot Token (send, read, react, upload files, list channels)
- **Discord**: Webhook-based integration (send messages, upload files)

## Features

| Feature | Slack | Discord |
|---------|-------|---------|
| Send messages | ✅ | ✅ |
| Read messages | ✅ | ❌ |
| Add reactions | ✅ | ❌ |
| Upload files | ✅ | ✅ |
| List channels | ✅ | ❌ |
| Thread replies | ✅ | ✅ |
| Rich formatting | ✅ (Blocks) | ✅ (Embeds) |

## Setup

### Slack Setup

1. Create a Slack App at https://api.slack.com/apps
2. Add the following Bot Token Scopes under "OAuth & Permissions":
   - `chat:write` - Send messages
   - `channels:history` - Read public channel messages
   - `channels:read` - List channels
   - `reactions:write` - Add reactions
   - `files:write` - Upload files
3. Install the app to your workspace
4. Copy the Bot User OAuth Token (starts with `xoxb-`)
5. Set the environment variable:
   ```bash
   export SLACK_BOT_TOKEN=xoxb-your-token-here
   ```

### Discord Setup

1. Open your Discord server
2. Go to Server Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Configure the webhook (name, channel, avatar)
5. Copy the Webhook URL
6. Set the environment variable:
   ```bash
   export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

## Tools

### messaging_send

Send a message to Slack or Discord.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `platform` | str | Yes | - | Platform: "slack" or "discord" |
| `message` | str | Yes | - | Message text (markdown supported) |
| `channel` | str | Slack only | "" | Channel ID (e.g., "C1234567890") |
| `thread_id` | str | No | "" | Thread ID for replies (Slack: message timestamp) |
| `username` | str | No | "" | Override bot username (Discord only) |
| `avatar_url` | str | No | "" | Override bot avatar (Discord only) |

**Example:**
```python
# Slack
messaging_send(platform="slack", channel="C123", message="Hello team!")

# Discord
messaging_send(platform="discord", message="Alert: Build completed!")
```

### messaging_read

Read recent messages from a Slack channel.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `channel` | str | Yes | - | Slack channel ID |
| `limit` | int | No | 10 | Number of messages (1-100) |
| `before` | str | No | "" | Fetch messages before this timestamp |

**Example:**
```python
result = messaging_read(channel="C123", limit=5)
for msg in result["messages"]:
    print(f"{msg['author']}: {msg['content']}")
```

### messaging_react

Add an emoji reaction to a Slack message.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `channel` | str | Yes | - | Channel ID containing the message |
| `message_id` | str | Yes | - | Message timestamp (ts) |
| `emoji` | str | Yes | - | Emoji name without colons (e.g., "thumbsup") |

**Example:**
```python
messaging_react(channel="C123", message_id="1234567890.123456", emoji="white_check_mark")
```

### messaging_upload

Upload a file to Slack or Discord.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `platform` | str | Yes | - | Platform: "slack" or "discord" |
| `filename` | str | Yes | - | Name for the file |
| `content` | str | Yes | - | File content as string |
| `channel` | str | Slack only | "" | Channel ID for Slack |
| `title` | str | No | "" | File title (Slack only) |
| `comment` | str | No | "" | Message to accompany the file |

**Example:**
```python
messaging_upload(
    platform="slack",
    channel="C123",
    filename="report.txt",
    content="Here is the daily report...",
    title="Daily Report",
    comment="Please review"
)
```

### messaging_list_channels

List available Slack channels.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `include_private` | bool | No | False | Include private channels |
| `limit` | int | No | 100 | Maximum channels to return (1-1000) |

**Example:**
```python
result = messaging_list_channels(include_private=False, limit=50)
for ch in result["channels"]:
    print(f"#{ch['name']} ({ch['id']})")
```

### messaging_validate

Validate messaging credentials for a platform.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `platform` | str | Yes | - | Platform: "slack" or "discord" |

**Example:**
```python
result = messaging_validate(platform="slack")
if result["valid"]:
    print(f"Connected as {result['user']} to {result['team']}")
else:
    print(f"Error: {result['error']}")
```

## Environment Variables

| Variable | Required For | Description |
|----------|--------------|-------------|
| `SLACK_BOT_TOKEN` | Slack | Bot OAuth Token (xoxb-...) |
| `DISCORD_WEBHOOK_URL` | Discord | Discord Webhook URL |

## Error Handling

The tools return error dicts for common issues:

| Error | Cause | Solution |
|-------|-------|----------|
| `SLACK_BOT_TOKEN environment variable not set` | Missing Slack token | Set the environment variable |
| `DISCORD_WEBHOOK_URL environment variable not set` | Missing Discord webhook | Set the environment variable |
| `Channel is required for Slack messages` | No channel specified | Provide `channel` argument |
| `Unknown platform: X` | Invalid platform | Use "slack" or "discord" |
| `channel_not_found` | Invalid Slack channel | Check channel ID/name |
| `not_in_channel` | Bot not in channel | Invite the bot to the channel |
| `invalid_auth` | Invalid Slack token | Check your bot token |

## Rate Limiting

### Slack
- Tier 1 methods (posting): ~1 request/second
- Tier 2 methods (reading): ~20 requests/minute
- Tier 3 methods (listing): ~50 requests/minute

The tool does not implement automatic retries. Handle rate limit errors (`ratelimited`) in your agent logic.

### Discord
- Webhooks: ~30 requests/minute per webhook
- Discord returns `429 Too Many Requests` when rate limited

## Examples

### Agent: Daily Standup Reminder

```python
# Send reminder to Slack
messaging_send(
    platform="slack",
    channel="#engineering",
    message="🌅 *Daily Standup in 15 minutes!*\n\nPlease prepare your updates."
)
```

### Agent: Build Notification to Discord

```python
# Send build status to Discord
messaging_send(
    platform="discord",
    message="✅ **Build #1234 Succeeded**\n\nBranch: `main`\nDuration: 5m 32s",
    username="Build Bot",
    avatar_url="https://example.com/build-bot.png"
)
```

### Agent: Monitor Channel Activity

```python
# Read recent messages and react to important ones
messages = messaging_read(channel="C123", limit=10)
for msg in messages["messages"]:
    if "urgent" in msg["content"].lower():
        messaging_react(
            channel="C123",
            message_id=msg["id"],
            emoji="rotating_light"
        )
```

## Limitations

### Discord Webhooks
- **Cannot read messages** - Webhooks are send-only
- **Cannot add reactions** - Requires a bot with gateway connection
- **Cannot list channels** - Webhook is bound to a single channel

For full Discord bot functionality, consider using the `discord.py` library directly.

### Slack
- Bot must be invited to channels before it can post
- Some features require additional OAuth scopes
- Enterprise Grid workspaces may have additional restrictions
