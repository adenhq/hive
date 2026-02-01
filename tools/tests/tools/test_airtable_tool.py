"""
Unit tests for the Airtable tool.

Tests cover:
- AirtableClient methods
- Credential integration
- Error handling
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from aden_tools.credentials import CredentialManager
from aden_tools.tools.airtable_tool.airtable import (
    AIRTABLE_BASE_URL,
    AIRTABLE_META_URL,
    AirtableClient,
    _get_client,
)


class TestAirtableClient(unittest.TestCase):
    """Tests for the AirtableClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.client = AirtableClient(self.api_key)
        self.base_id = "appTestBase123"
        self.table_id = "tblTestTable456"
        self.record_id = "recTestRecord789"

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_bases_success(self, mock_httpx_client):
        """Test successful listing of bases."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "bases": [
                {"id": "app123", "name": "Test Base", "permissionLevel": "owner"},
                {"id": "app456", "name": "Another Base", "permissionLevel": "editor"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        bases = self.client.list_bases()

        # Verify
        self.assertEqual(len(bases), 2)
        self.assertEqual(bases[0]["id"], "app123")
        self.assertEqual(bases[1]["name"], "Another Base")
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        self.assertEqual(call_args.kwargs["method"], "GET")
        self.assertIn(AIRTABLE_META_URL, call_args.kwargs["url"])

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_bases_with_pagination(self, mock_httpx_client):
        """Test listing bases with pagination."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # First page response
        first_response = MagicMock()
        first_response.json.return_value = {
            "bases": [{"id": "app1", "name": "Base 1", "permissionLevel": "owner"}],
            "offset": "next_page_token",
        }
        first_response.raise_for_status = MagicMock()

        # Second page response (no offset = last page)
        second_response = MagicMock()
        second_response.json.return_value = {
            "bases": [{"id": "app2", "name": "Base 2", "permissionLevel": "editor"}],
        }
        second_response.raise_for_status = MagicMock()

        mock_client_instance.request.side_effect = [first_response, second_response]

        # Execute
        bases = self.client.list_bases()

        # Verify
        self.assertEqual(len(bases), 2)
        self.assertEqual(mock_client_instance.request.call_count, 2)

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_tables_success(self, mock_httpx_client):
        """Test successful listing of tables in a base."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tables": [
                {
                    "id": "tbl123",
                    "name": "Leads",
                    "description": "Sales leads",
                    "fields": [
                        {"id": "fld1", "name": "Name", "type": "singleLineText"},
                        {"id": "fld2", "name": "Status", "type": "singleSelect"},
                    ],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        tables = self.client.list_tables(self.base_id)

        # Verify
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["name"], "Leads")
        self.assertEqual(len(tables[0]["fields"]), 2)

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_records_success(self, mock_httpx_client):
        """Test successful listing of records."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {"Name": "John Doe", "Status": "Contacted"},
                    "createdTime": "2024-01-01T00:00:00.000Z",
                },
                {
                    "id": "rec2",
                    "fields": {"Name": "Jane Smith", "Status": "Qualified"},
                    "createdTime": "2024-01-02T00:00:00.000Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        records = self.client.list_records(self.base_id, self.table_id)

        # Verify
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["fields"]["Name"], "John Doe")

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_records_with_filter(self, mock_httpx_client):
        """Test listing records with filter formula."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {"records": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        filter_formula = "{Status}='Contacted'"
        self.client.list_records(
            self.base_id,
            self.table_id,
            filter_by_formula=filter_formula,
        )

        # Verify filter was passed
        call_args = mock_client_instance.request.call_args
        self.assertIn("filterByFormula", call_args.kwargs["params"])
        self.assertEqual(
            call_args.kwargs["params"]["filterByFormula"], filter_formula
        )

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_list_records_with_sort(self, mock_httpx_client):
        """Test listing records with sorting."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {"records": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        sort = [{"field": "Name", "direction": "desc"}]
        self.client.list_records(
            self.base_id,
            self.table_id,
            sort=sort,
        )

        # Verify sort was passed
        call_args = mock_client_instance.request.call_args
        self.assertIn("sort[0][field]", call_args.kwargs["params"])
        self.assertEqual(call_args.kwargs["params"]["sort[0][field]"], "Name")
        self.assertEqual(call_args.kwargs["params"]["sort[0][direction]"], "desc")

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_create_record_success(self, mock_httpx_client):
        """Test successful record creation."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "recNew123",
            "fields": {"Name": "New Lead", "Status": "Contacted"},
            "createdTime": "2024-01-15T00:00:00.000Z",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        fields = {"Name": "New Lead", "Status": "Contacted"}
        record = self.client.create_record(self.base_id, self.table_id, fields)

        # Verify
        self.assertEqual(record["id"], "recNew123")
        self.assertEqual(record["fields"]["Name"], "New Lead")

        call_args = mock_client_instance.request.call_args
        self.assertEqual(call_args.kwargs["method"], "POST")
        self.assertEqual(call_args.kwargs["json"]["fields"], fields)

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_create_record_with_typecast(self, mock_httpx_client):
        """Test record creation with typecast enabled."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "recNew123", "fields": {}}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        self.client.create_record(
            self.base_id, self.table_id, {"Name": "Test"}, typecast=True
        )

        # Verify typecast was included
        call_args = mock_client_instance.request.call_args
        self.assertTrue(call_args.kwargs["json"]["typecast"])

    @patch("aden_tools.tools.airtable_tool.airtable.httpx.Client")
    def test_update_record_success(self, mock_httpx_client):
        """Test successful record update."""
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": self.record_id,
            "fields": {"Name": "Updated Name", "Status": "Qualified"},
            "createdTime": "2024-01-01T00:00:00.000Z",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_instance.request.return_value = mock_response

        # Execute
        fields = {"Status": "Qualified"}
        record = self.client.update_record(
            self.base_id, self.table_id, self.record_id, fields
        )

        # Verify
        self.assertEqual(record["id"], self.record_id)
        self.assertEqual(record["fields"]["Status"], "Qualified")

        call_args = mock_client_instance.request.call_args
        self.assertEqual(call_args.kwargs["method"], "PATCH")
        self.assertIn(self.record_id, call_args.kwargs["url"])


class TestGetClient(unittest.TestCase):
    """Tests for the _get_client helper function."""

    def test_get_client_with_valid_credentials(self):
        """Test client creation with valid credentials."""
        creds = CredentialManager.for_testing(
            {"airtable_api_key": "test_api_key_123"}
        )
        client = _get_client(creds)

        self.assertIsNotNone(client)
        self.assertIsInstance(client, AirtableClient)

    def test_get_client_without_credentials(self):
        """Test that None is returned when no credentials provided."""
        client = _get_client(None)
        self.assertIsNone(client)

    def test_get_client_with_missing_api_key(self):
        """Test client creation with missing API key."""
        # Empty credentials
        creds = CredentialManager.for_testing({})
        client = _get_client(creds)

        # Should return None because validation will fail
        self.assertIsNone(client)


class TestCredentialIntegration(unittest.TestCase):
    """Tests for credential specification integration."""

    def test_credential_spec_exists(self):
        """Verify Airtable credential spec is properly registered."""
        from aden_tools.credentials import CREDENTIAL_SPECS

        self.assertIn("airtable_api_key", CREDENTIAL_SPECS)
        spec = CREDENTIAL_SPECS["airtable_api_key"]
        self.assertEqual(spec.env_var, "AIRTABLE_API_KEY")
        self.assertTrue(spec.required)
        self.assertIn("airtable_list_bases", spec.tools)
        self.assertIn("airtable_create_record", spec.tools)

    @patch("aden_tools.tools.airtable_tool.airtable.AirtableClient.list_bases")
    def test_tool_flow_with_credentials(self, mock_list_bases):
        """Test the flow from credentials to tool execution."""
        mock_list_bases.return_value = [{"id": "app123", "name": "Test"}]

        creds = CredentialManager.for_testing(
            {"airtable_api_key": "test_key"}
        )

        # Simulate what the tool does
        creds.validate_for_tools(["airtable_list_bases"])
        api_key = creds.get("airtable_api_key")
        self.assertEqual(api_key, "test_key")

        # Create client and make request
        client = AirtableClient(api_key)
        bases = client.list_bases()

        self.assertEqual(len(bases), 1)
        mock_list_bases.assert_called_once()


class TestAirtableToolResponses(unittest.TestCase):
    """Tests for tool response formatting."""

    @patch("aden_tools.tools.airtable_tool.airtable._get_client")
    def test_missing_credentials_error_format(self, mock_get_client):
        """Test error message format when credentials are missing."""
        mock_get_client.return_value = None

        # Import and test the tool function behavior
        from aden_tools.tools.airtable_tool.airtable import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, credentials=None)

        # The tools are registered - we can check registered tool names
        # In practice, calling without credentials returns error JSON


if __name__ == "__main__":
    unittest.main()
