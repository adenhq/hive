"""
Notion Tool - Interact with Notion pages and databases via the Notion API.

Supports:
- Internal integration tokens (NOTION_API_KEY)

API Reference: https://developers.notion.com/reference
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class _NotionClient:
    """Internal client wrapping Notion API calls."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION,
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid Notion API key or token expired"}
        if response.status_code == 403:
            return {
                "error": "Access denied. Ensure the integration has access to this resource. "
                "Share the page/database with your integration."
            }
        if response.status_code == 404:
            return {
                "error": "Resource not found. Check the ID and ensure the integration has access."
            }
        if response.status_code == 429:
            return {"error": "Notion rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                detail = response.json().get("message", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Notion API error (HTTP {response.status_code}): {detail}"}
        return response.json()

    def search(
        self,
        query: str = "",
        filter_type: str | None = None,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Search pages and databases."""
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if query:
            body["query"] = query
        if filter_type in ("page", "database"):
            body["filter"] = {"property": "object", "value": filter_type}

        response = httpx.post(
            f"{NOTION_API_BASE}/search",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Retrieve a page by ID."""
        response = httpx.get(
            f"{NOTION_API_BASE}/pages/{page_id}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_page_content(self, page_id: str) -> dict[str, Any]:
        """Retrieve the content (blocks) of a page."""
        response = httpx.get(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            headers=self._headers,
            params={"page_size": 100},
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_page(
        self,
        parent_id: str,
        parent_type: str,
        title: str,
        content: list[dict[str, Any]] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new page."""
        body: dict[str, Any] = {}

        # Set parent
        if parent_type == "database":
            body["parent"] = {"database_id": parent_id}
            # For database pages, title goes in properties
            if properties:
                body["properties"] = properties
            else:
                body["properties"] = {"title": {"title": [{"text": {"content": title}}]}}
        else:
            body["parent"] = {"page_id": parent_id}
            # For page children, title is a property
            body["properties"] = {"title": {"title": [{"text": {"content": title}}]}}

        # Add content blocks if provided
        if content:
            body["children"] = content

        response = httpx.post(
            f"{NOTION_API_BASE}/pages",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        """Update a page's properties or archive status."""
        body: dict[str, Any] = {}
        if properties:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived

        response = httpx.patch(
            f"{NOTION_API_BASE}/pages/{page_id}",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def query_database(
        self,
        database_id: str,
        filter_conditions: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Query a database with optional filters and sorts."""
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter_conditions:
            body["filter"] = filter_conditions
        if sorts:
            body["sorts"] = sorts

        response = httpx.post(
            f"{NOTION_API_BASE}/databases/{database_id}/query",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def append_blocks(
        self,
        block_id: str,
        children: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Append child blocks to a parent block (page or existing block)."""
        response = httpx.patch(
            f"{NOTION_API_BASE}/blocks/{block_id}/children",
            headers=self._headers,
            json={"children": children},
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Notion tools with the MCP server."""

    def _get_api_key() -> str | None:
        """Get Notion API key from credential manager or environment."""
        if credentials is not None:
            key = credentials.get("notion")
            if key is not None and not isinstance(key, str):
                raise TypeError(
                    f"Expected string from credentials.get('notion'), got {type(key).__name__}"
                )
            return key
        return os.getenv("NOTION_API_KEY")

    def _get_client() -> _NotionClient | dict[str, str]:
        """Get a Notion client, or return an error dict if no credentials."""
        api_key = _get_api_key()
        if not api_key:
            return {
                "error": "Notion credentials not configured",
                "help": (
                    "Set NOTION_API_KEY environment variable "
                    "or configure via credential store. "
                    "Get your key at https://www.notion.so/my-integrations"
                ),
            }
        return _NotionClient(api_key)

    @mcp.tool()
    def notion_search(
        query: str = "",
        filter_type: str | None = None,
        page_size: int = 10,
    ) -> dict:
        """
        Search Notion pages and databases.

        Args:
            query: Search query string (searches titles and content)
            filter_type: Filter results by type: "page" or "database" (optional)
            page_size: Maximum number of results (1-100, default 10)

        Returns:
            Dict with search results containing pages and/or databases
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.search(query, filter_type, page_size)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def notion_get_page(
        page_id: str,
        include_content: bool = False,
    ) -> dict:
        """
        Get a Notion page by ID.

        Args:
            page_id: The Notion page ID (UUID format, with or without dashes)
            include_content: If True, also fetch the page's block content

        Returns:
            Dict with page properties and optionally its content blocks
        """
        if not page_id:
            return {"error": "page_id is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.get_page(page_id)
            if "error" in result:
                return result

            if include_content:
                content = client.get_page_content(page_id)
                if "error" not in content:
                    result["content"] = content.get("results", [])

            return result
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def notion_create_page(
        parent_id: str,
        title: str,
        parent_type: str = "page",
        content: list[dict] | None = None,
        properties: dict | None = None,
    ) -> dict:
        """
        Create a new Notion page.

        Args:
            parent_id: The parent page ID or database ID
            title: The page title
            parent_type: Type of parent: "page" or "database" (default "page")
            content: Optional list of block objects for page content.
                Example: [{"type": "paragraph", "paragraph": {"rich_text": [...]}}]
            properties: Optional properties dict (required for database pages with custom schema)

        Returns:
            Dict with created page data or error
        """
        if not parent_id:
            return {"error": "parent_id is required"}
        if not title:
            return {"error": "title is required"}
        if parent_type not in ("page", "database"):
            return {"error": "parent_type must be 'page' or 'database'"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_page(parent_id, parent_type, title, content, properties)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def notion_update_page(
        page_id: str,
        properties: dict | None = None,
        archived: bool | None = None,
    ) -> dict:
        """
        Update a Notion page's properties or archive it.

        Args:
            page_id: The Notion page ID to update
            properties: Properties to update (format depends on page's parent type).
                For title: {"title": {"title": [{"text": {"content": "New Title"}}]}}
            archived: Set to True to archive the page, False to unarchive

        Returns:
            Dict with updated page data or error
        """
        if not page_id:
            return {"error": "page_id is required"}
        if properties is None and archived is None:
            return {"error": "At least one of 'properties' or 'archived' must be provided"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.update_page(page_id, properties, archived)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def notion_query_database(
        database_id: str,
        filter_conditions: dict | None = None,
        sorts: list[dict] | None = None,
        page_size: int = 10,
    ) -> dict:
        """
        Query a Notion database with optional filters and sorting.

        Args:
            database_id: The Notion database ID
            filter_conditions: Optional filter object. Example:
                {"property": "Status", "select": {"equals": "Done"}}
            sorts: Optional list of sort objects. Example:
                [{"property": "Created", "direction": "descending"}]
            page_size: Maximum number of results (1-100, default 10)

        Returns:
            Dict with query results (list of pages in the database)
        """
        if not database_id:
            return {"error": "database_id is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.query_database(database_id, filter_conditions, sorts, page_size)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def notion_append_blocks(
        block_id: str,
        children: list[dict],
    ) -> dict:
        """
        Append content blocks to an existing Notion page or block.

        Args:
            block_id: The page ID or block ID to append children to
            children: List of block objects to append. Example:
                [
                    {"type": "paragraph", "paragraph": {"rich_text": [...]}},
                    {"type": "heading_2", "heading_2": {"rich_text": [...]}},
                    {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [...]}}
                ]

        Returns:
            Dict with the appended blocks or error
        """
        if not block_id:
            return {"error": "block_id is required"}
        if not children:
            return {"error": "children is required and cannot be empty"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.append_blocks(block_id, children)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
