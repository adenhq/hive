"""
PostHog Tool - Analytics-driven agent automation.

Supports:
- HogQL queries (SQL for analytics)
- Event retrieval
- Funnel metrics
- Cohort data
- Targeted triggers based on user behavior

API Reference: https://posthog.com/docs/api
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

DEFAULT_POSTHOG_URL = "https://app.posthog.com"


class _PostHogClient:
    """Internal client wrapping PostHog API calls."""

    def __init__(self, api_key: str, project_id: str, base_url: str | None = None):
        self._api_key = api_key
        self._project_id = project_id
        self._base_url = (base_url or DEFAULT_POSTHOG_URL).rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid or expired PostHog API key"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions for this PostHog project"}
        if response.status_code == 404:
            return {"error": "PostHog resource not found"}
        if response.status_code == 429:
            return {"error": "PostHog rate limit exceeded"}
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            return {"error": f"PostHog API error (HTTP {response.status_code}): {detail}"}
        
        return response.json()

    def query(self, hogql: str) -> dict[str, Any]:
        """Execute a HogQL query."""
        payload = {
            "query": {
                "kind": "HogQLQuery",
                "query": hogql
            }
        }
        response = httpx.post(
            f"{self._base_url}/api/projects/{self._project_id}/query/",
            headers=self._headers,
            json=payload,
            timeout=60.0,
        )
        return self._handle_response(response)

    def list_events(self, limit: int = 100, event_name: str | None = None) -> dict[str, Any]:
        """List raw events."""
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if event_name:
            params["event"] = event_name

        response = httpx.get(
            f"{self._base_url}/api/projects/{self._project_id}/events/",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_cohorts(self) -> dict[str, Any]:
        """List user cohorts."""
        response = httpx.get(
            f"{self._base_url}/api/projects/{self._project_id}/cohorts/",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_insight(self, insight_id: int | str) -> dict[str, Any]:
        """Retrieve insight metadata and data (useful for funnels)."""
        response = httpx.get(
            f"{self._base_url}/api/projects/{self._project_id}/insights/{insight_id}/",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register PostHog tools with the MCP server."""

    def _get_credentials() -> tuple[str | None, str | None, str | None]:
        """Get PostHog credentials from store or environment."""
        if credentials is not None:
            api_key = credentials.get("posthog")
            project_id = credentials.get("posthog_project_id")
            url = credentials.get("posthog_url")
            return api_key, project_id, url
        return os.getenv("POSTHOG_API_KEY"), os.getenv("POSTHOG_PROJECT_ID"), os.getenv("POSTHOG_URL")

    def _get_client() -> _PostHogClient | dict[str, str]:
        """Get initialized PostHog client or error."""
        api_key, project_id, url = _get_credentials()
        if not api_key:
            return {
                "error": "PostHog API key not configured",
                "help": "Set POSTHOG_API_KEY environment variable.",
            }
        if not project_id:
            return {
                "error": "PostHog Project ID not configured",
                "help": "Set POSTHOG_PROJECT_ID environment variable.",
            }
        return _PostHogClient(api_key, project_id, url)

    @mcp.tool()
    def posthog_query(hogql: str) -> dict[str, Any]:
        """
        Execute a HogQL (PostHog SQL) query for advanced analytics.
        
        Example: "SELECT event, count() FROM events WHERE timestamp > minus(now(), toIntervalDays(7)) GROUP BY event"

        Args:
            hogql: The HogQL query string.

        Returns:
            Dictionary containing columns and results.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.query(hogql)
        except httpx.TimeoutException:
            return {"error": "PostHog query timed out"}
        except Exception as e:
            return {"error": f"PostHog API error: {str(e)}"}

    @mcp.tool()
    def posthog_list_events(limit: int = 100, event_name: str | None = None) -> dict[str, Any]:
        """
        List recent raw events from PostHog.

        Args:
            limit: Maximum number of events to return (default 100, max 1000).
            event_name: Optional filter for a specific event type.

        Returns:
            List of events with their properties.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_events(limit=limit, event_name=event_name)
        except Exception as e:
            return {"error": f"PostHog API error: {str(e)}"}

    @mcp.tool()
    def posthog_get_funnel_metrics(insight_id: str) -> dict[str, Any]:
        """
        Retrieve conversion metrics for a saved funnel insight.

        Args:
            insight_id: The ID or short ID of the saved funnel insight.

        Returns:
            Funnel steps, completion rates, and drop-off data.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_insight(insight_id)
        except Exception as e:
            return {"error": f"PostHog API error: {str(e)}"}

    @mcp.tool()
    def posthog_list_cohorts() -> dict[str, Any]:
        """
        List all user cohorts defined in the project.

        Returns:
            List of cohorts with their definitions and sizes.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_cohorts()
        except Exception as e:
            return {"error": f"PostHog API error: {str(e)}"}
