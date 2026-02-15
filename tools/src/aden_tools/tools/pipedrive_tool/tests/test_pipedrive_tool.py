"""
Tests for Pipedrive CRM tool.

Covers:
- _PipedriveClient methods
- Error handling
- All 7 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.pipedrive_tool.pipedrive_tool import (
    PIPEDRIVE_API_BASE,
    _PipedriveClient,
    register_tools,
)


class TestPipedriveClient:
    def setup_method(self):
        self.client = _PipedriveClient("test-token")

    def test_params(self):
        params = self.client._params
        assert params["api_token"] == "test-token"

    def test_headers(self):
        headers = self.client._headers
        assert headers["Content-Type"] == "application/json"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"success": True, "data": []}
        assert self.client._handle_response(response) == {"success": True, "data": []}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid or expired"),
            (403, "Insufficient permissions"),
            (404, "not found"),
            (429, "rate limit"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring in result["error"]

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.post")
    def test_create_person(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "data": {"id": 1, "name": "John Doe"}}
        mock_post.return_value = mock_response

        result = self.client.create_person(name="John Doe", email="john@example.com")

        mock_post.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/persons",
            headers=self.client._headers,
            params=self.client._params,
            json={"name": "John Doe", "email": "john@example.com"},
            timeout=30.0,
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.get")
    def test_search_persons(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"items": []}}
        mock_get.return_value = mock_response

        result = self.client.search_persons(term="test@example.com", exact_match=True)

        mock_get.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/persons/search",
            headers=self.client._headers,
            params={**self.client._params, "term": "test@example.com", "fields": "email", "exact_match": "true"},
            timeout=30.0,
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.get")
    def test_get_person(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"id": 1}}
        mock_get.return_value = mock_response

        result = self.client.get_person(1)

        mock_get.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/persons/1",
            headers=self.client._headers,
            params=self.client._params,
            timeout=30.0,
        )
        assert result["data"]["id"] == 1

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.post")
    def test_create_deal(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "data": {"id": 123}}
        mock_post.return_value = mock_response

        result = self.client.create_deal(title="Big Deal", person_id=1, value=1000.0, currency="USD")

        mock_post.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/deals",
            headers=self.client._headers,
            params=self.client._params,
            json={"title": "Big Deal", "person_id": 1, "value": 1000.0, "currency": "USD"},
            timeout=30.0,
        )
        assert result["data"]["id"] == 123

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.put")
    def test_update_deal(self, mock_put):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_put.return_value = mock_response

        result = self.client.update_deal(123, stage_id=2)

        mock_put.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/deals/123",
            headers=self.client._headers,
            params=self.client._params,
            json={"stage_id": 2},
            timeout=30.0,
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.get")
    def test_list_deals(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": []}
        mock_get.return_value = mock_response

        result = self.client.list_deals(status="open", limit=5)

        mock_get.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/deals",
            headers=self.client._headers,
            params={**self.client._params, "status": "open", "limit": "5"},
            timeout=30.0,
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool.httpx.post")
    def test_add_note(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = self.client.add_note(content="Test note", deal_id=123)

        mock_post.assert_called_once_with(
            f"{PIPEDRIVE_API_BASE}/notes",
            headers=self.client._headers,
            params=self.client._params,
            json={"content": "Test note", "deal_id": 123},
            timeout=30.0,
        )
        assert result["success"] is True


class TestPipedriveMCPTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.registered_tools = {}

        def tool_decorator(name=None, **kwargs):
            def decorator(f):
                tool_name = name or f.__name__
                self.registered_tools[tool_name] = f
                return f

            return decorator

        self.mcp.tool.side_effect = tool_decorator

        self.mock_creds = MagicMock()
        self.mock_creds.get.return_value = "test-token"
        register_tools(self.mcp, credentials=self.mock_creds)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.create_person")
    def test_create_person_tool(self, mock_create):
        mock_create.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_create_person"]
        result = tool(name="John Doe", email="john@example.com")
        assert result == {"success": True}
        mock_create.assert_called_once_with(name="John Doe", email="john@example.com", phone=None)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.search_persons")
    def test_search_person_tool(self, mock_search):
        mock_search.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_search_person"]
        result = tool(email="john@example.com")
        assert result == {"success": True}
        mock_search.assert_called_once_with(term="john@example.com", fields="email", exact_match=True)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.get_person")
    def test_get_person_details_tool(self, mock_get):
        mock_get.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_get_person_details"]
        result = tool(person_id=1)
        assert result == {"success": True}
        mock_get.assert_called_once_with(1)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.create_deal")
    def test_create_deal_tool(self, mock_create):
        mock_create.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_create_deal"]
        result = tool(title="Big Deal", person_id=1, value=100.0, currency="USD")
        assert result == {"success": True}
        mock_create.assert_called_once_with(title="Big Deal", person_id=1, value=100.0, currency="USD")

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.update_deal")
    def test_update_deal_stage_tool(self, mock_update):
        mock_update.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_update_deal_stage"]
        result = tool(deal_id=123, stage_id=2)
        assert result == {"success": True}
        mock_update.assert_called_once_with(123, stage_id=2)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.list_deals")
    def test_list_deals_tool(self, mock_list):
        mock_list.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_list_deals"]
        result = tool(status="open", limit=5)
        assert result == {"success": True}
        mock_list.assert_called_once_with(status="open", limit=5)

    @patch("aden_tools.tools.pipedrive_tool.pipedrive_tool._PipedriveClient.add_note")
    def test_add_note_to_deal_tool(self, mock_add):
        mock_add.return_value = {"success": True}
        tool = self.registered_tools["pipedrive_add_note_to_deal"]
        result = tool(deal_id=123, content="Note")
        assert result == {"success": True}
        mock_add.assert_called_once_with(content="Note", deal_id=123)

    def test_no_creds_error(self):
        # Reset registered_tools
        self.registered_tools = {}
        register_tools(self.mcp, credentials=None)
        # Clear env just in case
        with patch.dict("os.environ", {}, clear=True):
            create_person_tool = self.registered_tools["pipedrive_create_person"]
            result = create_person_tool(name="Test")
            assert "error" in result
            assert "not configured" in result["error"]
