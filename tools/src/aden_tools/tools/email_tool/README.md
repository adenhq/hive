# Email Tool

Send emails via Resend API for agent notifications, reports, and communications.

## Features

- **send_email**: Send plain text or HTML emails
- **send_templated_email**: Use predefined templates for common email types

## Setup

### 1. Get a Resend API Key

1. Sign up at [resend.com](https://resend.com)
2. Create an API key at [resend.com/api-keys](https://resend.com/api-keys)
3. Add to your environment:

```bash
export RESEND_API_KEY="re_..."
export EMAIL_FROM="noreply@yourdomain.com"  # Optional, defaults to alerts@example.com
```

### 2. Install Dependencies

```bash
pip install resend
```

## Usage

### Basic Email

```python
send_email(
    to=["user@example.com"],
    subject="Hello from Agent",
    body="This is a test email from your AI agent.",
    body_type="text"
)
```

### HTML Email

```python
send_email(
    to=["user@example.com"],
    subject="Report Ready",
    body="<h1>Your Report</h1><p>The analysis is complete.</p>",
    body_type="html"
)
```

### Templated Email

#### Notification Template

```python
send_templated_email(
    to=["user@example.com"],
    template="notification",
    variables={
        "subject": "System Alert",
        "title": "Important Update",
        "message": "<p>Your system has been updated successfully.</p>",
        "icon": "🔔"
    }
)
```

#### Report Template

```python
send_templated_email(
    to=["team@example.com"],
    template="report",
    variables={
        "subject": "Weekly Sales Report",
        "title": "Sales Report",
        "content": "<h2>Total Sales: $50,000</h2><p>Details...</p>",
        "date": "2026-01-24"
    }
)
```

#### Approval Request Template

```python
send_templated_email(
    to=["manager@example.com"],
    template="approval_request",
    variables={
        "subject": "Approval Required",
        "title": "Purchase Approval Needed",
        "description": "Please approve the $5,000 software purchase.",
        "action_url": "https://app.example.com/approvals/123"
    }
)
```

#### Completion Template

```python
send_templated_email(
    to=["user@example.com"],
    template="completion",
    variables={
        "subject": "Task Complete",
        "title": "Analysis Complete",
        "task_name": "Data Analysis",
        "summary": "Your data analysis has been completed successfully."
    }
)
```

## Available Templates

| Template | Required Variables | Description |
|----------|-------------------|-------------|
| `notification` | `subject`, `title`, `message`, `icon` (optional) | General notification |
| `report` | `subject`, `title`, `content`, `date` (optional) | Report delivery |
| `approval_request` | `subject`, `title`, `description`, `action_url` | Request approval |
| `completion` | `subject`, `title`, `task_name`, `summary` | Task completion |

## Response Format

All email functions return a dictionary:

### Success

```python
{
    "success": True,
    "email_id": "abc123..."
}
```

### Error

```python
{
    "success": False,
    "error": "Error message",
    "help": "Helpful guidance (if applicable)"
}
```

## Use Cases for Agents

### 1. Human-in-the-Loop

```python
# Agent requests human approval
send_templated_email(
    to=["human@example.com"],
    template="approval_request",
    variables={
        "subject": "Approve Large Purchase",
        "title": "Approval Required",
        "description": "AI agent wants to purchase $10,000 in cloud credits.",
        "action_url": "https://app.example.com/approve/xyz"
    }
)
```

### 2. Progress Notifications

```python
# Agent reports progress
send_templated_email(
    to=["stakeholder@example.com"],
    template="notification",
    variables={
        "subject": "Analysis 50% Complete",
        "title": "Progress Update",
        "message": "<p>Data analysis is 50% complete. ETA: 2 hours</p>",
        "icon": "⏳"
    }
)
```

### 3. Report Delivery

```python
# Agent delivers generated report
send_templated_email(
    to=["team@example.com"],
    template="report",
    variables={
        "subject": "Daily AI Insights",
        "title": "AI Insights Report",
        "content": report_html,
        "date": "2026-01-24"
    }
)
```

### 4. Task Completion

```python
# Agent confirms completion
send_templated_email(
    to=["user@example.com"],
    template="completion",
    variables={
        "subject": "Research Complete",
        "title": "Research Task Finished",
        "task_name": "Competitor Analysis",
        "summary": "Found 15 competitors with detailed profiles."
    }
)
```

## Testing

To test without sending real emails, use the CredentialManager test mode:

```python
from aden_tools.credentials import CredentialManager

# Mock credentials for testing
creds = CredentialManager.for_testing({"resend": "test-key-123"})
```

## Architecture

The email tool is separate from the notification system:

```
┌─────────────────────────────────────┐
│          Email Tool                  │
│  (For Generated Agents)              │
│                                      │
│  - send_email                        │
│  - send_templated_email              │
│                                      │
│  Used by: Agent workflows            │
└─────────────────┬───────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │   EmailService   │
        │  (Core Service)  │
        └─────────┬────────┘
                  │
                  ▼
        ┌─────────────────┐
        │   Resend API     │
        └─────────────────┘
```

The core notification system (budget alerts) uses EmailService directly, while agents use the email tool via MCP.

## Security Notes

- Never hardcode API keys in code
- Use environment variables or credential management
- Validate recipient addresses
- Be mindful of rate limits
- Test with a sandbox domain first

## Error Handling

Common errors and solutions:

| Error | Solution |
|-------|----------|
| `RESEND_API_KEY not set` | Set the environment variable |
| `Resend library not installed` | Run `pip install resend` |
| `Invalid API key` | Check your API key at resend.com |
| `Rate limit exceeded` | Wait and retry, or upgrade plan |

## Troubleshooting

### Email not received?

1. Check spam folder
2. Verify recipient address
3. Check Resend dashboard for delivery status
4. Ensure sender domain is verified

### Template not rendering?

1. Verify all required variables are provided
2. Check template name spelling
3. Ensure HTML is valid

## Related Documentation

- [Email Service Guide](../../../docs/email-service-guide.md)
- [Building Tools Guide](../BUILDING_TOOLS.md)
- [Resend Documentation](https://resend.com/docs)
