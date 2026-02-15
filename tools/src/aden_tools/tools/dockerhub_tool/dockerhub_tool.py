"""Docker Hub tools for Hive agents.

Allows listing repositories, tags, and retrieving metadata.
"""

from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialStoreAdapter

DOCKERHUB_API_BASE = "https://hub.docker.com/v2"


def register_tools(mcp: FastMCP, credentials: Optional[CredentialStoreAdapter] = None):
    """Register Docker Hub tools with the provided MCP instance."""

    async def _get_headers() -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = None
        if credentials:
            token = credentials.get("docker_hub")
        else:
            import os
            token = os.environ.get("DOCKER_HUB_TOKEN")

        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @mcp.tool()
    async def dockerhub_list_repositories(username: str) -> dict[str, Any]:
        """
        List repositories for a specific Docker Hub user or organization.

        Args:
            username: Docker Hub username or organization name.
        """
        headers = await _get_headers()
        async with httpx.AsyncClient() as client:
            try:
                # Use v2 API to list repositories
                response = await client.get(
                    f"{DOCKERHUB_API_BASE}/repositories/{username}/",
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
            except Exception as e:
                return {"error": str(e)}

    @mcp.tool()
    async def dockerhub_list_tags(namespace: str, repository: str) -> dict[str, Any]:
        """
        List image tags for a specific Docker Hub repository.

        Args:
            namespace: Docker Hub username or organization.
            repository: Repository name.
        """
        headers = await _get_headers()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{DOCKERHUB_API_BASE}/repositories/{namespace}/{repository}/tags/",
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
            except Exception as e:
                return {"error": str(e)}

    @mcp.tool()
    async def dockerhub_get_tag_metadata(
        namespace: str, repository: str, tag: str
    ) -> dict[str, Any]:
        """
        Get metadata for a specific Docker Hub image tag.

        Args:
            namespace: Docker Hub username or organization.
            repository: Repository name.
            tag: Image tag (e.g., 'latest').
        """
        headers = await _get_headers()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{DOCKERHUB_API_BASE}/repositories/{namespace}/{repository}/tags/{tag}/",
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
            except Exception as e:
                return {"error": str(e)}
