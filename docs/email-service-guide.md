# Email Service Integration Guide

This guide explains how to set up and use email notifications in the Aden framework for budget alerts and other notifications.

## Overview

The email service integrates with [Resend](https://resend.com), a modern email API that provides:
- Simple, clean API
- Excellent TypeScript/Python support  
- Generous free tier (100 emails/day, 3,000/month)
- High deliverability rates
- Reliable transactional email

Budget alerts can be sent via email at configurable thresholds (50%, 80%, 95%, 100% of budget).

## Setup Instructions

### 1. Sign Up for Resend

1. Go to [https://resend.com](https://resend.com)
2. Create a free account
3. Go to [API Keys](https://resend.com/api-keys) to get your API key
4. Copy your API key (starts with `re_`)

### 2. Verify Your Sender Domain

For production use, verify your domain in Resend:

1. In Resend dashboard, go to **Domains**
2. Add your domain (e.g., `yourdomain.com`)
3. Follow the DNS verification steps
4. Once verified, you can send from `alerts@yourdomain.com`

**For testing**, Resend provides a `resend.dev` domain you can use immediately.

### 3. Update Configuration

Update your `config.yaml`:

```yaml
email:
  enabled: true
  from: "alerts@yourdomain.com"
  api_key: "re_your_api_key_here"
```

Or set environment variables:

```bash
export EMAIL_ENABLED=true
export EMAIL_FROM=alerts@yourdomain.com
export EMAIL_RESEND_API_KEY=re_your_api_key_here
```

### 4. Install Dependencies

The Resend Python library is included in `pyproject.toml`. Install dependencies:

```bash
cd core
pip install -e .
```

Or for development:

```bash
pip install -e ".[dev]"
```

## Usage

### Using the Email Service

```python
from framework.services import EmailService, EmailConfig, BudgetAlertEmail
import os

# Initialize from environment
config = EmailConfig.from_env()
email_service = EmailService(config)

# Or initialize with explicit values
config = EmailConfig(
    api_key="re_your_api_key",
    from_email="alerts@example.com",
    enabled=True
)
email_service = EmailService(config)

# Create a budget alert
alert = BudgetAlertEmail(
    recipients=["user@example.com", "admin@example.com"],
    budget_name="Engineering Team Monthly",
    current_spend=800.00,
    budget_limit=1000.00,
    percentage_used=80.0,
    threshold=80
)

# Send the alert
if email_service.is_enabled():
    success = await email_service.send_budget_alert(alert)
    if success:
        print("Email sent successfully")
    else:
        print("Failed to send email (see logs for details)")
```

### In Budget Monitoring Code

Here's how to integrate email alerts into your budget monitoring:

```python
from framework.services import EmailService, EmailConfig, BudgetAlertEmail

class BudgetMonitor:
    def __init__(self):
        self.email_service = EmailService(EmailConfig.from_env())
    
    async def check_budget(self, budget_id: str, threshold: int):
        """Check budget and send alerts if threshold exceeded."""
        budget = self.get_budget(budget_id)
        percentage = (budget.spent / budget.limit) * 100
        
        if percentage >= threshold:
            alert = BudgetAlertEmail(
                recipients=budget.alert_emails,
                budget_name=budget.name,
                current_spend=budget.spent,
                budget_limit=budget.limit,
                percentage_used=percentage,
                threshold=threshold
            )
            
            await self.email_service.send_budget_alert(alert)
```

## Features

### Email Content

Budget alert emails include:
- **Severity indicator** - WARNING (80%) or CRITICAL (95%+)
- **Budget information** - Name, current spend, limit
- **Usage metrics** - Percentage used, remaining budget
- **Visual progress bar** - Shows budget consumption
- **Action guidance** - Specific recommendations based on severity

### Responsive Design

Emails are formatted with:
- Professional HTML styling
- Mobile-responsive layout
- Clear visual hierarchy
- Color-coded severity indicators

### Error Handling

The email service gracefully handles errors:
- If email sending fails, it logs the error but doesn't crash
- Budget monitoring continues even if email fails
- Service can be disabled without affecting core functionality
- Missing Resend library is handled with helpful warning message

## Testing

### Running Tests

```bash
cd core
pytest tests/test_email_service.py -v
```

### Test Coverage

Tests include:
- ✅ Configuration loading from environment
- ✅ Service initialization with/without API key
- ✅ Successful email sending
- ✅ API error handling
- ✅ Disabled service behavior
- ✅ HTML content generation
- ✅ Subject line formatting
- ✅ Multiple recipients
- ✅ Critical vs warning severity levels

### Manual Testing

1. **Enable in development:**
   ```yaml
   email:
     enabled: true
     from: "alerts@resend.dev"
     api_key: "re_test_abc123..."
   ```

2. **Send test email:**
   ```python
   import asyncio
   from framework.services import EmailService, EmailConfig, BudgetAlertEmail
   
   async def test():
       config = EmailConfig.from_env()
       service = EmailService(config)
       
       alert = BudgetAlertEmail(
           recipients=["your-email@example.com"],
           budget_name="Test Budget",
           current_spend=800.00,
           budget_limit=1000.00,
           percentage_used=80.0,
           threshold=80
       )
       
       result = await service.send_budget_alert(alert)
       print(f"Email sent: {result}")
   
   asyncio.run(test())
   ```

3. **Check Resend dashboard** for delivery status

## Configuration Options

### EmailConfig

```python
@dataclass
class EmailConfig:
    api_key: str          # Resend API key
    from_email: str       # Sender email address
    enabled: bool = False # Service enabled/disabled
```

### BudgetAlertEmail

```python
@dataclass
class BudgetAlertEmail:
    recipients: list[str]      # Email addresses to send to
    budget_name: str           # Name of the budget
    current_spend: float       # Current spending
    budget_limit: float        # Budget limit
    percentage_used: float     # Percentage of budget used (0-100)
    threshold: int             # Threshold that triggered alert (50, 80, 95, 100)
```

## Troubleshooting

### "Resend library not installed" warning

Install the Resend package:
```bash
pip install resend>=0.4.0
```

### "Invalid API key" error

- Verify your API key is correct (should start with `re_`)
- Check the key is set in environment or config
- Regenerate API key in Resend dashboard if needed

### Emails not being delivered

1. **Check logs** - Review application logs for sending errors
2. **Verify sender** - Make sure `from_email` is verified in Resend
3. **Check spam** - New domains may initially land in spam
4. **Test with Resend domain** - Use `alerts@resend.dev` for testing
5. **Verify recipient** - Check that email address is correct

### Rate limiting

Resend free tier allows:
- 100 emails/day
- 3,000 emails/month

For higher limits, upgrade your Resend plan.

## Advanced Usage

### Custom Email Templates

To use custom HTML templates:

```python
class EmailService:
    def send_custom_email(self, to: list[str], subject: str, html: str):
        """Send email with custom HTML template."""
        return self.resend.emails.send({
            "from": self.config.from_email,
            "to": to,
            "subject": subject,
            "html": html,
        })
```

### Sending Different Alert Types

Extend for other notification types:

```python
async def send_runaway_agent_alert(self, alert_data):
    """Send alert for runaway agent detection."""
    html = self._build_runaway_agent_html(alert_data)
    # Send using standard method
    
async def send_quality_alert(self, alert_data):
    """Send alert for quality score drops."""
    html = self._build_quality_alert_html(alert_data)
    # Send using standard method
```

## Environment Variables

Standard environment variables for email configuration:

```bash
# Enable/disable email service
EMAIL_ENABLED=true|false

# Sender email address
EMAIL_FROM=alerts@yourdomain.com

# Resend API key
EMAIL_RESEND_API_KEY=re_xxxxx

# Custom prefix (if using from_env(prefix="..."))
CUSTOM_ENABLED=true
CUSTOM_FROM=noreply@company.com
CUSTOM_RESEND_API_KEY=re_xxxxx
```

## Integration with Budget Alerts

The email service is designed to integrate with the existing budget alert infrastructure:

1. Budget thresholds trigger at 50%, 80%, 95%, 100%
2. For each threshold, notifications are sent to configured channels
3. Email is one of the supported channels (along with Slack, webhooks, etc.)
4. Recipients are determined by the budget's alert configuration

Example budget configuration:

```yaml
budget:
  name: "Engineering Team Monthly"
  limit: 1000.00
  alerts:
    channels: ["slack", "email"]
    thresholds: [50, 80, 95, 100]
    email_recipients: ["team@company.com", "finance@company.com"]
    slack_channel: "#budget-alerts"
```

## Support

For issues with:
- **Email service code** - Check logs and review the troubleshooting section above
- **Resend API** - Visit [Resend documentation](https://resend.com/docs)
- **Integration** - Review example code in `core/tests/test_email_service.py`

## Next Steps

After implementing email alerts, consider:

1. **Email templates** - Create custom templates for different alert types
2. **Digest emails** - Send daily/weekly summaries instead of real-time alerts
3. **Email preferences** - Let users customize alert frequency
4. **Other channels** - Extend to support SMS, Teams, Discord, etc.
5. **Email rate limiting** - Prevent alert flooding during issues

## References

- [Resend Documentation](https://resend.com/docs)
- [Resend Python SDK](https://github.com/resendlabs/resend-python)
- [Cost Management Guide](../articles/ai-agent-cost-management-guide.md)
- [Observability & Monitoring Guide](../articles/ai-agent-observability-monitoring.md)
