"""
n8n workflow automation tool for Aden Tools.

Allows agents to trigger workflows, check execution status, and list workflows.
Uses the n8n Public API (v1).
"""

import logging
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)


class N8NClient:
    """Client for interacting with the n8n Public API."""

    def __init__(self, api_key: str, host: str):
        """
        Initialize the n8n client.

        Args:
            api_key: n8n Public API key.
            host: n8n instance URL (e.g., https://n8n.example.com).
        """
        self.api_key = api_key
        # Ensure host doesn't have trailing slash
        self.host = host.rstrip("/")
        self.base_url = f"{self.host}/api/v1"
        self.headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Make a request to the n8n API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = f" - {e.response.text}"
            except Exception:
                pass
            logger.error(f"n8n API error: {e.response.status_code}{error_detail}")
            raise ValueError(f"n8n API error: {e.response.status_code}{error_detail}")
        except Exception as e:
            logger.error(f"n8n request failed: {str(e)}")
            raise RuntimeError(f"n8n request failed: {str(e)}")

    def list_workflows(self) -> list[dict[str, Any]]:
        """List available workflows."""
        data = self._request("GET", "workflows")
        return data.get("data", [])

    def trigger_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Trigger a workflow execution.
        Note: n8n Public API v1 usually requires a Webhook node for external triggers.
        This implementation attempts to use the workflow execution endpoint if available,
        or instructs users to use the webhook tool if preferred.
        """
        # Many n8n instances use a specific webhook URL for triggers.
        # But per requirements, we implement 'execute workflow by ID'.
        # Some versions support POST /workflows/:id/run
        return self._request("POST", f"workflows/{workflow_id}/run", json_data=payload)

    def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Retrieve the status and details of a specific execution."""
        return self._request("GET", f"executions/{execution_id}")


def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None) -> None:
    """Register n8n tools with the MCP server."""

    def get_client() -> N8NClient:
        if credentials:
            api_key = credentials.get("n8n")
            host = credentials.get("n8n_host")
        else:
            import os
            api_key = os.getenv("N8N_API_KEY")
            host = os.getenv("N8N_HOST")

        if not api_key or not host:
            raise ValueError("N8N_API_KEY and N8N_HOST must be set")
        
        return N8NClient(api_key, host)

    @mcp.tool()
    def n8n_list_workflows() -> str:
        """
        List all available workflows in the n8n instance.

        Returns:
            JSON string containing a list of workflows with their IDs and names.
        """
        try:
            client = get_client()
            workflows = client.list_workflows()
            # Return a simplified view for the agent
            result = [{"id": w["id"], "name": w["name"], "active": w.get("active")} for w in workflows]
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing workflows: {str(e)}"

    @mcp.tool()
    def n8n_trigger_workflow(workflow_id: str, payload: dict[str, Any]) -> str:
        """
        Trigger a specific n8n workflow by its ID.

        Args:
            workflow_id: The unique ID of the workflow to execute.
            payload: A dictionary containing the data to pass to the workflow.

        Returns:
            JSON string with execution details (e.g., execution ID, status).
        """
        try:
            client = get_client()
            result = client.trigger_workflow(workflow_id, payload)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error triggering workflow {workflow_id}: {str(e)}"

    @mcp.tool()
    def n8n_get_execution_status(execution_id: str) -> str:
        """
        Retrieve the current status of an n8n workflow execution.

        Args:
            execution_id: The unique ID of the execution to check.

        Returns:
            JSON string with the execution status (success, failed, running, etc.) and details.
        """
        try:
            client = get_client()
            result = client.get_execution_status(execution_id)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error fetching status for execution {execution_id}: {str(e)}"
