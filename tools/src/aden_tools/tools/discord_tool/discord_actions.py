import requests
from fastmcp import FastMCP

def register_tools(mcp: FastMCP) -> None:
    
    @mcp.tool()
    def send_discord_message(webhook_url: str, message: str) -> str:
        """
        Sends a notification to a Discord channel via Webhook.
        Args:
            webhook_url: The discord webhook link.
            message: The text you want to send.
        """
        if not webhook_url:
            return "Error: Webhook URL is missing."

        try:
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code in [200, 204]:
                return "Success: Message sent to Discord!"
            else:
                return f"Failed: Discord returned status {response.status_code}"
                
        except Exception as e:
            return f"Error: {str(e)}"