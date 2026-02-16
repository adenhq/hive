"""
ClickUp Tool - Task and workspace operations via ClickUp API v2.

Supports:
- Workspace, space, and list discovery
- Task listing and retrieval
- Task creation, update, and comments

API Reference: https://developer.clickup.com/reference/getauthorizedteams
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"
DEFAULT_TIMEOUT = 30.0


class _ClickUpClient:
    """Internal client wrapping ClickUp API calls."""

    def __init__(self, api_token: str):
        self._api_token = api_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _extract_error_message(self, response: httpx.Response) -> str:
        """Extract a readable API error message."""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return str(
                    payload.get("err")
                    or payload.get("error")
                    or payload.get("error_description")
                    or payload.get("message")
                    or response.text
                )
        except Exception:
            pass
        return response.text

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Map common HTTP failures to stable error messages."""
        if response.status_code in (200, 201):
            return response.json()
        if response.status_code == 400:
            return {
                "error": "Invalid request to ClickUp API",
                "details": self._extract_error_message(response),
            }
        if response.status_code == 401:
            return {"error": "Invalid or expired ClickUp API token"}
        if response.status_code == 403:
            return {
                "error": "Insufficient permissions. Check your ClickUp workspace access and token."
            }
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "ClickUp rate limit exceeded. Try again later."}

        detail = self._extract_error_message(response)
        return {"error": f"ClickUp API error (HTTP {response.status_code}): {detail}"}

    def list_workspaces(self) -> dict[str, Any]:
        response = httpx.get(
            f"{CLICKUP_API_BASE}/team",
            headers=self._headers,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def list_spaces(self, workspace_id: str, archived: bool = False) -> dict[str, Any]:
        response = httpx.get(
            f"{CLICKUP_API_BASE}/team/{workspace_id}/space",
            headers=self._headers,
            params={"archived": str(archived).lower()},
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def list_lists(self, space_id: str, archived: bool = False) -> dict[str, Any]:
        response = httpx.get(
            f"{CLICKUP_API_BASE}/space/{space_id}/list",
            headers=self._headers,
            params={"archived": str(archived).lower()},
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def list_tasks(
        self,
        list_id: str,
        *,
        include_closed: bool = False,
        archived: bool = False,
        page: int = 0,
        statuses: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "include_closed": str(include_closed).lower(),
            "archived": str(archived).lower(),
            "page": max(page, 0),
        }
        if statuses:
            params["statuses[]"] = statuses
        if assignees:
            params["assignees[]"] = assignees

        response = httpx.get(
            f"{CLICKUP_API_BASE}/list/{list_id}/task",
            headers=self._headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def get_task(self, task_id: str) -> dict[str, Any]:
        response = httpx.get(
            f"{CLICKUP_API_BASE}/task/{task_id}",
            headers=self._headers,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def create_task(
        self,
        *,
        list_id: str,
        name: str,
        description: str | None = None,
        status: str | None = None,
        assignees: list[str] | None = None,
        due_date: int | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if assignees is not None:
            body["assignees"] = assignees
        if due_date is not None:
            body["due_date"] = due_date
        if priority is not None:
            body["priority"] = priority

        response = httpx.post(
            f"{CLICKUP_API_BASE}/list/{list_id}/task",
            headers=self._headers,
            json=body,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def update_task(
        self,
        *,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignees: list[str] | None = None,
        due_date: int | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if assignees is not None:
            body["assignees"] = assignees
        if due_date is not None:
            body["due_date"] = due_date
        if priority is not None:
            body["priority"] = priority

        response = httpx.put(
            f"{CLICKUP_API_BASE}/task/{task_id}",
            headers=self._headers,
            json=body,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)

    def add_task_comment(
        self,
        *,
        task_id: str,
        comment_text: str,
        notify_all: bool = False,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{CLICKUP_API_BASE}/task/{task_id}/comment",
            headers=self._headers,
            json={
                "comment_text": comment_text,
                "notify_all": notify_all,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register ClickUp tools with the MCP server."""

    def _get_api_token() -> str | None:
        """Get ClickUp token from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("clickup")
            if token is not None and not isinstance(token, str):
                return None
            return token
        return os.getenv("CLICKUP_API_TOKEN")

    def _get_client() -> _ClickUpClient | dict[str, str]:
        """Create ClickUp client or return credential error."""
        token = _get_api_token()
        if not token:
            return {
                "error": "ClickUp API token not configured",
                "help": (
                    "Set CLICKUP_API_TOKEN environment variable "
                    "or configure via credential store"
                ),
            }
        return _ClickUpClient(token)

    def _execute(callable_fn: Callable[[_ClickUpClient], dict[str, Any]]) -> dict[str, Any]:
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return callable_fn(client)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def clickup_list_workspaces() -> dict:
        """List ClickUp workspaces accessible with the current token."""
        return _execute(lambda client: client.list_workspaces())

    @mcp.tool()
    def clickup_list_spaces(workspace_id: str, archived: bool = False) -> dict:
        """List spaces for a ClickUp workspace."""
        return _execute(lambda client: client.list_spaces(workspace_id, archived=archived))

    @mcp.tool()
    def clickup_list_lists(space_id: str, archived: bool = False) -> dict:
        """List lists for a ClickUp space."""
        return _execute(lambda client: client.list_lists(space_id, archived=archived))

    @mcp.tool()
    def clickup_list_tasks(
        list_id: str,
        include_closed: bool = False,
        archived: bool = False,
        page: int = 0,
        statuses: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        """List tasks in a ClickUp list with optional filters."""
        return _execute(
            lambda client: client.list_tasks(
                list_id,
                include_closed=include_closed,
                archived=archived,
                page=page,
                statuses=statuses,
                assignees=assignees,
            )
        )

    @mcp.tool()
    def clickup_get_task(task_id: str) -> dict:
        """Get a single ClickUp task by ID."""
        return _execute(lambda client: client.get_task(task_id))

    @mcp.tool()
    def clickup_create_task(
        list_id: str,
        name: str,
        description: str | None = None,
        status: str | None = None,
        assignees: list[str] | None = None,
        due_date: int | None = None,
        priority: int | None = None,
    ) -> dict:
        """Create a task in a ClickUp list."""
        if not name.strip():
            return {"error": "Task name is required"}

        return _execute(
            lambda client: client.create_task(
                list_id=list_id,
                name=name,
                description=description,
                status=status,
                assignees=assignees,
                due_date=due_date,
                priority=priority,
            )
        )

    @mcp.tool()
    def clickup_update_task(
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignees: list[str] | None = None,
        due_date: int | None = None,
        priority: int | None = None,
    ) -> dict:
        """Update one or more fields on a ClickUp task."""
        if all(
            field is None
            for field in (name, description, status, assignees, due_date, priority)
        ):
            return {"error": "At least one field must be provided for update"}

        return _execute(
            lambda client: client.update_task(
                task_id=task_id,
                name=name,
                description=description,
                status=status,
                assignees=assignees,
                due_date=due_date,
                priority=priority,
            )
        )

    @mcp.tool()
    def clickup_add_task_comment(
        task_id: str,
        comment_text: str,
        notify_all: bool = False,
    ) -> dict:
        """Add a comment to a ClickUp task."""
        if not comment_text.strip():
            return {"error": "Comment text is required"}

        return _execute(
            lambda client: client.add_task_comment(
                task_id=task_id,
                comment_text=comment_text,
                notify_all=notify_all,
            )
        )
