"""
Zendesk Integration Tools - Ticket management and search.
"""

import base64
import logging
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)

def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None):
    """
    Register Zendesk tools with the FastMCP server.
    """
    
    def get_auth_header(creds: CredentialManager) -> dict[str, str]:
        email = creds.get("zendesk_email")
        token = creds.get("zendesk")
        if not email or not token:
            return {}
        
        # Zendesk API Token auth format: {email_address}/token:{api_token}
        auth_str = f"{email}/token:{token}"
        encoded_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {encoded_auth}"}

    def get_base_url(creds: CredentialManager) -> str:
        subdomain = creds.get("zendesk_subdomain")
        return f"https://{subdomain}.zendesk.com/api/v2"

    @mcp.tool()
    async def zendesk_health_check() -> str:
        """
        Verify Zendesk connection by fetching current user info.
        """
        creds = credentials or CredentialManager()
        headers = get_auth_header(creds)
        base_url = get_base_url(creds)
        
        if not headers or "None" in base_url:
            return "❌ Missing Zendesk credentials (email, token, or subdomain)"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{base_url}/users/me.json", headers=headers)
                response.raise_for_status()
                user_data = response.json().get("user", {})
                return f"✅ Zendesk connection active. Authenticated as: {user_data.get('name')} ({user_data.get('email')})"
            except Exception as e:
                return f"❌ Zendesk health check failed: {str(e)}"

    @mcp.tool()
    async def zendesk_ticket_search(
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Search for tickets in Zendesk.
        
        Args:
            query: The search query (e.g., 'printer issue', 'requester:12345').
            status: Filter by status (new, open, pending, hold, solved, closed).
            priority: Filter by priority (low, normal, high, urgent).
        """
        creds = credentials or CredentialManager()
        headers = get_auth_header(creds)
        base_url = get_base_url(creds)
        
        # Combine filters into zendesk search syntax
        search_query = f"type:ticket {query}"
        if status:
            search_query += f" status:{status}"
        if priority:
            search_query += f" priority:{priority}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/search.json",
                params={"query": search_query},
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    @mcp.tool()
    async def zendesk_ticket_get(ticket_id: int) -> dict[str, Any]:
        """
        Get full details of a single Zendesk ticket.
        """
        creds = credentials or CredentialManager()
        headers = get_auth_header(creds)
        base_url = get_base_url(creds)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/tickets/{ticket_id}.json",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    @mcp.tool()
    async def zendesk_ticket_update(
        ticket_id: int,
        status: Optional[str] = None,
        assignee_id: Optional[int] = None,
        comment: Optional[str] = None,
        is_public: bool = False,
    ) -> dict[str, Any]:
        """
        Update a Zendesk ticket.
        
        Args:
            ticket_id: The ID of the ticket to update.
            status: New status for the ticket.
            assignee_id: User ID to assign the ticket to.
            comment: Text for the ticket comment.
            is_public: Whether the comment is public (visible to requester) or private (internal note).
        """
        creds = credentials or CredentialManager()
        headers = get_auth_header(creds)
        base_url = get_base_url(creds)
        
        ticket_data = {}
        if status:
            ticket_data["status"] = status
        if assignee_id:
            ticket_data["assignee_id"] = assignee_id
        if comment:
            ticket_data["comment"] = {"body": comment, "public": is_public}
            
        payload = {"ticket": ticket_data}
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{base_url}/tickets/{ticket_id}.json",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
