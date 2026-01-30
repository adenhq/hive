# Notification Tool

Send notifications through various channels (console, email, Slack).

## Tools

### `send_notification`
Send a single notification.

**Arguments:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| message | string | Yes | - | Notification content (1-5000 chars) |
| channel | enum | No | "console" | "console", "email", or "slack" |
| recipient | string | No | "" | Email address or Slack channel/webhook |
| subject | string | No | "Notification..." | Subject line |
| priority | enum | No | "normal" | "low", "normal", "high", "urgent" |

**Returns:** Status dict with delivery confirmation

### `send_bulk_notification`
Send multiple notifications in batch.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| messages | list | Yes | List of {message, recipient, subject} dicts |
| channel | enum | No | Delivery channel for all |
| batch_size | int | No | Max messages per batch (1-50) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| SMTP_HOST | Email | SMTP server (default: smtp.gmail.com) |
| SMTP_PORT | Email | SMTP port (default: 587) |
| SMTP_USER | Email | SMTP username/email |
| SMTP_PASSWORD | Email | SMTP password or app password |
| SLACK_WEBHOOK_URL | Slack | Incoming webhook URL |
| SLACK_BOT_TOKEN | Slack | Bot token (not yet implemented) |

## Examples

```python
# Console notification
send_notification(
    message="Task completed successfully",
    channel="console",
    priority="high"
)

# Email notification
send_notification(
    message="Monthly report is ready",
    channel="email",
    recipient="user@example.com",
    subject="Monthly Report"
)

# Slack notification
send_notification(
    message="Deployment complete!",
    channel="slack",
    recipient="https://hooks.slack.com/services/..."
)
```
