"""
Salesforce CRM Tool - Manage leads, contacts, opportunities, and execute SOQL queries.

API Reference: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

DEFAULT_API_VERSION = "v60.0"


class _SalesforceClient:
    """Internal client wrapping Salesforce REST API calls."""

    def __init__(self, instance_url: str, access_token: str, api_version: str = DEFAULT_API_VERSION):
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"{self.instance_url}/services/data/{self.api_version}"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Salesforce access token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions. Check your Salesforce OAuth scopes."}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "Salesforce rate limit exceeded."}
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                if isinstance(error_data, list) and len(error_data) > 0:
                    detail = error_data[0].get("message", response.text)
                else:
                    detail = error_data.get("message", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Salesforce API error (HTTP {response.status_code}): {detail}"}
        
        if response.status_code == 204:  # No Content (successful update/delete)
            return {"success": True}
        
        try:
            return response.json()
        except Exception:
            return {"success": True, "text": response.text}

    def query(self, soql: str) -> dict[str, Any]:
        """Execute a SOQL query."""
        response = httpx.get(
            f"{self.base_url}/query",
            headers=self._headers,
            params={"q": soql},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_record(self, object_name: str, record_id: str, fields: list[str] | None = None) -> dict[str, Any]:
        """Get a record by ID."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        
        response = httpx.get(
            f"{self.base_url}/sobjects/{object_name}/{record_id}",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_record(self, object_name: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a new record."""
        response = httpx.post(
            f"{self.base_url}/sobjects/{object_name}",
            headers=self._headers,
            json=fields,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_record(self, object_name: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update an existing record."""
        response = httpx.patch(
            f"{self.base_url}/sobjects/{object_name}/{record_id}",
            headers=self._headers,
            json=fields,
            timeout=30.0,
        )
        return self._handle_response(response)

    def describe_object(self, object_name: str) -> dict[str, Any]:
        """Get object metadata."""
        response = httpx.get(
            f"{self.base_url}/sobjects/{object_name}/describe",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Salesforce CRM tools with the MCP server."""

    def _get_credentials() -> tuple[str | None, str | None]:
        """Get Salesforce credentials from credential manager or environment."""
        instance_url = None
        access_token = None

        if credentials is not None:
            instance_url = credentials.get("salesforce_instance_url")
            access_token = credentials.get("salesforce_access_token")

        if not instance_url:
            instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        if not access_token:
            access_token = os.getenv("SALESFORCE_ACCESS_TOKEN")

        return instance_url, access_token

    def _get_client() -> _SalesforceClient | dict[str, str]:
        """Get a Salesforce client, or return an error dict if no credentials."""
        instance_url, access_token = _get_credentials()
        if not instance_url or not access_token:
            return {
                "error": "Salesforce credentials not configured",
                "help": (
                    "Set SALESFORCE_INSTANCE_URL and SALESFORCE_ACCESS_TOKEN environment variables "
                    "or configure via credential store"
                ),
            }
        return _SalesforceClient(instance_url, access_token)

    @mcp.tool()
    def salesforce_query(soql_query: str) -> dict:
        """
        Execute a SOQL (Salesforce Object Query Language) query.

        Args:
            soql_query: The SOQL query to execute (e.g., "SELECT Id, Name FROM Lead WHERE Status = 'Open'")

        Returns:
            Dict with query results or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.query(soql_query)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def salesforce_create_record(object_name: str, fields: dict[str, Any]) -> dict:
        """
        Create a new record in Salesforce.

        Args:
            object_name: The API name of the object (e.g., 'Lead', 'Contact', 'Opportunity')
            fields: A dictionary of field names and values to set

        Returns:
            Dict with created record ID or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_record(object_name, fields)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def salesforce_update_record(object_name: str, record_id: str, fields: dict[str, Any]) -> dict:
        """
        Update an existing record in Salesforce.

        Args:
            object_name: The API name of the object
            record_id: The Salesforce record ID
            fields: A dictionary of field names and values to update

        Returns:
            Dict indicating success or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.update_record(object_name, record_id, fields)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def salesforce_get_record(object_name: str, record_id: str, fields: list[str] | None = None) -> dict:
        """
        Get a record from Salesforce by ID.

        Args:
            object_name: The API name of the object
            record_id: The Salesforce record ID
            fields: Optional list of fields to return

        Returns:
            Dict with record data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_record(object_name, record_id, fields)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def salesforce_describe_object(object_name: str) -> dict:
        """
        Get metadata (fields, picklist values, etc.) for a Salesforce object.

        Args:
            object_name: The API name of the object

        Returns:
            Dict with object metadata or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.describe_object(object_name)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Convenience wrappers for Leads, Contacts, Opportunities ---

    @mcp.tool()
    def salesforce_search_leads(query: str, limit: int = 10) -> dict:
        """
        Search for leads by name or email using SOQL.

        Args:
            query: Name or email to search for
            limit: Maximum results to return (default 10)
        """
        soql = f"SELECT Id, Name, Email, Status, Company FROM Lead WHERE Name LIKE '%{query}%' OR Email LIKE '%{query}%' LIMIT {limit}"
        return salesforce_query(soql)

    @mcp.tool()
    def salesforce_search_contacts(query: str, limit: int = 10) -> dict:
        """
        Search for contacts by name or email using SOQL.

        Args:
            query: Name or email to search for
            limit: Maximum results to return (default 10)
        """
        soql = f"SELECT Id, Name, Email, Account.Name FROM Contact WHERE Name LIKE '%{query}%' OR Email LIKE '%{query}%' LIMIT {limit}"
        return salesforce_query(soql)

    @mcp.tool()
    def salesforce_search_opportunities(query: str, limit: int = 10) -> dict:
        """
        Search for opportunities by name using SOQL.

        Args:
            query: Opportunity name to search for
            limit: Maximum results to return (default 10)
        """
        soql = f"SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE Name LIKE '%{query}%' LIMIT {limit}"
        return salesforce_query(soql)
