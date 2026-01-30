"""
Slack Integration Tool - Send real notifications to Slack.

Provides tools to:
- Test Slack connection
- List channels
- Send messages to channels/users
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register Slack tools with the MCP server."""

    def _get_slack_config() -> Dict[str, str]:
        """Get Slack configuration from environment."""
        return {
            "access_token": os.getenv("SLACK_ACCESS_TOKEN", "").strip(),
            "refresh_token": os.getenv("SLACK_REFRESH_TOKEN", "").strip(),
            "webhook_url": os.getenv("SLACK_WEBHOOK_URL", "").strip(),
        }

    def _slack_api_request(
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Slack API."""
        config = _get_slack_config()
        
        if not config["access_token"]:
            return {"error": "SLACK_ACCESS_TOKEN not configured. Set in .env file."}
        
        url = f"https://slack.com/api/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json; charset=utf-8",
        }
        
        try:
            if data:
                request_data = json.dumps(data).encode("utf-8")
            else:
                request_data = None
            
            req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                if not result.get("ok"):
                    return {
                        "error": f"Slack API error: {result.get('error', 'Unknown error')}",
                        "details": result,
                    }
                return result
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {
                "error": f"Slack API error: {e.code} {e.reason}",
                "details": error_body[:500],
            }
        except urllib.error.URLError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    @mcp.tool()
    def slack_test_connection() -> dict:
        """
        Test connection to Slack and get bot info.

        Use this to verify Slack credentials are working.

        Returns:
            Dict with connection status and bot info
        """
        result = _slack_api_request("auth.test")
        
        if "error" in result:
            return {
                "connected": False,
                **result,
            }
        
        return {
            "connected": True,
            "team": result.get("team"),
            "user": result.get("user"),
            "user_id": result.get("user_id"),
            "team_id": result.get("team_id"),
            "bot_id": result.get("bot_id"),
        }

    @mcp.tool()
    def slack_list_channels(
        types: str = "public_channel,private_channel",
        limit: int = 100,
    ) -> dict:
        """
        List available Slack channels.

        Use this to see which channels you can send messages to.

        Args:
            types: Channel types to list (public_channel, private_channel)
            limit: Maximum channels to return

        Returns:
            Dict with list of channels
        """
        result = _slack_api_request(
            f"conversations.list?types={types}&limit={limit}"
        )
        
        if "error" in result:
            return result
        
        channels = []
        for ch in result.get("channels", []):
            channels.append({
                "id": ch.get("id"),
                "name": ch.get("name"),
                "is_private": ch.get("is_private", False),
                "is_member": ch.get("is_member", False),
                "num_members": ch.get("num_members", 0),
            })
        
        return {
            "success": True,
            "count": len(channels),
            "channels": channels,
        }

    @mcp.tool()
    def slack_send_message(
        channel: str,
        message: str,
        thread_ts: str = "",
    ) -> dict:
        """
        Send a message to a Slack channel.

        Use this to send real notifications to your team.

        Args:
            channel: Channel ID or name (e.g., "C1234567890" or "#general")
            message: Message text to send (supports Slack markdown)
            thread_ts: Optional thread timestamp to reply in a thread

        Returns:
            Dict with message delivery confirmation
        """
        if not channel:
            return {"error": "channel is required"}
        if not message:
            return {"error": "message is required"}
        
        data = {
            "channel": channel,
            "text": message,
        }
        
        if thread_ts:
            data["thread_ts"] = thread_ts
        
        result = _slack_api_request("chat.postMessage", method="POST", data=data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "delivered": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
            "message": message[:100] + "..." if len(message) > 100 else message,
        }

    @mcp.tool()
    def slack_send_rich_message(
        channel: str,
        title: str,
        message: str,
        color: str = "#36a64f",
        fields: list = None,
        footer: str = "Aden Agent",
    ) -> dict:
        """
        Send a rich formatted message to Slack with attachments.

        Use this for important notifications with structured data.

        Args:
            channel: Channel ID or name
            title: Message title
            message: Main message text
            color: Attachment color (hex code)
            fields: List of {"title": "...", "value": "...", "short": bool}
            footer: Footer text

        Returns:
            Dict with message delivery confirmation
        """
        if not channel:
            return {"error": "channel is required"}
        if not message:
            return {"error": "message is required"}
        
        fields = fields or []
        
        # Build blocks for rich message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                }
            },
        ]
        
        # Add fields as context
        if fields:
            field_elements = []
            for f in fields[:10]:  # Max 10 fields
                field_elements.append({
                    "type": "mrkdwn",
                    "text": f"*{f.get('title', '')}*: {f.get('value', '')}",
                })
            blocks.append({
                "type": "context",
                "elements": field_elements,
            })
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_{footer} | {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
                }
            ],
        })
        
        data = {
            "channel": channel,
            "text": f"{title}: {message[:50]}...",  # Fallback text
            "blocks": blocks,
        }
        
        result = _slack_api_request("chat.postMessage", method="POST", data=data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "delivered": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
            "title": title,
        }


__all__ = ["register_tools"]
