"""
Pipedrive CRM Tool - Manage persons, deals, and notes via Pipedrive API v1.

Supports:
- Personal API tokens (PIPEDRIVE_API_TOKEN)
- API tokens via the credential store

API Reference: https://developers.pipedrive.com/docs/api/v1
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

PIPEDRIVE_API_BASE = "https://api.pipedrive.com/v1"


class _PipedriveClient:
    """Internal client wrapping Pipedrive CRM API v1 calls."""

    def __init__(self, api_token: str):
        self._token = api_token

    @property
    def _params(self) -> dict[str, str]:
        return {"api_token": self._token}

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Pipedrive API token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions. Check your Pipedrive token scopes."}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 410:
            return {"error": "Resource gone (deleted)"}
        if response.status_code == 429:
            return {"error": "Pipedrive rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Pipedrive API error (HTTP {response.status_code}): {detail}"}
        
        try:
            return response.json()
        except Exception as e:
            return {"error": f"Failed to parse JSON response: {e}"}

    def create_person(self, name: str, email: str | list[str] | None = None, phone: str | list[str] | None = None, **kwargs) -> dict[str, Any]:
        """Create a new person."""
        body = {"name": name, **kwargs}
        if email:
            body["email"] = email
        if phone:
            body["phone"] = phone
        
        response = httpx.post(
            f"{PIPEDRIVE_API_BASE}/persons",
            headers=self._headers,
            params=self._params,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def search_persons(self, term: str, fields: str = "email", exact_match: bool = False) -> dict[str, Any]:
        """Search for persons by email or other terms."""
        params = self._params.copy()
        params["term"] = term
        params["fields"] = fields
        if exact_match:
            params["exact_match"] = "true"
        
        response = httpx.get(
            f"{PIPEDRIVE_API_BASE}/persons/search",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_person(self, person_id: int) -> dict[str, Any]:
        """Get details of a person by ID."""
        response = httpx.get(
            f"{PIPEDRIVE_API_BASE}/persons/{person_id}",
            headers=self._headers,
            params=self._params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_deal(self, title: str, person_id: int | None = None, org_id: int | None = None, value: float | None = None, currency: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a new deal."""
        body = {"title": title, **kwargs}
        if person_id:
            body["person_id"] = person_id
        if org_id:
            body["org_id"] = org_id
        if value is not None:
            body["value"] = value
        if currency:
            body["currency"] = currency
        
        response = httpx.post(
            f"{PIPEDRIVE_API_BASE}/deals",
            headers=self._headers,
            params=self._params,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_deal(self, deal_id: int, **kwargs) -> dict[str, Any]:
        """Update an existing deal (e.g., stage_id, status, value)."""
        response = httpx.put(
            f"{PIPEDRIVE_API_BASE}/deals/{deal_id}",
            headers=self._headers,
            params=self._params,
            json=kwargs,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_deals(self, user_id: int | None = None, filter_id: int | None = None, status: str | None = None, limit: int = 10) -> dict[str, Any]:
        """List deals with optional filtering."""
        params = self._params.copy()
        if user_id:
            params["user_id"] = str(user_id)
        if filter_id:
            params["filter_id"] = str(filter_id)
        if status:
            params["status"] = status
        params["limit"] = str(min(limit, 100))
        
        response = httpx.get(
            f"{PIPEDRIVE_API_BASE}/deals",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def add_note(self, content: str, deal_id: int | None = None, person_id: int | None = None, org_id: int | None = None) -> dict[str, Any]:
        """Add a note to a deal, person, or organization."""
        body = {"content": content}
        if deal_id:
            body["deal_id"] = deal_id
        if person_id:
            body["person_id"] = person_id
        if org_id:
            body["org_id"] = org_id
        
        response = httpx.post(
            f"{PIPEDRIVE_API_BASE}/notes",
            headers=self._headers,
            params=self._params,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Pipedrive CRM tools with the MCP server."""

    def _get_token() -> str | None:
        """Get Pipedrive API token from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("pipedrive")
            if token is not None and not isinstance(token, str):
                raise TypeError(
                    f"Expected string from credentials.get('pipedrive'), got {type(token).__name__}"
                )
            return token
        return os.getenv("PIPEDRIVE_API_TOKEN")

    def _get_client() -> _PipedriveClient | dict[str, str]:
        """Get a Pipedrive client, or return an error dict if no credentials."""
        token = _get_token()
        if not token:
            return {
                "error": "Pipedrive credentials not configured",
                "help": (
                    "Set PIPEDRIVE_API_TOKEN environment variable "
                    "or configure via credential store"
                ),
            }
        return _PipedriveClient(token)

    # --- Persons ---

    @mcp.tool()
    def pipedrive_create_person(
        name: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> dict:
        """
        Create a new person in Pipedrive.

        Args:
            name: Name of the person
            email: Email address of the person
            phone: Phone number of the person

        Returns:
            Dict with created person data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_person(name=name, email=email, phone=phone)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pipedrive_search_person(
        email: str,
    ) -> dict:
        """
        Search for a person in Pipedrive by email.

        Args:
            email: Email address to search for

        Returns:
            Dict with search results or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.search_persons(term=email, fields="email", exact_match=True)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pipedrive_get_person_details(
        person_id: int,
    ) -> dict:
        """
        Get full details of a Pipedrive person by ID.

        Args:
            person_id: The Pipedrive person ID

        Returns:
            Dict with person data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_person(person_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Deals ---

    @mcp.tool()
    def pipedrive_create_deal(
        title: str,
        person_id: int | None = None,
        value: float | None = None,
        currency: str | None = None,
    ) -> dict:
        """
        Create a new deal in Pipedrive.

        Args:
            title: Title of the deal
            person_id: Optional ID of the person this deal is associated with
            value: Optional monetary value of the deal
            currency: Optional currency code (e.g., 'USD', 'EUR')

        Returns:
            Dict with created deal data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_deal(title=title, person_id=person_id, value=value, currency=currency)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pipedrive_update_deal_stage(
        deal_id: int,
        stage_id: int,
    ) -> dict:
        """
        Update the stage of an existing Pipedrive deal.

        Args:
            deal_id: The Pipedrive deal ID
            stage_id: The ID of the new stage

        Returns:
            Dict with updated deal data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.update_deal(deal_id, stage_id=stage_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pipedrive_list_deals(
        status: str | None = "open",
        limit: int = 10,
    ) -> dict:
        """
        List deals from Pipedrive.

        Args:
            status: Optional filter by status ('open', 'won', 'lost', 'deleted', 'all_not_deleted')
            limit: Maximum number of deals to return (default 10)

        Returns:
            Dict with deals list or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_deals(status=status, limit=limit)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Notes ---

    @mcp.tool()
    def pipedrive_add_note_to_deal(
        deal_id: int,
        content: str,
    ) -> dict:
        """
        Add a note to a Pipedrive deal.

        Args:
            deal_id: The Pipedrive deal ID
            content: The text content of the note (can be HTML)

        Returns:
            Dict with created note data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.add_note(content=content, deal_id=deal_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
