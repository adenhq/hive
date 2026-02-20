"""
Tests for Stripe tool.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.stripe_tool.stripe_tool import (
    _StripeClient,
    register_tools,
)

class TestStripeClient:
    def setup_method(self):
        self.client = _StripeClient("sk_test_token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Bearer sk_test_token"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "cus_123", "object": "customer"}
        result = self.client._handle_response(response)
        assert result["success"] is True
        assert result["data"]["id"] == "cus_123"

    @patch("aden_tools.tools.stripe_tool.stripe_tool.httpx.get")
    def test_list_customers(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = self.client.list_customers(limit=5)

        mock_get.assert_called_once()
        assert result["success"] is True

class TestStripeToolRegistration:
    @pytest.fixture
    def mcp(self):
        return FastMCP("test-server")

    def test_env_var_token(self, mcp):
        with patch("os.getenv", return_value="sk_test_env"):
            with patch("aden_tools.tools.stripe_tool.stripe_tool.httpx.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": []}
                mock_get.return_value = mock_response

                register_tools(mcp, credentials=None)
                list_tool = mcp._tool_manager._tools["stripe_list_customers"].fn
                list_tool()

                call_headers = mock_get.call_args.kwargs["headers"]
                assert call_headers["Authorization"] == "Bearer sk_test_env"
