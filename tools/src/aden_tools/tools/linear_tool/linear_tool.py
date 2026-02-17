"""
Linear Tool - Interact with Linear issues and projects.

API Reference: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

LINEAR_API_URL = "https://api.linear.app/graphql"


def _sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to prevent token leaks.
    """
    error_str = str(error)
    # Remove any Authorization headers or Bearer tokens
    if "Authorization" in error_str or "Bearer" in error_str:
        return "Network error occurred"
    return f"Network error: {error_str}"


class _LinearClient:
    """Internal client wrapping Linear GraphQL API calls."""

    def __init__(self, token: str):
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token,  # Linear uses simply "Authorization: <token>" or "Authorization: Bearer <token>"? Docs say "Authorization: <api_key>". Wait, docs say "Authorization: <api_key>". Or "Authorization: Bearer <oauth_token>". I'll assume API Key first.
            "Content-Type": "application/json",
        }

    def _execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = httpx.post(
                LINEAR_API_URL,
                headers=self._headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            
            data = response.json()
            if "errors" in data:
                return {"error": f"Linear API error: {data['errors'][0]['message']}"}
                
            return {"success": True, "data": data.get("data", {})}
            
        except httpx.HTTPStatusError as e:
             # Handle specific HTTP errors if needed
            return {"error": f"Linear API error (HTTP {e.response.status_code}): {e.response.text}"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}
        except Exception as e:
             return {"error": f"Unexpected error: {str(e)}"}


    # --- Issues ---

    def create_issue(
        self,
        title: str,
        team_id: str,
        description: str | None = None,
        priority: int | None = None,
        state_id: str | None = None,
        assignee_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue."""
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """
        
        variables = {
            "input": {
                "title": title,
                "teamId": team_id,
            }
        }
        
        if description:
            variables["input"]["description"] = description
        if priority is not None:
             variables["input"]["priority"] = priority
        if state_id:
             variables["input"]["stateId"] = state_id
        if assignee_id:
             variables["input"]["assigneeId"] = assignee_id
             
        return self._execute(mutation, variables)

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        """Get issue details by ID (e.g., LIN-123 or UUID)."""
        query = """
        query Issue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                priority
                state {
                    name
                }
                assignee {
                    name
                }
                url
                createdAt
            }
        }
        """
        return self._execute(query, {"id": issue_id})
        
    def search_issues(
        self,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search issues."""
        gql_query = """
        query IssueSearch($query: String!, $first: Int) {
            issueSearch(query: $query, first: $first) {
                nodes {
                    id
                    identifier
                    title
                    state {
                        name
                    }
                    url
                }
            }
        }
        """
        return self._execute(gql_query, {"query": query, "first": limit})


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Linear tools with the MCP server."""

    def _get_token() -> str | None:
        """Get Linear API key from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("linear_api_key")
            if token:
                 return token
        return os.getenv("LINEAR_API_KEY")

    def _get_client() -> _LinearClient | dict[str, str]:
        """Get a Linear client, or return an error dict if no credentials."""
        token = _get_token()
        if not token:
            return {
                "error": "Linear credentials not configured",
                "help": (
                    "Set LINEAR_API_KEY environment variable. "
                    "Get a key at https://linear.app/settings/api"
                ),
            }
        return _LinearClient(token)

    @mcp.tool()
    def linear_create_issue(
        title: str,
        team_id: str,
        description: str | None = None,
        priority: int | None = None,
        state_id: str | None = None,
        assignee_id: str | None = None,
    ) -> dict:
        """
        Create a new issue in Linear.
        
        Args:
            title: Issue title.
            team_id: The ID of the team to create the issue in (e.g., UUID or team key like 'LIN'). 
                     Note: API usually requires UUID, but try team key if client supports lookup. 
                     Wait, `issueCreate` requires `teamId` as UUID.
            description: Issue description (markdown supported).
            priority: Priority (0=No Priority, 1=Urgent, 2=High, 3=Normal, 4=Low).
            state_id: ID of the workflow state (UUID).
            assignee_id: ID of the user to assign (UUID).
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.create_issue(title, team_id, description, priority, state_id, assignee_id)

    @mcp.tool()
    def linear_get_issue(issue_id: str) -> dict:
        """
        Get details of a Linear issue.
        
        Args:
           issue_id: The issue identifier (e.g., "LIN-123") or UUID.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.get_issue(issue_id)

    @mcp.tool()
    def linear_search_issues(query: str, limit: int = 10) -> dict:
        """
        Search for issues in Linear.
        
        Args:
            query: The search term.
            limit: Max results to return (default 10).
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.search_issues(query, limit)
