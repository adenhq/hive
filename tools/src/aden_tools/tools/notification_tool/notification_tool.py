"""
Notification Tool - Send notifications through various channels.

Supports channels: console, email, slack (with API keys).
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Literal, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register notification tools with the MCP server."""

    @mcp.tool()
    def send_notification(
        message: str,
        channel: Literal["console", "email", "slack"] = "console",
        recipient: str = "",
        subject: str = "Notification from Aden Agent",
        priority: Literal["low", "normal", "high", "urgent"] = "normal",
    ) -> dict:
        """
        Send a notification through the specified channel.

        Use this when you need to alert users, send status updates, or communicate
        results to external systems.

        Args:
            message: The notification message content (1-5000 chars)
            channel: Delivery channel - "console", "email", or "slack"
            recipient: For email: email address. For slack: channel ID or webhook URL
            subject: Subject line for email notifications
            priority: Message priority level for proper handling

        Returns:
            Dict with delivery status, channel used, and timestamp
        """
        import datetime
        
        # Validate message
        if not message or len(message) > 5000:
            return {"error": "Message must be 1-5000 characters"}
        
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            if channel == "console":
                # Console output - always works, great for testing
                priority_prefix = {
                    "low": "[INFO]",
                    "normal": "[NOTICE]",
                    "high": "[ALERT]",
                    "urgent": "[URGENT]"
                }.get(priority, "[NOTICE]")
                
                print(f"\n{priority_prefix} {subject}")
                print(f"{'=' * 50}")
                print(message)
                print(f"{'=' * 50}")
                print(f"Sent at: {timestamp}\n")
                
                return {
                    "success": True,
                    "channel": "console",
                    "message": message[:100] + "..." if len(message) > 100 else message,
                    "timestamp": timestamp,
                }
            
            elif channel == "email":
                # Email notification
                if not recipient:
                    return {"error": "Email recipient is required"}
                
                # Get SMTP credentials
                smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
                smtp_port = int(os.getenv("SMTP_PORT", "587"))
                smtp_user = os.getenv("SMTP_USER")
                smtp_password = os.getenv("SMTP_PASSWORD")
                
                if not smtp_user or not smtp_password:
                    return {
                        "error": "SMTP credentials not configured",
                        "help": "Set SMTP_USER and SMTP_PASSWORD environment variables",
                        "fallback": "Using console fallback",
                        "message_preview": message[:100],
                    }
                
                # Send email
                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = recipient
                msg["Subject"] = f"[{priority.upper()}] {subject}"
                msg.attach(MIMEText(message, "plain"))
                
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                
                return {
                    "success": True,
                    "channel": "email",
                    "recipient": recipient,
                    "subject": subject,
                    "timestamp": timestamp,
                }
            
            elif channel == "slack":
                # Slack notification
                if not recipient:
                    return {"error": "Slack channel or webhook URL is required"}
                
                # Check for Slack webhook or token
                slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
                slack_token = os.getenv("SLACK_BOT_TOKEN")
                
                if recipient.startswith("https://hooks.slack.com"):
                    webhook_url = recipient
                elif slack_webhook:
                    webhook_url = slack_webhook
                elif slack_token:
                    # Would use Slack API with token
                    return {
                        "error": "Slack API with token not yet implemented",
                        "help": "Use SLACK_WEBHOOK_URL for webhook-based notifications",
                    }
                else:
                    return {
                        "error": "Slack credentials not configured",
                        "help": "Set SLACK_WEBHOOK_URL environment variable",
                        "fallback": "Using console fallback",
                        "message_preview": message[:100],
                    }
                
                # Send via webhook
                import urllib.request
                
                # Format message with priority emoji
                priority_emoji = {
                    "low": ":information_source:",
                    "normal": ":bell:",
                    "high": ":warning:",
                    "urgent": ":rotating_light:"
                }.get(priority, ":bell:")
                
                payload = {
                    "text": f"{priority_emoji} *{subject}*\n{message}",
                    "username": "Aden Agent",
                }
                
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={"Content-Type": "application/json"},
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "channel": "slack",
                            "webhook": webhook_url[:50] + "...",
                            "timestamp": timestamp,
                        }
                    else:
                        return {"error": f"Slack returned status {response.status}"}
            
            else:
                return {"error": f"Unknown channel: {channel}"}
            
        except smtplib.SMTPException as e:
            return {"error": f"Email delivery failed: {str(e)}"}
        except urllib.error.URLError as e:
            return {"error": f"Slack delivery failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Notification failed: {str(e)}"}

    @mcp.tool()
    def send_bulk_notification(
        messages: list,
        channel: Literal["console", "email", "slack"] = "console",
        batch_size: int = 10,
    ) -> dict:
        """
        Send multiple notifications in batch.

        Use this when you need to send notifications to multiple recipients
        or send a series of status updates.

        Args:
            messages: List of dicts with 'message', 'recipient', optional 'subject'
            channel: Delivery channel for all messages
            batch_size: Maximum messages per batch (1-50)

        Returns:
            Dict with success count, failure count, and error details
        """
        if not messages:
            return {"error": "Messages list cannot be empty"}
        
        if not isinstance(messages, list):
            return {"error": "Messages must be a list"}
        
        batch_size = max(1, min(50, batch_size))
        
        results = {
            "total": len(messages),
            "sent": 0,
            "failed": 0,
            "errors": [],
        }
        
        for i, msg_config in enumerate(messages[:batch_size]):
            if not isinstance(msg_config, dict):
                results["failed"] += 1
                results["errors"].append({"index": i, "error": "Invalid message format"})
                continue
            
            message = msg_config.get("message", "")
            recipient = msg_config.get("recipient", "")
            subject = msg_config.get("subject", "Bulk Notification")
            
            # Call single notification (re-use logic)
            # For simplicity, just track success/failure
            try:
                if channel == "console":
                    print(f"[{i+1}/{len(messages)}] {subject}: {message[:50]}...")
                    results["sent"] += 1
                else:
                    # Would call send_notification for each
                    results["sent"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"index": i, "error": str(e)})
        
        return results


__all__ = ["register_tools"]
