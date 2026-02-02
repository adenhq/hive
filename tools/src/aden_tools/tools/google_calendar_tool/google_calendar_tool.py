"""Google Calendar Tool - Manage calendars and events via Google Calendar API v3."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class _GoogleCalendarClient:
    """Internal client wrapping Google Calendar API v3 calls."""

    def __init__(self, access_token: str):
        self._token = access_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: httpx.Response, expect_no_content: bool = False) -> dict:
        if expect_no_content and response.status_code == 204:
            return {"success": True}
        if response.status_code == 401:
            return {"error": "Invalid or expired Google Calendar access token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions. Check Google Calendar scopes."}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "Google Calendar rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Google Calendar API error (HTTP {response.status_code}): {detail}"}
        return response.json()

    def list_calendars(self) -> dict[str, Any]:
        response = httpx.get(
            f"{GOOGLE_CALENDAR_API_BASE}/users/me/calendarList",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_events(
        self,
        calendar_id: str,
        time_min: str | None,
        time_max: str | None,
        query: str | None,
        max_results: int,
        single_events: bool,
        order_by: str,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "maxResults": min(max_results, 250),
            "singleEvents": single_events,
            "orderBy": order_by,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        response = httpx.get(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{quote(calendar_id)}/events",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        response = httpx.get(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{quote(calendar_id)}/events/{quote(event_id)}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_event(self, calendar_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{quote(calendar_id)}/events",
            headers=self._headers,
            json=payload,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_event(self, calendar_id: str, event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.patch(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{quote(calendar_id)}/events/{quote(event_id)}",
            headers=self._headers,
            json=payload,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        response = httpx.delete(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{quote(calendar_id)}/events/{quote(event_id)}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response, expect_no_content=True)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Google Calendar tools with the MCP server."""

    def _get_token() -> str | None:
        if credentials is not None:
            token = credentials.get("google_calendar")
            if token is not None and not isinstance(token, str):
                raise TypeError(
                    "Expected string from credentials.get('google_calendar'), "
                    f"got {type(token).__name__}"
                )
            return token
        return os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")

    def _get_client() -> _GoogleCalendarClient | dict[str, str]:
        token = _get_token()
        if not token:
            return {
                "error": "Google Calendar credentials not configured",
                "help": (
                    "Set GOOGLE_CALENDAR_ACCESS_TOKEN environment variable "
                    "or configure via credential store"
                ),
            }
        return _GoogleCalendarClient(token)

    @mcp.tool()
    def google_calendar_list_calendars() -> dict:
        """List calendars available to the authenticated user."""
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_calendars()
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}

    @mcp.tool()
    def google_calendar_list_events(
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        query: str | None = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> dict:
        """
        List events for a calendar.

        Args:
            calendar_id: Calendar ID (default: primary)
            time_min: Lower bound (RFC3339 timestamp)
            time_max: Upper bound (RFC3339 timestamp)
            query: Free text search query
            max_results: Max events (1-250)
            single_events: Expand recurring events into instances
            order_by: "startTime" or "updated"
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        if max_results <= 0:
            return {"error": "max_results must be greater than zero"}
        if order_by not in {"startTime", "updated"}:
            return {"error": "order_by must be 'startTime' or 'updated'"}
        try:
            return client.list_events(
                calendar_id,
                time_min,
                time_max,
                query,
                max_results,
                single_events,
                order_by,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}

    @mcp.tool()
    def google_calendar_get_event(
        calendar_id: str,
        event_id: str,
    ) -> dict:
        """Get a single event by ID."""
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_event(calendar_id, event_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}

    @mcp.tool()
    def google_calendar_create_event(
        calendar_id: str,
        summary: str,
        start_time: str,
        end_time: str,
        time_zone: str = "UTC",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict:
        """Create a calendar event."""
        client = _get_client()
        if isinstance(client, dict):
            return client

        payload: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": time_zone},
            "end": {"dateTime": end_time, "timeZone": time_zone},
        }
        if description:
            payload["description"] = description
        if location:
            payload["location"] = location
        if attendees:
            payload["attendees"] = [{"email": email} for email in attendees]

        try:
            return client.create_event(calendar_id, payload)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}

    @mcp.tool()
    def google_calendar_update_event(
        calendar_id: str,
        event_id: str,
        summary: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        time_zone: str = "UTC",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict:
        """Update fields on a calendar event."""
        client = _get_client()
        if isinstance(client, dict):
            return client

        payload: dict[str, Any] = {}
        if summary is not None:
            payload["summary"] = summary
        if start_time is not None:
            payload["start"] = {"dateTime": start_time, "timeZone": time_zone}
        if end_time is not None:
            payload["end"] = {"dateTime": end_time, "timeZone": time_zone}
        if description is not None:
            payload["description"] = description
        if location is not None:
            payload["location"] = location
        if attendees is not None:
            payload["attendees"] = [{"email": email} for email in attendees]

        if not payload:
            return {"error": "No fields provided to update"}

        try:
            return client.update_event(calendar_id, event_id, payload)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}

    @mcp.tool()
    def google_calendar_delete_event(
        calendar_id: str,
        event_id: str,
    ) -> dict:
        """Delete a calendar event."""
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.delete_event(calendar_id, event_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as exc:
            return {"error": f"Network error: {exc}"}
