"""
Unit tests for the Generic API Connector tool.

Tests cover:
- Tool registration with FastMCP.
- Input validation (URL length, unsupported methods).
- Auth header/param generation for all supported auth methods.
- Credential resolution (credential store and env var fallback).
- Retry logic on transient HTTP errors (429, 5xx).
- Timeout and network error handling.
- The convenience wrappers (generic_api_get, generic_api_post).
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.generic_api_tool.generic_api_tool import (
    _resolve_auth_headers,
    _resolve_auth_params,
    register_tools,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp():
    """Create a FastMCP instance with generic API tools registered."""
    server = FastMCP("test")
    register_tools(server)
    return server


@pytest.fixture
def mcp_with_creds():
    """Create a FastMCP instance with mock credentials."""
    server = FastMCP("test")
    mock_creds = MagicMock()
    mock_creds.get.return_value = "test-token-123"
    register_tools(server, credentials=mock_creds)
    return server


def _get_tool_fn(mcp_instance: FastMCP, name: str):
    """Extract a registered tool function by name."""
    return mcp_instance._tool_manager._tools[name].fn


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------


class TestRegistration:
    """Verify tool registration with FastMCP."""

    def test_registers_all_three_tools(self, mcp):
        """All three tool functions should be registered."""
        tool_names = set(mcp._tool_manager._tools.keys())
        assert "generic_api_get" in tool_names
        assert "generic_api_post" in tool_names
        assert "generic_api_request" in tool_names


# ---------------------------------------------------------------------------
# Auth Helper Tests
# ---------------------------------------------------------------------------


class TestAuthHelpers:
    """Test auth header and param generation helpers."""

    def test_bearer_auth(self):
        """Bearer token should set Authorization header."""
        headers = _resolve_auth_headers("bearer", "my-token")
        assert headers == {"Authorization": "Bearer my-token"}

    def test_api_key_auth(self):
        """API key should set Authorization header."""
        headers = _resolve_auth_headers("api_key", "my-key")
        assert headers == {"Authorization": "ApiKey my-key"}

    def test_basic_auth(self):
        """Basic auth should base64-encode user:password."""
        headers = _resolve_auth_headers("basic", "user:pass")
        expected = base64.b64encode(b"user:pass").decode()
        assert headers == {"Authorization": f"Basic {expected}"}

    def test_custom_header_auth(self):
        """Custom header should use the provided header name."""
        headers = _resolve_auth_headers(
            "custom_header", "tok", custom_header_name="X-Service-Key"
        )
        assert headers == {"X-Service-Key": "tok"}

    def test_custom_header_default_name(self):
        """Custom header without explicit name defaults to X-API-Key."""
        headers = _resolve_auth_headers("custom_header", "tok")
        assert headers == {"X-API-Key": "tok"}

    def test_query_param_auth(self):
        """Query param auth should return params dict."""
        params = _resolve_auth_params("query_param", "tok")
        assert params == {"api_key": "tok"}

    def test_query_param_custom_name(self):
        """Query param auth should use the custom param name."""
        params = _resolve_auth_params(
            "query_param", "tok", query_param_name="access_key"
        )
        assert params == {"access_key": "tok"}

    def test_bearer_no_query_params(self):
        """Non-query auth methods should return empty params."""
        params = _resolve_auth_params("bearer", "tok")
        assert params == {}


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Test input validation logic."""

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    def test_empty_url_rejected(self, mcp):
        """Empty URL should return an error."""
        fn = _get_tool_fn(mcp, "generic_api_get")
        result = fn(url="")
        assert "error" in result

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    def test_long_url_rejected(self, mcp):
        """URL exceeding 2048 chars should be rejected."""
        fn = _get_tool_fn(mcp, "generic_api_get")
        result = fn(url="https://example.com/" + "a" * 2050)
        assert "error" in result

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    def test_unsupported_method_rejected(self, mcp):
        """Unsupported HTTP method should return an error."""
        fn = _get_tool_fn(mcp, "generic_api_request")
        result = fn(url="https://example.com", method="TRACE")
        assert "error" in result
        assert "allowed" in result

    def test_missing_token_returns_error(self, mcp):
        """Missing credential should return a helpful error."""
        with patch.dict("os.environ", {}, clear=True):
            fn = _get_tool_fn(mcp, "generic_api_get")
            result = fn(url="https://example.com/api")
            assert "error" in result
            assert "GENERIC_API_TOKEN" in result["error"]

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    def test_no_auth_skips_token_check(self, mcp):
        """auth_method='none' should not require a token."""
        fn = _get_tool_fn(mcp, "generic_api_get")
        with patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True}
            mock_resp.headers = {}
            mock_req.return_value = mock_resp

            result = fn(url="https://open.api.com/data", auth_method="none")
            assert result["status_code"] == 200


# ---------------------------------------------------------------------------
# Credential Store Tests
# ---------------------------------------------------------------------------


class TestCredentialStore:
    """Test credential resolution through the store adapter."""

    def test_uses_credential_store(self, mcp_with_creds):
        """Should resolve token from credential store adapter."""
        fn = _get_tool_fn(mcp_with_creds, "generic_api_get")
        with patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": "ok"}
            mock_resp.headers = {}
            mock_req.return_value = mock_resp

            result = fn(url="https://example.com/api/v1/items")
            assert result["status_code"] == 200
            # Verify the Bearer header was set with the mock token.
            call_kwargs = mock_req.call_args
            assert "Bearer test-token-123" in call_kwargs.kwargs["headers"]["Authorization"]


# ---------------------------------------------------------------------------
# HTTP Request Tests (mocked)
# ---------------------------------------------------------------------------


class TestHttpRequests:
    """Test actual HTTP request execution with mocked httpx."""

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_get_success(self, mock_req, mcp):
        """Successful GET should return structured response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [1, 2, 3]}
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_req.return_value = mock_resp

        fn = _get_tool_fn(mcp, "generic_api_get")
        result = fn(url="https://api.example.com/items")

        assert result["status_code"] == 200
        assert result["body"] == {"items": [1, 2, 3]}
        assert result["method"] == "GET"

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_post_sends_body(self, mock_req, mcp):
        """POST should send JSON body."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "new-42"}
        mock_resp.headers = {}
        mock_req.return_value = mock_resp

        fn = _get_tool_fn(mcp, "generic_api_post")
        result = fn(
            url="https://api.example.com/items",
            body={"name": "Widget"},
        )

        assert result["status_code"] == 201
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["json"] == {"name": "Widget"}

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_put_method(self, mock_req, mcp):
        """generic_api_request with PUT should set correct method."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"updated": True}
        mock_resp.headers = {}
        mock_req.return_value = mock_resp

        fn = _get_tool_fn(mcp, "generic_api_request")
        result = fn(
            url="https://api.example.com/items/42",
            method="PUT",
            body={"status": "active"},
        )

        assert result["status_code"] == 200
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["method"] == "PUT"

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_delete_method(self, mock_req, mcp):
        """generic_api_request with DELETE should work."""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.json.side_effect = Exception("no body")
        mock_resp.text = ""
        mock_resp.headers = {}
        mock_req.return_value = mock_resp

        fn = _get_tool_fn(mcp, "generic_api_request")
        result = fn(url="https://api.example.com/items/42", method="DELETE")

        assert result["status_code"] == 204

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_timeout_error(self, mock_req, mcp):
        """Timeout should return error after retries."""
        mock_req.side_effect = httpx.TimeoutException("timed out")

        fn = _get_tool_fn(mcp, "generic_api_get")
        with patch("aden_tools.tools.generic_api_tool.generic_api_tool.time.sleep"):
            result = fn(url="https://slow.api.com/data", timeout=1.0)

        assert "error" in result
        assert "timed out" in result["error"].lower()

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_network_error(self, mock_req, mcp):
        """Network error should return error after retries."""
        mock_req.side_effect = httpx.RequestError("DNS resolution failed")

        fn = _get_tool_fn(mcp, "generic_api_get")
        with patch("aden_tools.tools.generic_api_tool.generic_api_tool.time.sleep"):
            result = fn(url="https://unreachable.api.com/data")

        assert "error" in result
        assert "Network error" in result["error"]


# ---------------------------------------------------------------------------
# Retry Tests
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Test retry behaviour on transient failures."""

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.time.sleep")
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_retries_on_429(self, mock_req, mock_sleep, mcp):
        """Should retry on 429 and eventually succeed."""
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"ok": True}
        success.headers = {}

        mock_req.side_effect = [rate_limited, rate_limited, success]

        fn = _get_tool_fn(mcp, "generic_api_get")
        result = fn(url="https://api.example.com/data")

        assert result["status_code"] == 200
        assert mock_req.call_count == 3
        assert mock_sleep.call_count == 2

    @patch.dict("os.environ", {"GENERIC_API_TOKEN": "test-key"})
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.time.sleep")
    @patch("aden_tools.tools.generic_api_tool.generic_api_tool.httpx.request")
    def test_retries_on_500(self, mock_req, mock_sleep, mcp):
        """Should retry on 500 server errors."""
        error = MagicMock()
        error.status_code = 500

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"recovered": True}
        success.headers = {}

        mock_req.side_effect = [error, success]

        fn = _get_tool_fn(mcp, "generic_api_get")
        result = fn(url="https://api.example.com/data")

        assert result["status_code"] == 200
        assert mock_req.call_count == 2
