"""
Email Tool - Send emails via Resend API.

Provides email sending capabilities for generated agents.

Requirements:
- RESEND_API_KEY environment variable
- EMAIL_FROM environment variable (optional, defaults to alerts@example.com)

Use cases:
- Send notifications to users
- Deliver generated reports
- Request human approval/feedback
- Communicate task completion
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register email sending tools with the MCP server."""

    @mcp.tool()
    def send_email(
        to: list[str],
        subject: str,
        body: str,
        body_type: str = "text",
        from_email: str | None = None,
    ) -> dict:
        """
        Send an email via Resend API.
        
        Use this when the agent needs to:
        - Send notifications to users
        - Deliver generated reports
        - Communicate results or updates
        - Request human input or approval
        
        Args:
            to: List of recipient email addresses (e.g., ["user@example.com"])
            subject: Email subject line
            body: Email body content (text or HTML)
            body_type: "text" for plain text, "html" for HTML content (default: "text")
            from_email: Sender email address (optional, uses EMAIL_FROM env var or default)
            
        Returns:
            Dict with {"success": True, "email_id": "..."} or {"success": False, "error": "..."}
            
        Example:
            send_email(
                to=["user@example.com"],
                subject="Daily Report",
                body="<h1>Report</h1><p>Your daily report is ready.</p>",
                body_type="html"
            )
        """
        # Get API key from credentials or environment
        if credentials is not None:
            api_key = credentials.get("resend")
        else:
            api_key = os.getenv("RESEND_API_KEY") or os.getenv("EMAIL_RESEND_API_KEY")

        if not api_key:
            return {
                "success": False,
                "error": "RESEND_API_KEY environment variable not set",
                "help": "Get an API key at https://resend.com/api-keys",
            }

        # Get sender email
        sender = from_email or os.getenv("EMAIL_FROM", "alerts@example.com")

        # Validate inputs
        if not to:
            return {"success": False, "error": "No recipients specified"}
        if not subject:
            return {"success": False, "error": "Subject is required"}
        if not body:
            return {"success": False, "error": "Body is required"}
        if body_type not in ["text", "html"]:
            return {"success": False, "error": "body_type must be 'text' or 'html'"}

        try:
            # Import resend dynamically
            try:
                import resend
            except ImportError:
                return {
                    "success": False,
                    "error": "Resend library not installed. Install with: pip install resend",
                }

            # Set API key for resend
            os.environ["RESEND_API_KEY"] = api_key
            
            # Reload resend to pick up the API key
            import importlib
            importlib.reload(resend)

            # Create email payload
            email_payload = {
                "from": sender,
                "to": to,
                "subject": subject,
            }

            if body_type == "html":
                email_payload["html"] = body
            else:
                email_payload["text"] = body

            # Send email
            emails_client = resend.Emails()
            response = emails_client.send(email_payload)

            logger.info(f"Email sent to {', '.join(to)} - Subject: {subject}")
            return {"success": True, "email_id": str(response.get("id", ""))}

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def send_templated_email(
        to: list[str],
        template: str,
        variables: dict,
        from_email: str | None = None,
    ) -> dict:
        """
        Send an email using a predefined template.
        
        Available templates:
        - "notification" - General notification template (requires: title, message, icon)
        - "report" - Report delivery template (requires: title, content, date)
        - "approval_request" - Request approval/feedback (requires: title, description, action_url)
        - "completion" - Task completion notification (requires: title, task_name, summary)
        
        Args:
            to: List of recipient email addresses
            template: Template name (notification, report, approval_request, completion)
            variables: Dict of variables to inject into template (including 'subject')
            from_email: Sender email address (optional)
            
        Returns:
            Dict with {"success": True, "email_id": "..."} or {"success": False, "error": "..."}
            
        Example:
            send_templated_email(
                to=["user@example.com"],
                template="report",
                variables={
                    "subject": "Daily Sales Report",
                    "title": "Sales Report",
                    "content": "<p>Total sales: $50,000</p>",
                    "date": "2026-01-24"
                }
            )
        """
        # Get API key from credentials or environment
        if credentials is not None:
            api_key = credentials.get("resend")
        else:
            api_key = os.getenv("RESEND_API_KEY") or os.getenv("EMAIL_RESEND_API_KEY")

        if not api_key:
            return {
                "success": False,
                "error": "RESEND_API_KEY environment variable not set",
                "help": "Get an API key at https://resend.com/api-keys",
            }

        # Validate template name
        valid_templates = ["notification", "report", "approval_request", "completion"]
        if template not in valid_templates:
            return {
                "success": False,
                "error": f"Unknown template: {template}. Available: {valid_templates}",
            }

        # Validate required variables
        if "subject" not in variables:
            return {"success": False, "error": "variables must include 'subject'"}

        try:
            # Render template
            html_content = _render_template(template, variables)
            subject = variables["subject"]

            # Use send_email to actually send
            return send_email(
                to=to,
                subject=subject,
                body=html_content,
                body_type="html",
                from_email=from_email,
            )

        except Exception as e:
            logger.error(f"Failed to send templated email: {e}")
            return {"success": False, "error": str(e)}


def _render_template(template_name: str, variables: dict) -> str:
    """
    Render HTML template with variables.
    
    Args:
        template_name: Name of the template
        variables: Variables to inject into template
        
    Returns:
        Rendered HTML string
    """
    if template_name == "notification":
        return _render_notification_template(variables)
    elif template_name == "report":
        return _render_report_template(variables)
    elif template_name == "approval_request":
        return _render_approval_request_template(variables)
    elif template_name == "completion":
        return _render_completion_template(variables)
    else:
        raise ValueError(f"Unknown template: {template_name}")


def _render_notification_template(variables: dict) -> str:
    """Render notification template."""
    title = variables.get("title", "Notification")
    message = variables.get("message", "")
    icon = variables.get("icon", "📢")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
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
            padding: 20px 0;
            border-bottom: 2px solid #007bff;
        }}
        .header h1 {{
            margin: 0;
            color: #222;
            font-size: 24px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{icon} {title}</h1>
        </div>
        <div class="content">
            {message}
        </div>
        <div class="footer">
            <p>This is an automated notification.</p>
        </div>
    </div>
</body>
</html>"""


def _render_report_template(variables: dict) -> str:
    """Render report template."""
    title = variables.get("title", "Report")
    content = variables.get("content", "")
    date = variables.get("date", "")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            background-color: #f8f9fa;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            color: #222;
            font-size: 28px;
        }}
        .meta {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title}</h1>
            {f'<div class="meta">{date}</div>' if date else ''}
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>This report was generated automatically.</p>
        </div>
    </div>
</body>
</html>"""


def _render_approval_request_template(variables: dict) -> str:
    """Render approval request template."""
    title = variables.get("title", "Approval Required")
    description = variables.get("description", "")
    action_url = variables.get("action_url", "#")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
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
            padding: 20px 0;
            background-color: #fff3cd;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            color: #222;
            font-size: 24px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            margin: 20px 0;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✋ {title}</h1>
        </div>
        <div class="content">
            <p>{description}</p>
            <div style="text-align: center;">
                <a href="{action_url}" class="button">Review and Approve</a>
            </div>
        </div>
        <div class="footer">
            <p>Please review and take action as needed.</p>
        </div>
    </div>
</body>
</html>"""


def _render_completion_template(variables: dict) -> str:
    """Render task completion template."""
    title = variables.get("title", "Task Completed")
    task_name = variables.get("task_name", "")
    summary = variables.get("summary", "")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
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
            padding: 20px 0;
            background-color: #d4edda;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            color: #155724;
            font-size: 24px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .task-name {{
            font-weight: bold;
            color: #007bff;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ {title}</h1>
        </div>
        <div class="content">
            {f'<div class="task-name">{task_name}</div>' if task_name else ''}
            <p>{summary}</p>
        </div>
        <div class="footer">
            <p>Task completed successfully.</p>
        </div>
    </div>
</body>
</html>"""
