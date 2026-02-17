"""
Tests for Linear tool.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.linear_tool.linear_tool import (
    _LinearClient,
    register_tools,
)


class TestLinearClient:
    def setup_method(self):
        self.client = _LinearClient("lin_test_token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "lin_test_token"
        assert headers["Content-Type"] == "application/json"

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_execute_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"foo": "bar"}}
        mock_post.return_value = mock_response

        result = self.client._execute("query { foo }")

        assert result["success"] is True
        assert result["data"]["foo"] == "bar"

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_execute_graphql_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Cannot find that issue"}]
        }
        mock_post.return_value = mock_response

        result = self.client._execute("query { foo }")

        assert "error" in result
        assert "Cannot find that issue" in result["error"]

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_execute_network_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("Network error")

        result = self.client._execute("query { foo }")

        assert "error" in result
        assert "Network error" in result["error"]


class TestLinearTools:
    @pytest.fixture
    def mcp(self):
        return FastMCP("test-server")

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_create_issue(self, mock_post, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "uuid-1",
                        "identifier": "LIN-1",
                        "title": "Bug",
                        "url": "https://linear.app/issue/LIN-1"
                    }
                }
            }
        }
        mock_post.return_value = mock_response

        with patch("os.getenv", return_value="lin_test"):
            register_tools(mcp, credentials=None)
            create_issue = mcp._tool_manager._tools["linear_create_issue"].fn

            result = create_issue(
                title="Bug",
                team_id="team-uuid",
                description="Desc",
                priority=1
            )

            assert result["success"] is True
            assert result["data"]["issueCreate"]["issue"]["identifier"] == "LIN-1"
            
            # Verify variables
            call_kwargs = mock_post.call_args.kwargs
            variables = call_kwargs["json"]["variables"]
            assert variables["input"]["title"] == "Bug"
            assert variables["input"]["teamId"] == "team-uuid"
            assert variables["input"]["description"] == "Desc"
            assert variables["input"]["priority"] == 1

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_get_issue(self, mock_post, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issue": {
                    "id": "uuid-1",
                    "identifier": "LIN-123",
                    "title": "Bug Report"
                }
            }
        }
        mock_post.return_value = mock_response

        with patch("os.getenv", return_value="lin_test"):
            register_tools(mcp, credentials=None)
            get_issue = mcp._tool_manager._tools["linear_get_issue"].fn

            result = get_issue(issue_id="LIN-123")

            assert result["success"] is True
            assert result["data"]["issue"]["title"] == "Bug Report"

    @patch("aden_tools.tools.linear_tool.linear_tool.httpx.post")
    def test_search_issues(self, mock_post, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issueSearch": {
                    "nodes": [
                        {"identifier": "LIN-1", "title": "First Issue"},
                        {"identifier": "LIN-2", "title": "Second Issue"}
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        with patch("os.getenv", return_value="lin_test"):
            register_tools(mcp, credentials=None)
            search_issues = mcp._tool_manager._tools["linear_search_issues"].fn

            result = search_issues(query="bug")

            assert result["success"] is True
            nodes = result["data"]["issueSearch"]["nodes"]
            assert len(nodes) == 2
