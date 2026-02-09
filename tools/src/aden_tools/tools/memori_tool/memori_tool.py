"""
Memori AI Tool Integration - Persistent memory fabric for Hive agents.
"""

import logging
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)

def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None):
    """
    Register Memori memory tools with the FastMCP server.
    """

    async def _request(
        method: str,
        path: str,
        creds: CredentialManager,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Base request handler for Memori API."""
        api_key = creds.get("memori")
        if not api_key:
            return {"status": "error", "message": "Memori API key missing (MEMORI_API_KEY)"}
        
        base_url = "https://api.memorilabs.ai/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, 
                    f"{base_url}{path}", 
                    headers=headers, 
                    json=json, 
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    return {"status": "error", "message": "Invalid Memori API key"}
                if response.status_code == 429:
                    return {"status": "error", "message": "Memori rate limit exceeded"}
                
                response.raise_for_status()
                # If DELETE, might be empty
                if method == "DELETE" and response.status_code == 204:
                    return {"status": "success", "message": "Deleted"}
                
                return response.json()
            except Exception as e:
                logger.error(f"Memori API error: {e}")
                return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def memori_add(
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Add a new memory or fact to the persistent memory fabric.
        
        Args:
            content: The text content to remember (e.g., 'The user prefers dark mode').
            user_id: Unique identifier for the user/entity this memory belongs to.
            metadata: Optional key-value pairs to store with the memory.
        """
        creds = credentials or CredentialManager()
        payload = {"content": content}
        if user_id:
            payload["user_id"] = user_id
        if metadata:
            payload["metadata"] = metadata
            
        return await _request("POST", "/memories", creds, json=payload)

    @mcp.tool()
    async def memori_recall(
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Recall relevant memories or facts based on a semantic search query.
        
        Args:
            query: Description of what you want to recall.
            user_id: Unique identifier for the user/entity to restrict search to.
            limit: Maximum number of memories to return (default: 5).
        """
        creds = credentials or CredentialManager()
        payload = {"query": query, "limit": limit}
        if user_id:
            payload["user_id"] = user_id
            
        return await _request("POST", "/memories/search", creds, json=payload)

    @mcp.tool()
    async def memori_delete(
        memory_id: str,
    ) -> dict[str, Any]:
        """
        Delete a specific memory by its ID.
        
        Args:
            memory_id: The unique ID of the memory to remove.
        """
        creds = credentials or CredentialManager()
        return await _request("DELETE", f"/memories/{memory_id}", creds)

    @mcp.tool()
    async def memori_health_check() -> dict[str, Any]:
        """
        Verify connectivity and authentication with Memori AI.
        """
        creds = credentials or CredentialManager()
        # Health check endpoint varies, usually GET / or /health
        # We'll use a simple list check if /health isn't standard
        return await _request("GET", "/health", creds)
