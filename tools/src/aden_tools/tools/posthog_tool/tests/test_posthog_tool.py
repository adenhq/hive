"""Tests for PostHog tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.posthog_tool.posthog_tool import (
    DEFAULT_POSTHOG_URL,
    _PostHogClient,
    register_tools,
)


class TestPostHogClient:
    def setup_method(self):
        self.client = _PostHogClient("test-key", "test-project")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"results": []}
        assert self.client._handle_response(response) == {"results": []}

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

    @patch("aden_tools.tools.posthog_tool.posthog_tool.httpx.post")
    def test_query(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [["event1", 10]]}
        mock_post.return_value = mock_response

        hogql = "SELECT event, count() FROM events GROUP BY event"
        result = self.client.query(hogql)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == f"{DEFAULT_POSTHOG_URL}/api/projects/test-project/query/"
        assert kwargs["json"]["query"]["query"] == hogql
        assert result["results"] == [["event1", 10]]

    @patch("aden_tools.tools.posthog_tool.posthog_tool.httpx.get")
    def test_list_events(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        self.client.list_events(limit=50, event_name="pageview")

        mock_get.assert_called_once_with(
            f"{DEFAULT_POSTHOG_URL}/api/projects/test-project/events/",
            headers=self.client._headers,
            params={"limit": 50, "event": "pageview"},
            timeout=30.0,
        )


class TestToolRegistration:
    def test_register_tools_registers_all(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 4

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)

        query_fn = next(fn for fn in registered_fns if fn.__name__ == "posthog_query")
        result = query_fn(hogql="SELECT 1")
        assert "error" in result
        assert "not configured" in result["error"]

    @patch("aden_tools.tools.posthog_tool.posthog_tool.httpx.post")
    def test_credentials_from_store(self, mock_post):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_store = MagicMock()
        cred_store.get.side_effect = lambda key: {
            "posthog": "store-key",
            "posthog_project_id": "store-project"
        }.get(key)
        
        register_tools(mcp, credentials=cred_store)
        query_fn = next(fn for fn in registered_fns if fn.__name__ == "posthog_query")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        query_fn(hogql="SELECT 1")

        call_headers = mock_post.call_args.kwargs["headers"]
        assert call_headers["Authorization"] == "Bearer store-key"
        assert "/api/projects/store-project/" in mock_post.call_args.args[0]
