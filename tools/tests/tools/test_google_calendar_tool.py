"""
Tests for Google Calendar tool and client behavior.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.google_calendar_tool.google_calendar_tool import (
    GOOGLE_CALENDAR_API_BASE,
    _GoogleCalendarClient,
    register_tools,
)


class TestGoogleCalendarClient:
    def setup_method(self):
        self.client = _GoogleCalendarClient("test-token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"items": []}
        assert self.client._handle_response(response) == {"items": []}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid"),
            (403, "Insufficient"),
            (404, "not found"),
            (429, "rate limit"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring.lower() in result["error"].lower()

    @patch("aden_tools.tools.google_calendar_tool.google_calendar_tool.httpx.get")
    def test_list_calendars(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        result = self.client.list_calendars()

        mock_get.assert_called_once_with(
            f"{GOOGLE_CALENDAR_API_BASE}/users/me/calendarList",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert "items" in result

    @patch("aden_tools.tools.google_calendar_tool.google_calendar_tool.httpx.get")
    def test_list_events(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        self.client.list_events(
            calendar_id="primary",
            time_min=None,
            time_max=None,
            query=None,
            max_results=10,
            single_events=True,
            order_by="startTime",
        )

        mock_get.assert_called_once()


class TestToolRegistration:
    def _get_tool_fn(self, mcp_mock, tool_name):
        for call in mcp_mock.tool.return_value.call_args_list:
            fn = call[0][0]
            if fn.__name__ == tool_name:
                return fn
        raise ValueError(f"Tool '{tool_name}' not found in registered tools")

    def test_register_tools_registers_all_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 6

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp, credentials=None)

        list_calendars = self._get_tool_fn(mcp, "google_calendar_list_calendars")

        with patch.dict("os.environ", {}, clear=True):
            result = list_calendars()

        assert "error" in result

    @patch("aden_tools.tools.google_calendar_tool.google_calendar_tool.httpx.get")
    def test_list_events_timeout(self, mock_get):
        mock_get.side_effect = httpx.TimeoutException("timeout")
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn

        with patch.dict("os.environ", {"GOOGLE_CALENDAR_ACCESS_TOKEN": "token"}):
            register_tools(mcp, credentials=None)
            list_events = self._get_tool_fn(mcp, "google_calendar_list_events")

        result = list_events()
        assert "error" in result
