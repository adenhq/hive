"""Dropbox Tool - Upload, download, and manage files via Dropbox API."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

DROPBOX_API_BASE = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT_BASE = "https://content.dropboxapi.com/2"


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Dropbox tools with the MCP server.

    Args:
        mcp: The FastMCP instance to register tools with.
        credentials: The credential store adapter to retrieve tokens from.
    """

    def _get_token() -> str | None:
        """Retrieve the Dropbox access token from credentials or environment."""
        if credentials is not None:
            return credentials.get("dropbox")
        return os.getenv("DROPBOX_ACCESS_TOKEN")

    @mcp.tool()
    async def dropbox_list_folder(path: str = "") -> dict[str, Any]:
        """List files and folders in a Dropbox directory.

        Args:
            path: Folder path (empty string for root). Must start with a forward slash / or be empty.

        Returns:
            Dict with file/folder entries or error.
        """
        token = _get_token()
        if not token:
            return {"error": "Dropbox access token not configured"}

        # Dropbox API expects empty string for root, but paths must start with /
        if path and not path.startswith("/"):
            path = f"/{path}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DROPBOX_API_BASE}/files/list_folder",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"path": path if path else ""},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Dropbox API error: {e.response.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool()
    async def dropbox_upload_file(
        file_content: str,
        dropbox_path: str,
        mode: str = "add",
        autorename: bool = True,
        mute: bool = False,
    ) -> dict[str, Any]:
        """Upload a file to Dropbox.

        Args:
            file_content: Content of the file to upload (text or base64).
            dropbox_path: Destination path in Dropbox (e.g., /reports/daily.txt).
            mode: Selects what to do if the file already exists (add, overwrite, update).
            autorename: If True, the file will be renamed if a conflict occurs.
            mute: If True, the user won't receive a notification.

        Returns:
            Metadata of the uploaded file or error.
        """
        token = _get_token()
        if not token:
            return {"error": "Dropbox access token not configured"}

        if not dropbox_path.startswith("/"):
            dropbox_path = f"/{dropbox_path}"

        arg = {
            "path": dropbox_path,
            "mode": mode,
            "autorename": autorename,
            "mute": mute,
            "strict_conflict": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DROPBOX_CONTENT_BASE}/files/upload",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Dropbox-API-Arg": json.dumps(arg),
                        "Content-Type": "application/octet-stream",
                    },
                    content=file_content.encode("utf-8") if isinstance(file_content, str) else file_content,
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Dropbox API error: {e.response.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool()
    async def dropbox_download_file(dropbox_path: str) -> dict[str, Any]:
        """Download a file from Dropbox.

        Args:
            dropbox_path: Path to the file in Dropbox.

        Returns:
            Dict containing file_content and metadata or error.
        """
        token = _get_token()
        if not token:
            return {"error": "Dropbox access token not configured"}

        if not dropbox_path.startswith("/"):
            dropbox_path = f"/{dropbox_path}"

        arg = {"path": dropbox_path}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DROPBOX_CONTENT_BASE}/files/download",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Dropbox-API-Arg": json.dumps(arg),
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                
                # Check if it's binary or text. For MVP, we'll try to return as text.
                content = response.text
                metadata = json.loads(response.headers.get("dropbox-api-result", "{}"))
                
                return {
                    "file_content": content,
                    "metadata": metadata
                }
        except httpx.HTTPStatusError as e:
            return {"error": f"Dropbox API error: {e.response.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool()
    async def dropbox_create_shared_link(path: str) -> dict[str, Any]:
        """Create a shared link for a file or folder.

        Args:
            path: Path to the file or folder.

        Returns:
            Metadata of the shared link or error.
        """
        token = _get_token()
        if not token:
            return {"error": "Dropbox access token not configured"}

        if not path.startswith("/"):
            path = f"/{path}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DROPBOX_API_BASE}/sharing/create_shared_link_with_settings",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"path": path},
                    timeout=30.0,
                )
                # If link already exists, response will be 409 Conflict with shared_link_already_exists
                if response.status_code == 409 and "shared_link_already_exists" in response.text:
                    # Retrieve existing links
                    existing_response = await client.post(
                        f"{DROPBOX_API_BASE}/sharing/list_shared_links",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json={"path": path, "direct_only": True},
                    )
                    existing_response.raise_for_status()
                    links = existing_response.json().get("links", [])
                    if links:
                        return links[0]
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Dropbox API error: {e.response.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
