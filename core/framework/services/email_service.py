"""Email service for sending budget alerts and notifications."""

import logging
from dataclasses import dataclass
from typing import Optional

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuration for email service."""

    api_key: str
    from_email: str
    enabled: bool = False

    @classmethod
    def from_env(cls, prefix: str = "EMAIL_") -> "EmailConfig":
        """Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variable names (default: "EMAIL_")
        
        Returns:
            EmailConfig instance
        """
        import os

        api_key = os.getenv(f"{prefix}RESEND_API_KEY", "")
        from_email = os.getenv(f"{prefix}FROM", "alerts@example.com")
        enabled = os.getenv(f"{prefix}ENABLED", "false").lower() == "true"

        return cls(
            api_key=api_key,
            from_email=from_email,
            enabled=enabled,
        )


@dataclass
class BudgetAlertEmail:
    """Email data for budget alerts."""

    recipients: list[str]
    budget_name: str
    current_spend: float
    budget_limit: float
    percentage_used: float
    threshold: int


class EmailService:
    """Service for sending emails via Resend."""

    def __init__(self, config: EmailConfig):
        """Initialize email service.
        
        Args:
            config: EmailConfig instance with API key and settings
        """
        self.config = config
        self.emails_client: Optional[object] = None

        if config.enabled and config.api_key:
            if not RESEND_AVAILABLE:
                logger.warning(
                    "Resend library not installed. Email service will be disabled. "
                    "Install with: pip install resend"
                )
            else:
                try:
                    # Set API key in environment for resend to pick it up
                    import os
                    os.environ["RESEND_API_KEY"] = config.api_key
                    
                    # Reload resend module to pick up the new API key
                    import importlib
                    importlib.reload(resend)
                    
                    # Create emails client
                    self.emails_client = resend.Emails()
                except Exception as e:
                    logger.error(f"Failed to initialize Resend client: {e}")

    async def send_budget_alert(self, alert: BudgetAlertEmail) -> bool:
        """Send a budget alert email.
        
        Args:
            alert: BudgetAlertEmail with recipient and budget information
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("Email service disabled, skipping budget alert email")
            return False

        try:
            subject = self._format_subject(alert)
            html_content = self._build_budget_alert_html(alert)

            response = self.emails_client.send(
                {
                    "from": self.config.from_email,
                    "to": alert.recipients,
                    "subject": subject,
                    "html": html_content,
                }
            )

            logger.info(
                f"Budget alert email sent to {', '.join(alert.recipients)} "
                f"for budget '{alert.budget_name}' at {alert.percentage_used:.1f}%"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send budget alert email: {e}")
            # Don't raise - email failure shouldn't break budget monitoring
            return False

    def _format_subject(self, alert: BudgetAlertEmail) -> str:
        """Format email subject line.
        
        Args:
            alert: BudgetAlertEmail with alert data
            
        Returns:
            Formatted subject line
        """
        severity = "🚨 CRITICAL" if alert.percentage_used >= 95 else "⚠️  WARNING"
        return (
            f"{severity}: Budget Alert - {alert.budget_name} "
            f"at {alert.percentage_used:.1f}%"
        )

    def _build_budget_alert_html(self, alert: BudgetAlertEmail) -> str:
        """Build HTML content for budget alert email.
        
        Args:
            alert: BudgetAlertEmail with budget information
            
        Returns:
            HTML email content
        """
        remaining = alert.budget_limit - alert.current_spend
        is_critical = alert.percentage_used >= 95

        severity_class = "critical" if is_critical else "warning"
        severity_icon = "🚨" if is_critical else "⚠️"
        severity_text = "CRITICAL" if is_critical else "WARNING"

        action_text = (
            "Immediate action recommended to avoid budget overrun."
            if is_critical
            else "Please review your spending and adjust if necessary."
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            color: #222;
            font-size: 28px;
        }}
        .alert-box {{
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid;
            border-radius: 4px;
            background-color: #fafafa;
        }}
        .alert-box.critical {{
            border-left-color: #dc3545;
            background-color: #fff5f5;
        }}
        .alert-box.warning {{
            border-left-color: #ffc107;
            background-color: #fffbf0;
        }}
        .severity {{
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 10px;
        }}
        .severity.critical {{
            color: #dc3545;
        }}
        .severity.warning {{
            color: #ff8c00;
        }}
        .metrics {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .metric {{
            margin: 12px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .metric-label {{
            font-weight: 600;
            color: #555;
        }}
        .metric-value {{
            color: #333;
            font-size: 16px;
            font-family: 'Courier New', monospace;
        }}
        .progress-bar {{
            margin: 15px 0;
        }}
        .progress {{
            height: 24px;
            background-color: #e9ecef;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #28a745;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }}
        .progress-fill.warning {{
            background-color: #ffc107;
            color: #333;
        }}
        .progress-fill.critical {{
            background-color: #dc3545;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            margin: 10px 0;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
            transition: background-color 0.3s;
        }}
        .button:hover {{
            background-color: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 Budget Alert Notification</h1>
        </div>

        <div class="alert-box {severity_class}">
            <div class="severity {severity_class}">
                {severity_icon} {severity_text}: {alert.threshold}% budget threshold reached
            </div>
            <p>Budget: <strong>{alert.budget_name}</strong></p>
        </div>

        <div class="metrics">
            <div class="metric">
                <span class="metric-label">Budget Name:</span>
                <span class="metric-value">{alert.budget_name}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Current Spend:</span>
                <span class="metric-value">${alert.current_spend:.2f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Budget Limit:</span>
                <span class="metric-value">${alert.budget_limit:.2f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Remaining Budget:</span>
                <span class="metric-value">${remaining:.2f}</span>
            </div>

            <div class="progress-bar">
                <div class="progress">
                    <div class="progress-fill {'critical' if is_critical else 'warning' if alert.percentage_used >= 80 else ''}" style="width: {min(alert.percentage_used, 100):.1f}%">
                        {alert.percentage_used:.1f}%
                    </div>
                </div>
            </div>

            <div class="metric">
                <span class="metric-label">Usage:</span>
                <span class="metric-value">{alert.percentage_used:.1f}% of budget</span>
            </div>
        </div>

        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p style="margin: 0; color: #004085;">
                <strong>Action Required:</strong> {action_text}
            </p>
        </div>

        <div class="footer">
            <p>This is an automated notification from your budget monitoring system.</p>
            <p>If you believe this was sent in error, please contact your administrator.</p>
        </div>
    </div>
</body>
</html>"""

    def is_enabled(self) -> bool:
        """Check if email service is enabled and properly configured.
        
        Returns:
            True if service is enabled with a valid client, False otherwise
        """
        return self.config.enabled and self.emails_client is not None
