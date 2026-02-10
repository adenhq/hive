"""
Salesforce Tool - Interact with Salesforce data via the REST API.

Supports:
- OAuth2 Access Tokens (SALESFORCE_ACCESS_TOKEN)
- Instance URL (SALESFORCE_INSTANCE_URL)

API Reference: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

# Default API version if not specified
DEFAULT_API_VERSION = "v60.0"


class _SalesforceClient:
    """Internal client wrapping Salesforce REST API calls."""

    def __init__(
        self, access_token: str, instance_url: str, api_version: str = DEFAULT_API_VERSION
    ):
        self._access_token = access_token
        self._instance_url = instance_url.rstrip("/")
        self._api_version = api_version

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def _base_url(self) -> str:
        return f"{self._instance_url}/services/data/{self._api_version}"

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle Salesforce API response format."""
        if response.status_code == 204:
            return {"success": True}

        try:
            data = response.json()
        except Exception:
            # If JSON parsing fails but status is error, return error
            if response.status_code >= 400:
                return {
                    "error": f"HTTP error {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                }
            return {"success": True, "text": response.text}

        # Check for Salesforce error array format
        if (
            isinstance(data, list)
            and len(data) > 0
            and isinstance(data[0], dict)
            and "errorCode" in data[0]
        ):
            return {"error": data[0]["message"], "code": data[0]["errorCode"]}

        # Check for error object format
        if isinstance(data, dict) and "error" in data:
            return {"error": data.get("error_description", data["error"])}

        if response.status_code >= 400:
            return {
                "error": f"HTTP error {response.status_code}",
                "details": data,
                "status_code": response.status_code,
            }

        return data

    def query(self, query_string: str) -> dict[str, Any]:
        """Execute a SOQL query."""
        response = httpx.get(
            f"{self._base_url}/query",
            headers=self._headers,
            params={"q": query_string},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_record(
        self, sobject: str, record_id: str, fields: list[str] | None = None
    ) -> dict[str, Any]:
        """Retrieve a specific record by ID."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = httpx.get(
            f"{self._base_url}/sobjects/{sobject}/{record_id}",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_record(self, sobject: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new record."""
        response = httpx.post(
            f"{self._base_url}/sobjects/{sobject}",
            headers=self._headers,
            json=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_record(self, sobject: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing record."""
        response = httpx.patch(
            f"{self._base_url}/sobjects/{sobject}/{record_id}",
            headers=self._headers,
            json=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_record(self, sobject: str, record_id: str) -> dict[str, Any]:
        """Delete a record."""
        response = httpx.delete(
            f"{self._base_url}/sobjects/{sobject}/{record_id}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_limits(self) -> dict[str, Any]:
        """Check API usage limits."""
        response = httpx.get(
            f"{self._base_url}/limits",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)


# -----------------------------------------------------------------------------
# Tool Definitions
# -----------------------------------------------------------------------------


def register_tools(mcp: FastMCP, credential_store: CredentialStoreAdapter | None = None) -> None:
    """Register Salesforce tools with the MCP server."""

    def _get_client(
        user_access_token: str | None = None, user_instance_url: str | None = None
    ) -> _SalesforceClient:
        # 1. Try passed arguments (e.g. from agent input)
        # 2. Try environment variables
        token = user_access_token or os.environ.get("SALESFORCE_ACCESS_TOKEN")
        instance_url = user_instance_url or os.environ.get("SALESFORCE_INSTANCE_URL")

        # 3. Try Credential Store if available
        if (not token or not instance_url) and credential_store:
            # Basic lookup naming convention 'salesforce'
            creds = credential_store.get_credential("salesforce")
            if creds:
                token = token or creds.get("access_token")
                instance_url = instance_url or creds.get("instance_url")

        if not token:
            raise ValueError(
                "Salesforce Access Token is required. Set SALESFORCE_ACCESS_TOKEN env var."
            )
        if not instance_url:
            raise ValueError(
                "Salesforce Instance URL is required. Set SALESFORCE_INSTANCE_URL env var."
            )

        return _SalesforceClient(token, instance_url)

    @mcp.tool()
    def salesforce_soql_query(
        query: str, access_token: str | None = None, instance_url: str | None = None
    ) -> str:
        """Execute a SOQL query to search or retrieve data from Salesforce.

        Args:
            query: The SOQL query string
                   (e.g., "SELECT Id, Name, Email FROM Contact WHERE Email LIKE '%@example.com%'")
            access_token: Optional access token override
            instance_url: Optional instance URL override
        """
        try:
            client = _get_client(access_token, instance_url)
            result = client.query(query)

            if "error" in result:
                return f"Error executing query: {result['error']}"

            records = result.get("records", [])
            total_size = result.get("totalSize", 0)

            # Simple string representation for agent consumption
            # We strip out the messy 'attributes' metadata field from records to keep it clean
            clean_records = []
            for record in records:
                if "attributes" in record:
                    del record["attributes"]
                clean_records.append(record)

            return f"Found {total_size} records. Top results:\n{clean_records}"

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def salesforce_get_record(
        sobject: str,
        record_id: str,
        fields: list[str] | None = None,
        access_token: str | None = None,
        instance_url: str | None = None,
    ) -> str:
        """Retrieve a single record from Salesforce by ID.

        Args:
            sobject: The API name of the object (e.g., "Account", "Contact", "CustomObject__c")
            record_id: The 15 or 18 character Salesforce ID
            fields: Optional list of specific fields to retrieve (defaults to all)
            access_token: Optional access token override
            instance_url: Optional instance URL override
        """
        try:
            client = _get_client(access_token, instance_url)
            result = client.get_record(sobject, record_id, fields)

            if "error" in result:
                return f"Error retrieving record: {result['error']}"

            if "attributes" in result:
                del result["attributes"]

            return str(result)

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def salesforce_create_record(
        sobject: str,
        data: dict[str, Any],
        access_token: str | None = None,
        instance_url: str | None = None,
    ) -> str:
        """Create a new record in Salesforce.

        Args:
            sobject: The API name of the object (e.g., "Lead", "Case")
            data: A dictionary of field API names and values to set
            access_token: Optional access token override
            instance_url: Optional instance URL override
        """
        try:
            client = _get_client(access_token, instance_url)
            result = client.create_record(sobject, data)

            if "error" in result:
                return f"Error creating record: {result['error']}"

            return f"Successfully created record. ID: {result.get('id')}"

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def salesforce_update_record(
        sobject: str,
        record_id: str,
        data: dict[str, Any],
        access_token: str | None = None,
        instance_url: str | None = None,
    ) -> str:
        """Update an existing record in Salesforce.

        Args:
            sobject: The API name of the object
            record_id: The ID of the record to update
            data: A dictionary of fields to update
            access_token: Optional access token override
            instance_url: Optional instance URL override
        """
        try:
            client = _get_client(access_token, instance_url)
            result = client.update_record(sobject, record_id, data)

            if "error" in result:
                return f"Error updating record: {result['error']}"

            return "Successfully updated record."

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def salesforce_get_limits(
        access_token: str | None = None, instance_url: str | None = None
    ) -> str:
        """Check API usage limits for the Salesforce organization.

        Args:
            access_token: Optional access token override
            instance_url: Optional instance URL override
        """
        try:
            client = _get_client(access_token, instance_url)
            result = client.get_limits()

            if "error" in result:
                return f"Error fetching limits: {result['error']}"

            # Extract just the DailyApiRequests for brevity, or return full dict str
            api_usage = result.get("DailyApiRequests", {})
            return f"API Usage: {api_usage}"

        except Exception as e:
            return f"Error: {str(e)}"
