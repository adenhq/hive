"""Tests for Outlook-specific tools (FastMCP)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.outlook_tool import register_tools

HTTPX_MODULE = "aden_tools.tools.outlook_tool.outlook_tool.httpx"


@pytest.fixture
def outlook_tools(mcp: FastMCP):
    """Register Outlook tools and return a dict of tool functions."""
    register_tools(mcp)
    tools = mcp._tool_manager._tools
    return {name: tools[name].fn for name in tools}


@pytest.fixture
def list_categories_fn(outlook_tools):
    return outlook_tools["outlook_list_categories"]


@pytest.fixture
def set_category_fn(outlook_tools):
    return outlook_tools["outlook_set_category"]


@pytest.fixture
def create_category_fn(outlook_tools):
    return outlook_tools["outlook_create_category"]


@pytest.fixture
def focused_inbox_fn(outlook_tools):
    return outlook_tools["outlook_get_focused_inbox"]


@pytest.fixture
def create_draft_fn(outlook_tools):
    return outlook_tools["outlook_create_draft"]


@pytest.fixture
def batch_get_fn(outlook_tools):
    return outlook_tools["outlook_batch_get_messages"]


def _mock_response(
    status_code: int = 200, json_data: dict | None = None, text: str = ""
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Credential handling (shared across all tools)
# ---------------------------------------------------------------------------


class TestCredentials:
    """All Outlook tools require OUTLOOK_OAUTH_TOKEN."""

    def test_list_categories_no_credentials(self, list_categories_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = list_categories_fn()
        assert "error" in result
        assert "Outlook credentials not configured" in result["error"]
        assert "help" in result

    def test_set_category_no_credentials(self, set_category_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = set_category_fn(message_id="abc", categories=["Red"])
        assert "error" in result
        assert "Outlook credentials not configured" in result["error"]

    def test_create_category_no_credentials(self, create_category_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = create_category_fn(display_name="Test")
        assert "error" in result

    def test_focused_inbox_no_credentials(self, focused_inbox_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = focused_inbox_fn()
        assert "error" in result

    def test_create_draft_no_credentials(self, create_draft_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = create_draft_fn(to="test@example.com", subject="Test", html="<p>Hi</p>")
        assert "error" in result

    def test_batch_get_no_credentials(self, batch_get_fn, monkeypatch):
        monkeypatch.delenv("OUTLOOK_OAUTH_TOKEN", raising=False)
        result = batch_get_fn(message_ids=["msg1"])
        assert "error" in result


# ---------------------------------------------------------------------------
# outlook_list_categories
# ---------------------------------------------------------------------------


HTTPX_REQUEST = f"{HTTPX_MODULE}.request"


class TestListCategories:
    def test_list_success(self, list_categories_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            200,
            {
                "value": [
                    {"displayName": "Red category", "color": "preset0"},
                    {"displayName": "Blue category", "color": "preset7"},
                ]
            },
        )
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = list_categories_fn()

        assert result["count"] == 2
        assert result["categories"][0]["displayName"] == "Red category"
        assert result["categories"][1]["color"] == "preset7"
        call_args = mock_req.call_args
        assert call_args[0][0] == "GET"
        assert "masterCategories" in call_args[0][1]

    def test_list_empty(self, list_categories_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(200, {"value": []})
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = list_categories_fn()

        assert result["categories"] == []
        assert result["count"] == 0

    def test_list_token_expired(self, list_categories_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "expired")
        mock_resp = _mock_response(401)
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = list_categories_fn()

        assert "error" in result
        assert "expired" in result["error"].lower() or "invalid" in result["error"].lower()

    def test_list_network_error(self, list_categories_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        with patch(HTTPX_REQUEST, side_effect=httpx.HTTPError("connection refused")):
            result = list_categories_fn()

        assert "error" in result
        assert "Request failed" in result["error"]


# ---------------------------------------------------------------------------
# outlook_set_category
# ---------------------------------------------------------------------------


class TestSetCategory:
    def test_set_success(self, set_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            200, {"id": "msg1", "categories": ["Red category", "Blue category"]}
        )
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = set_category_fn(
                message_id="msg1", categories=["Red category", "Blue category"]
            )

        assert result["success"] is True
        assert result["message_id"] == "msg1"
        assert result["categories"] == ["Red category", "Blue category"]
        call_args = mock_req.call_args
        assert call_args[0][0] == "PATCH"
        assert call_args[1]["json"]["categories"] == ["Red category", "Blue category"]

    def test_set_empty_categories(self, set_category_fn, monkeypatch):
        """Setting empty list removes all categories."""
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(200, {"id": "msg1", "categories": []})
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = set_category_fn(message_id="msg1", categories=[])

        assert result["success"] is True
        assert result["categories"] == []

    def test_set_empty_message_id(self, set_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = set_category_fn(message_id="", categories=["Red"])
        assert "error" in result
        assert "message_id" in result["error"]

    def test_set_not_found(self, set_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(404)
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = set_category_fn(message_id="nonexistent", categories=["Red"])

        assert "error" in result
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# outlook_create_category
# ---------------------------------------------------------------------------


class TestCreateCategory:
    def test_create_success(self, create_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(201, {"displayName": "My Category", "color": "preset3"})
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = create_category_fn(display_name="My Category", color="preset3")

        assert result["success"] is True
        assert result["displayName"] == "My Category"
        assert result["color"] == "preset3"
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["json"]["displayName"] == "My Category"
        assert call_args[1]["json"]["color"] == "preset3"

    def test_create_default_color(self, create_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(201, {"displayName": "Default Color", "color": "preset0"})
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = create_category_fn(display_name="Default Color")

        assert result["success"] is True
        call_args_json = mock_req.call_args[1]["json"]
        assert call_args_json["color"] == "preset0"

    def test_create_empty_name(self, create_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = create_category_fn(display_name="")
        assert "error" in result
        assert "display_name" in result["error"]

    def test_create_invalid_color(self, create_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = create_category_fn(display_name="Test", color="invalid_color")
        assert "error" in result
        assert "Invalid color" in result["error"]

    def test_create_api_error(self, create_category_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(409, text="Category already exists")
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = create_category_fn(display_name="Existing")

        assert "error" in result
        assert "409" in result["error"]


# ---------------------------------------------------------------------------
# outlook_get_focused_inbox
# ---------------------------------------------------------------------------


class TestGetFocusedInbox:
    def test_focused_success(self, focused_inbox_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            200,
            {
                "value": [
                    {
                        "id": "msg1",
                        "subject": "Important email",
                        "from": {"emailAddress": {"address": "sender@example.com"}},
                        "receivedDateTime": "2024-01-01T12:00:00Z",
                        "bodyPreview": "This is important...",
                        "isRead": False,
                        "inferenceClassification": "focused",
                    },
                ]
            },
        )
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = focused_inbox_fn(inbox_type="focused")

        assert result["count"] == 1
        assert result["inbox_type"] == "focused"
        msg = result["messages"][0]
        assert msg["id"] == "msg1"
        assert msg["subject"] == "Important email"
        assert msg["from"] == "sender@example.com"
        assert msg["classification"] == "focused"
        # Verify filter param
        params = mock_req.call_args[1]["params"]
        assert "focused" in params["$filter"]

    def test_other_inbox(self, focused_inbox_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(200, {"value": []})
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = focused_inbox_fn(inbox_type="other")

        assert result["inbox_type"] == "other"
        assert result["count"] == 0
        params = mock_req.call_args[1]["params"]
        assert "other" in params["$filter"]

    def test_max_results_clamped(self, focused_inbox_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(200, {"value": []})
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            focused_inbox_fn(max_results=999)

        params = mock_req.call_args[1]["params"]
        assert params["$top"] == 500

    def test_token_expired(self, focused_inbox_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "expired")
        mock_resp = _mock_response(401)
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = focused_inbox_fn()

        assert "error" in result


# ---------------------------------------------------------------------------
# outlook_create_draft
# ---------------------------------------------------------------------------


class TestCreateDraft:
    def test_create_success(self, create_draft_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            201,
            {
                "id": "draft_123",
                "subject": "My Draft",
                "isDraft": True,
            },
        )
        with patch(HTTPX_REQUEST, return_value=mock_resp) as mock_req:
            result = create_draft_fn(
                to="recipient@example.com",
                subject="My Draft",
                html="<p>Draft body</p>",
            )

        assert result["success"] is True
        assert result["draft_id"] == "draft_123"
        assert result["subject"] == "My Draft"
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        body = call_args[1]["json"]
        assert body["subject"] == "My Draft"
        assert body["body"]["contentType"] == "html"
        assert body["toRecipients"][0]["emailAddress"]["address"] == "recipient@example.com"

    def test_create_empty_to(self, create_draft_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = create_draft_fn(to="", subject="Test", html="<p>Hi</p>")
        assert "error" in result
        assert "Recipient" in result["error"]

    def test_create_empty_subject(self, create_draft_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = create_draft_fn(to="test@example.com", subject="", html="<p>Hi</p>")
        assert "error" in result
        assert "Subject" in result["error"]

    def test_create_empty_html(self, create_draft_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = create_draft_fn(to="test@example.com", subject="Test", html="")
        assert "error" in result
        assert "body" in result["error"].lower()

    def test_create_api_error(self, create_draft_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(403, text="Insufficient permissions")
        with patch(HTTPX_REQUEST, return_value=mock_resp):
            result = create_draft_fn(to="test@example.com", subject="Test", html="<p>Hi</p>")

        assert "error" in result
        assert "403" in result["error"]


# ---------------------------------------------------------------------------
# outlook_batch_get_messages
# ---------------------------------------------------------------------------

HTTPX_POST = f"{HTTPX_MODULE}.post"


class TestBatchGetMessages:
    def test_batch_success(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            200,
            {
                "responses": [
                    {
                        "id": "0",
                        "status": 200,
                        "body": {
                            "id": "msg1",
                            "subject": "First email",
                            "from": {"emailAddress": {"address": "alice@example.com"}},
                            "toRecipients": [{"emailAddress": {"address": "me@example.com"}}],
                            "ccRecipients": [],
                            "receivedDateTime": "2024-01-01T12:00:00Z",
                            "bodyPreview": "Hello...",
                            "isRead": True,
                            "body": {"contentType": "html", "content": "<p>Hello</p>"},
                        },
                    },
                    {
                        "id": "1",
                        "status": 200,
                        "body": {
                            "id": "msg2",
                            "subject": "Second email",
                            "from": {"emailAddress": {"address": "bob@example.com"}},
                            "toRecipients": [],
                            "ccRecipients": [],
                            "receivedDateTime": "2024-01-02T12:00:00Z",
                            "bodyPreview": "World...",
                            "isRead": False,
                            "body": {"contentType": "text", "content": "World"},
                        },
                    },
                ]
            },
        )
        with patch(HTTPX_POST, return_value=mock_resp) as mock_post:
            result = batch_get_fn(message_ids=["msg1", "msg2"])

        assert result["count"] == 2
        assert result["errors"] == []
        assert result["messages"][0]["subject"] == "First email"
        assert result["messages"][0]["body_html"] == "<p>Hello</p>"
        assert result["messages"][1]["body_text"] == "World"
        # Verify batch endpoint
        call_args = mock_post.call_args
        assert "$batch" in call_args[0][0]
        batch_body = call_args[1]["json"]
        assert len(batch_body["requests"]) == 2

    def test_batch_partial_errors(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        mock_resp = _mock_response(
            200,
            {
                "responses": [
                    {
                        "id": "0",
                        "status": 200,
                        "body": {
                            "id": "msg1",
                            "subject": "OK message",
                            "from": {"emailAddress": {"address": "a@example.com"}},
                            "toRecipients": [],
                            "ccRecipients": [],
                            "receivedDateTime": "2024-01-01T12:00:00Z",
                            "bodyPreview": "OK",
                            "isRead": True,
                            "body": {"contentType": "text", "content": "OK"},
                        },
                    },
                    {
                        "id": "1",
                        "status": 404,
                        "body": {"error": {"code": "ErrorItemNotFound", "message": "Not found"}},
                    },
                ]
            },
        )
        with patch(HTTPX_POST, return_value=mock_resp):
            result = batch_get_fn(message_ids=["msg1", "nonexistent"])

        assert result["count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["message_id"] == "nonexistent"

    def test_batch_empty_ids(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = batch_get_fn(message_ids=[])
        assert "error" in result
        assert "must not be empty" in result["error"]

    def test_batch_too_many_ids(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        result = batch_get_fn(message_ids=[f"msg{i}" for i in range(21)])
        assert "error" in result
        assert "Maximum 20" in result["error"]

    def test_batch_token_expired(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "expired")
        mock_resp = _mock_response(401)
        with patch(HTTPX_POST, return_value=mock_resp):
            result = batch_get_fn(message_ids=["msg1"])

        assert "error" in result
        assert "expired" in result["error"].lower() or "invalid" in result["error"].lower()

    def test_batch_network_error(self, batch_get_fn, monkeypatch):
        monkeypatch.setenv("OUTLOOK_OAUTH_TOKEN", "test_token")
        with patch(HTTPX_POST, side_effect=httpx.HTTPError("timeout")):
            result = batch_get_fn(message_ids=["msg1"])

        assert "error" in result
        assert "Batch request failed" in result["error"]
