"""
Jira Project Management Tool - Manage issues, projects, and workflows via Jira Cloud REST API v3.

Supports:
- API token authentication (JIRA_EMAIL + JIRA_API_TOKEN)
- OAuth2 tokens via the credential store

API Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


class _JiraClient:
    """Internal client wrapping Jira Cloud REST API v3 calls."""

    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize Jira client.

        Args:
            base_url: Jira instance URL (e.g., "https://your-domain.atlassian.net")
            email: Email address for authentication
            api_token: Jira API token
        """
        self.base_url = base_url.rstrip("/")
        self._email = email
        self._token = api_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid Jira credentials or expired API token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions. Check your Jira access rights."}
        if response.status_code == 404:
            return {"error": "Resource not found. Check issue key or project ID."}
        if response.status_code == 429:
            return {"error": "Jira rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                error_data = response.json()
                if "errorMessages" in error_data and error_data["errorMessages"]:
                    detail = "; ".join(error_data["errorMessages"])
                elif "errors" in error_data:
                    detail = str(error_data["errors"])
                else:
                    detail = error_data.get("message", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Jira API error (HTTP {response.status_code}): {detail}"}
        try:
            return response.json()
        except Exception:
            return {"success": True, "status_code": response.status_code}

    def search_issues(
        self,
        jql: str = "",
        fields: list[str] | None = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """
        Search issues using JQL (Jira Query Language).

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")
            fields: List of fields to return (e.g., ["summary", "status", "assignee"])
            max_results: Maximum number of results (1-100, default 50)

        Returns:
            Dict with search results or error
        """
        body: dict[str, Any] = {
            "jql": jql or "order by created DESC",
            "maxResults": min(max_results, 100),
        }
        if fields:
            body["fields"] = fields
        else:
            body["fields"] = ["summary", "status", "assignee", "priority", "created"]

        response = httpx.post(
            f"{self.base_url}/rest/api/3/search",
            auth=(self._email, self._token),
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_issue(
        self,
        issue_key: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get a single issue by key or ID.

        Args:
            issue_key: Issue key (e.g., "PROJ-123") or ID
            fields: List of fields to return

        Returns:
            Dict with issue data or error
        """
        params: dict[str, str] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = httpx.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}",
            auth=(self._email, self._token),
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str | None = None,
        additional_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new issue.

        Args:
            project_key: Project key (e.g., "PROJ")
            summary: Issue summary/title
            issue_type: Issue type (e.g., "Task", "Bug", "Story")
            description: Issue description
            additional_fields: Additional fields to set

        Returns:
            Dict with created issue data or error
        """
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            # Jira Cloud uses ADF (Atlassian Document Format)
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

        if additional_fields:
            fields.update(additional_fields)

        response = httpx.post(
            f"{self.base_url}/rest/api/3/issue",
            auth=(self._email, self._token),
            headers=self._headers,
            json={"fields": fields},
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            fields: Fields to update (e.g., {"summary": "New title"})

        Returns:
            Dict with success status or error
        """
        response = httpx.put(
            f"{self.base_url}/rest/api/3/issue/{issue_key}",
            auth=(self._email, self._token),
            headers=self._headers,
            json={"fields": fields},
            timeout=30.0,
        )
        return self._handle_response(response)

    def add_comment(
        self,
        issue_key: str,
        comment: str,
    ) -> dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            comment: Comment text

        Returns:
            Dict with created comment data or error
        """
        # Use ADF for comment body
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        response = httpx.post(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
            auth=(self._email, self._token),
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
    ) -> dict[str, Any]:
        """
        Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            transition_id: Transition ID (use get_transitions to find available IDs)

        Returns:
            Dict with success status or error
        """
        response = httpx.post(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
            auth=(self._email, self._token),
            headers=self._headers,
            json={"transition": {"id": transition_id}},
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_transitions(self, issue_key: str) -> dict[str, Any]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Dict with available transitions or error
        """
        response = httpx.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
            auth=(self._email, self._token),
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_projects(self) -> dict[str, Any]:
        """
        List all accessible projects.

        Returns:
            Dict with project list or error
        """
        response = httpx.get(
            f"{self.base_url}/rest/api/3/project",
            auth=(self._email, self._token),
            headers=self._headers,
            timeout=30.0,
        )
        result = self._handle_response(response)
        # API returns array directly, wrap it in dict for consistency
        if isinstance(result, list):
            return {"projects": result}
        return result


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Jira tools with the MCP server."""

    def _get_credentials() -> tuple[str, str, str] | None:
        """Get Jira credentials from credential manager or environment."""
        if credentials is not None:
            jira_creds = credentials.get("jira")
            if jira_creds is not None:
                if not isinstance(jira_creds, dict):
                    raise TypeError(
                        f"Expected dict from credentials.get('jira'), got {type(jira_creds).__name__}"
                    )
                base_url = jira_creds.get("base_url")
                email = jira_creds.get("email")
                api_token = jira_creds.get("api_token")
                if base_url and email and api_token:
                    return (base_url, email, api_token)

        # Fall back to environment variables
        base_url = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")

        if base_url and email and api_token:
            return (base_url, email, api_token)

        return None

    def _get_client() -> _JiraClient | dict[str, str]:
        """Get a Jira client, or return an error dict if no credentials."""
        creds = _get_credentials()
        if not creds:
            return {
                "error": "Jira credentials not configured",
                "help": (
                    "Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables "
                    "or configure via credential store"
                ),
            }
        base_url, email, api_token = creds
        return _JiraClient(base_url, email, api_token)

    # --- Issue Operations ---

    @mcp.tool()
    def jira_search_issues(
        jql: str = "",
        fields: list[str] | None = None,
        max_results: int = 50,
    ) -> dict:
        """
        Search Jira issues using JQL (Jira Query Language).

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")
                Leave empty to get recent issues
            fields: List of fields to return
                (e.g., ["summary", "status", "assignee", "priority"])
            max_results: Maximum number of results (1-100, default 50)

        Returns:
            Dict with search results or error

        Examples:
            - jql="project = MYPROJ"
            - jql="assignee = currentUser() AND status != Done"
            - jql="created >= -7d"
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.search_issues(jql, fields, max_results)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_get_issue(
        issue_key: str,
        fields: list[str] | None = None,
    ) -> dict:
        """
        Get a Jira issue by key or ID.

        Args:
            issue_key: Issue key (e.g., "PROJ-123") or ID
            fields: List of fields to return
                (e.g., ["summary", "status", "assignee", "description"])

        Returns:
            Dict with issue data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_issue(issue_key, fields)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_create_issue(
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str | None = None,
        additional_fields: dict[str, Any] | None = None,
    ) -> dict:
        """
        Create a new Jira issue.

        Args:
            project_key: Project key (e.g., "PROJ")
            summary: Issue summary/title
            issue_type: Issue type (e.g., "Task", "Bug", "Story"), default "Task"
            description: Issue description (optional)
            additional_fields: Additional fields to set (e.g., {"priority": {"name": "High"}})

        Returns:
            Dict with created issue data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_issue(
                project_key, summary, issue_type, description, additional_fields
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_update_issue(
        issue_key: str,
        fields: dict[str, Any],
    ) -> dict:
        """
        Update an existing Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            fields: Fields to update (e.g., {"summary": "New title"})

        Returns:
            Dict with success status or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.update_issue(issue_key, fields)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_add_comment(
        issue_key: str,
        comment: str,
    ) -> dict:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            comment: Comment text

        Returns:
            Dict with created comment data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.add_comment(issue_key, comment)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_transition_issue(
        issue_key: str,
        transition_id: str,
    ) -> dict:
        """
        Transition a Jira issue to a new status.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            transition_id: Transition ID (use jira_get_transitions to find available IDs)

        Returns:
            Dict with success status or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.transition_issue(issue_key, transition_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_get_transitions(issue_key: str) -> dict:
        """
        Get available transitions for a Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Dict with available transitions or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_transitions(issue_key)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def jira_list_projects() -> dict:
        """
        List all accessible Jira projects.

        Returns:
            Dict with project list or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_projects()
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
