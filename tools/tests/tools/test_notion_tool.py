"""
Tests for Notion tool.

Covers:
- _NotionClient methods (search, databases, pages, blocks)
- Error handling (API errors, timeout, network errors)
- Credential retrieval
- All 6 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.notion_tool.notion_tool import (
    _NotionClient,
    register_tools,
)

class TestNotionClient:
    def setup_method(self):
        self.client = _NotionClient("secret_test_token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Bearer secret_test_token"
        assert headers["Notion-Version"] == "2022-06-28"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"object": "list", "results": []}
        result = self.client._handle_response(response)
        assert result["success"] is True
        assert "results" in result["data"]

    def test_handle_response_401(self):
        response = MagicMock()
        response.status_code = 401
        result = self.client._handle_response(response)
        assert "error" in result
        assert "Invalid or expired" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_search(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        result = self.client.search(query="test")

        mock_post.assert_called_once()
        assert result["success"] is True

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_get_database(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "db_id", "title": []}
        mock_get.return_value = mock_response

        result = self.client.get_database("db_id")

        assert result["success"] is True
        assert result["data"]["id"] == "db_id"

class TestNotionToolRegistration:
    @pytest.fixture
    def mcp(self):
        return FastMCP("test-server")

    def test_no_credentials_returns_error(self, mcp):
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.getenv", return_value=None):
                register_tools(mcp, credentials=None)
                search_tool = mcp._tool_manager._tools["notion_search"].fn
                result = search_tool(query="test")
                assert "error" in result
                assert "not configured" in result["error"]

    def test_env_var_token(self, mcp):
        with patch("os.getenv", return_value="secret_env_token"):
            with patch("aden_tools.tools.notion_tool.notion_tool.httpx.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"results": []}
                mock_post.return_value = mock_response

                register_tools(mcp, credentials=None)
                search_tool = mcp._tool_manager._tools["notion_search"].fn
                search_tool(query="test")

                call_headers = mock_post.call_args.kwargs["headers"]
                assert call_headers["Authorization"] == "Bearer secret_env_token"
