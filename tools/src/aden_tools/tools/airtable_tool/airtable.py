"""
Airtable integration tool for MCP Server.

Provides comprehensive Airtable API functionality:
- List bases (with optional table listing)
- List records (with filter/sort support)
- Create and update records

Authentication: Personal Access Token (PAT).

API Reference: https://airtable.com/developers/web/api
"""

import json
import logging
from typing import Any

import httpx
from fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)

# Constants
AIRTABLE_BASE_URL = "https://api.airtable.com/v0"
AIRTABLE_META_URL = "https://api.airtable.com/v0/meta"
DEFAULT_TIMEOUT = 30.0
MAX_PAGE_SIZE = 100  # Airtable default max page size


class AirtableClient:
    """
    Airtable API client.

    Handles authentication and provides methods for all Airtable operations.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the Airtable client.

        Args:
            api_key: Personal Access Token for Airtable API.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the Airtable API.

        Args:
            method: HTTP method (GET, POST, PATCH).
            url: Full URL to request.
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Response JSON as a dictionary.

        Raises:
            httpx.HTTPStatusError: If request fails with non-2xx status.
        """
        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self._headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

    def list_bases(self) -> list[dict[str, Any]]:
        """
        List all accessible bases.

        Returns:
            List of base objects with 'id', 'name', and 'permissionLevel'.
        """
        url = f"{AIRTABLE_META_URL}/bases"
        all_bases = []
        offset = None

        while True:
            params = {}
            if offset:
                params["offset"] = offset

            response = self._make_request("GET", url, params=params)
            bases = response.get("bases", [])
            all_bases.extend(bases)

            offset = response.get("offset")
            if not offset:
                break

        return all_bases

    def list_tables(self, base_id: str) -> list[dict[str, Any]]:
        """
        List all tables in a base.

        Args:
            base_id: The ID of the base.

        Returns:
            List of table objects with 'id', 'name', 'description', 'fields'.
        """
        url = f"{AIRTABLE_META_URL}/bases/{base_id}/tables"
        response = self._make_request("GET", url)
        return response.get("tables", [])

    def list_records(
        self,
        base_id: str,
        table_id_or_name: str,
        filter_by_formula: str | None = None,
        sort: list[dict[str, str]] | None = None,
        max_records: int | None = None,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        List records in a table with optional filtering and sorting.

        Args:
            base_id: The ID of the base.
            table_id_or_name: The ID or name of the table.
            filter_by_formula: Airtable formula for filtering records.
            sort: List of sort specifications (e.g., [{"field": "Name", "direction": "asc"}]).
            max_records: Maximum number of records to return.
            fields: List of field names to return (returns all if not specified).

        Returns:
            List of record objects.
        """
        url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id_or_name}"
        all_records = []
        offset = None
        records_fetched = 0
        limit = max_records if max_records else float("inf")

        while records_fetched < limit:
            params: dict[str, Any] = {"pageSize": min(MAX_PAGE_SIZE, limit - records_fetched)}

            if offset:
                params["offset"] = offset
            if filter_by_formula:
                params["filterByFormula"] = filter_by_formula
            if sort:
                for i, s in enumerate(sort):
                    params[f"sort[{i}][field]"] = s.get("field")
                    params[f"sort[{i}][direction]"] = s.get("direction", "asc")
            if fields:
                params["fields[]"] = fields

            response = self._make_request("GET", url, params=params)
            records = response.get("records", [])
            all_records.extend(records)
            records_fetched += len(records)

            offset = response.get("offset")
            if not offset:
                break

        return all_records

    def create_record(
        self,
        base_id: str,
        table_id_or_name: str,
        fields: dict[str, Any],
        typecast: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new record in a table.

        Args:
            base_id: The ID of the base.
            table_id_or_name: The ID or name of the table.
            fields: Dictionary of field names to values.
            typecast: Whether to enable automatic type conversion.

        Returns:
            The created record object.
        """
        url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id_or_name}"
        data: dict[str, Any] = {"fields": fields}
        if typecast:
            data["typecast"] = True

        return self._make_request("POST", url, json_data=data)

    def update_record(
        self,
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        fields: dict[str, Any],
        typecast: bool = False,
    ) -> dict[str, Any]:
        """
        Update an existing record by ID.

        Args:
            base_id: The ID of the base.
            table_id_or_name: The ID or name of the table.
            record_id: The ID of the record to update.
            fields: Dictionary of field names to new values.
            typecast: Whether to enable automatic type conversion.

        Returns:
            The updated record object.
        """
        url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id_or_name}/{record_id}"
        data: dict[str, Any] = {"fields": fields}
        if typecast:
            data["typecast"] = True

        return self._make_request("PATCH", url, json_data=data)


def _get_client(credentials) -> AirtableClient | None:
    """
    Create an AirtableClient from credentials.

    Args:
        credentials: CredentialManager instance.

    Returns:
        AirtableClient if credentials are available, None otherwise.
    """
    if not credentials:
        return None

    try:
        credentials.validate_for_tools(["airtable_list_bases"])
        api_key = credentials.get("airtable_api_key")
        if api_key:
            return AirtableClient(api_key)
        return None
    except Exception as e:
        logger.error(f"Failed to get Airtable credentials: {e}")
        return None


def register_tools(mcp: FastMCP, credentials=None):
    """
    Register Airtable tools with the MCP server.

    Args:
        mcp: FastMCP server instance.
        credentials: Optional CredentialManager for API key access.
    """

    @mcp.tool(
        name="airtable_list_bases",
        description=(
            "List all Airtable bases accessible with the configured API key. "
            "Returns base IDs, names, and permission levels."
        ),
    )
    def airtable_list_bases(ctx: Context = None) -> str:
        """
        List all accessible Airtable bases.

        Returns:
            JSON string containing list of bases with 'id', 'name',
            and 'permissionLevel'.
        """
        client = _get_client(credentials)
        if not client:
            return json.dumps({
                "error": "Missing Airtable credentials. "
                "Set AIRTABLE_API_KEY environment variable."
            })

        try:
            bases = client.list_bases()
            return json.dumps({"bases": bases}, indent=2, default=str)
        except httpx.HTTPStatusError as e:
            logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": f"Airtable API error: {e.response.status_code}",
                "details": e.response.text,
            })
        except Exception as e:
            logger.error(f"Error listing bases: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="airtable_list_tables",
        description=(
            "List all tables in an Airtable base. "
            "Returns table IDs, names, descriptions, and field schemas."
        ),
    )
    def airtable_list_tables(base_id: str, ctx: Context = None) -> str:
        """
        List all tables in a base.

        Args:
            base_id: The ID of the Airtable base (e.g., 'appXXXXXXX').

        Returns:
            JSON string containing list of tables with their schemas.
        """
        client = _get_client(credentials)
        if not client:
            return json.dumps({
                "error": "Missing Airtable credentials. "
                "Set AIRTABLE_API_KEY environment variable."
            })

        try:
            tables = client.list_tables(base_id)
            return json.dumps({"tables": tables}, indent=2, default=str)
        except httpx.HTTPStatusError as e:
            logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": f"Airtable API error: {e.response.status_code}",
                "details": e.response.text,
            })
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="airtable_list_records",
        description=(
            "List records in an Airtable table with optional filtering and sorting. "
            "Supports Airtable formula filtering (e.g., \"{Status}='Active'\") "
            "and multi-field sorting."
        ),
    )
    def airtable_list_records(
        base_id: str,
        table_id_or_name: str,
        filter_by_formula: str | None = None,
        sort_field: str | None = None,
        sort_direction: str | None = None,
        max_records: int | None = None,
        fields: str | None = None,
        ctx: Context = None,
    ) -> str:
        """
        List records in a table.

        Args:
            base_id: The ID of the Airtable base.
            table_id_or_name: The table ID (e.g., 'tblXXX') or name (e.g., 'Leads').
            filter_by_formula: Airtable formula for filtering
                (e.g., "{Status}='Contacted'").
            sort_field: Field name to sort by.
            sort_direction: Sort direction ('asc' or 'desc').
            max_records: Maximum number of records to return.
            fields: Comma-separated list of field names to return.

        Returns:
            JSON string containing list of records.
        """
        client = _get_client(credentials)
        if not client:
            return json.dumps({
                "error": "Missing Airtable credentials. "
                "Set AIRTABLE_API_KEY environment variable."
            })

        try:
            sort = None
            if sort_field:
                sort = [{"field": sort_field, "direction": sort_direction or "asc"}]

            field_list = None
            if fields:
                field_list = [f.strip() for f in fields.split(",")]

            records = client.list_records(
                base_id=base_id,
                table_id_or_name=table_id_or_name,
                filter_by_formula=filter_by_formula,
                sort=sort,
                max_records=max_records,
                fields=field_list,
            )
            return json.dumps({"records": records}, indent=2, default=str)
        except httpx.HTTPStatusError as e:
            logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": f"Airtable API error: {e.response.status_code}",
                "details": e.response.text,
            })
        except Exception as e:
            logger.error(f"Error listing records: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="airtable_create_record",
        description=(
            "Create a new record in an Airtable table. "
            "Fields are provided as a JSON object mapping field names to values."
        ),
    )
    def airtable_create_record(
        base_id: str,
        table_id_or_name: str,
        fields_json: str,
        typecast: bool = False,
        ctx: Context = None,
    ) -> str:
        """
        Create a new record in a table.

        Args:
            base_id: The ID of the Airtable base.
            table_id_or_name: The table ID or name.
            fields_json: JSON string of field name to value mappings
                (e.g., '{"Name": "John Doe", "Status": "Contacted"}').
            typecast: If true, Airtable will try to convert string values to
                appropriate types.

        Returns:
            JSON string of the created record.
        """
        client = _get_client(credentials)
        if not client:
            return json.dumps({
                "error": "Missing Airtable credentials. "
                "Set AIRTABLE_API_KEY environment variable."
            })

        try:
            fields = json.loads(fields_json)
            if not isinstance(fields, dict):
                return json.dumps({"error": "fields_json must be a JSON object"})

            record = client.create_record(
                base_id=base_id,
                table_id_or_name=table_id_or_name,
                fields=fields,
                typecast=typecast,
            )
            return json.dumps(record, indent=2, default=str)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in fields_json: {e}"})
        except httpx.HTTPStatusError as e:
            logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": f"Airtable API error: {e.response.status_code}",
                "details": e.response.text,
            })
        except Exception as e:
            logger.error(f"Error creating record: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="airtable_update_record",
        description=(
            "Update an existing record in an Airtable table by its record ID. "
            "Only the specified fields are updated; other fields remain unchanged."
        ),
    )
    def airtable_update_record(
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        fields_json: str,
        typecast: bool = False,
        ctx: Context = None,
    ) -> str:
        """
        Update an existing record by ID.

        Args:
            base_id: The ID of the Airtable base.
            table_id_or_name: The table ID or name.
            record_id: The ID of the record to update (e.g., 'recXXXXXX').
            fields_json: JSON string of field name to value mappings to update.
            typecast: If true, Airtable will try to convert string values to
                appropriate types.

        Returns:
            JSON string of the updated record.
        """
        client = _get_client(credentials)
        if not client:
            return json.dumps({
                "error": "Missing Airtable credentials. "
                "Set AIRTABLE_API_KEY environment variable."
            })

        try:
            fields = json.loads(fields_json)
            if not isinstance(fields, dict):
                return json.dumps({"error": "fields_json must be a JSON object"})

            record = client.update_record(
                base_id=base_id,
                table_id_or_name=table_id_or_name,
                record_id=record_id,
                fields=fields,
                typecast=typecast,
            )
            return json.dumps(record, indent=2, default=str)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in fields_json: {e}"})
        except httpx.HTTPStatusError as e:
            logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": f"Airtable API error: {e.response.status_code}",
                "details": e.response.text,
            })
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            return json.dumps({"error": str(e)})
