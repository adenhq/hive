"""
Outlook Tool - Outlook-specific email operations via Microsoft Graph.

Provides features unique to Outlook/Microsoft 365 that have no Gmail equivalent:
- Categories (color-coded tags)
- Focused Inbox
- Draft creation
- Batch message fetching via $batch endpoint

Requires: OUTLOOK_OAUTH_TOKEN (via Aden OAuth2)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

GRAPH_BASE = "https://graph.microsoft.com/v1.0/me"


def _sanitize_path_param(param: str, param_name: str = "parameter") -> str:
    """Sanitize URL path parameters to prevent path traversal."""
    if "/" in param or ".." in param:
        raise ValueError(f"Invalid {param_name}: cannot contain '/' or '..'")
    return param


# Outlook category preset colors (Graph API enum values)
OUTLOOK_CATEGORY_COLORS = [
    "preset0",
    "preset1",
    "preset2",
    "preset3",
    "preset4",
    "preset5",
    "preset6",
    "preset7",
    "preset8",
    "preset9",
    "preset10",
    "preset11",
    "preset12",
    "preset13",
    "preset14",
    "preset15",
    "preset16",
    "preset17",
    "preset18",
    "preset19",
    "preset20",
    "preset21",
    "preset22",
    "preset23",
    "preset24",
]


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Outlook-specific tools with the MCP server."""

    def _get_token() -> str | None:
        """Get Outlook access token from credentials or environment."""
        if credentials is not None:
            return credentials.get("outlook")
        return os.getenv("OUTLOOK_OAUTH_TOKEN")

    def _outlook_request(
        method: str, path: str, access_token: str, **kwargs: object
    ) -> httpx.Response:
        """Make an authenticated Microsoft Graph API request."""
        return httpx.request(
            method,
            f"{GRAPH_BASE}/{path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
            **kwargs,
        )

    def _handle_error(response: httpx.Response) -> dict | None:
        """Return error dict for non-success responses, or None if OK."""
        if response.status_code in (200, 201, 204):
            return None
        if response.status_code == 401:
            return {
                "error": "Outlook token expired or invalid",
                "help": "Re-authorize via hive.adenhq.com",
            }
        if response.status_code == 404:
            return {"error": "Resource not found"}
        return {
            "error": f"Outlook API error (HTTP {response.status_code}): {response.text}",
        }

    def _require_token() -> dict | str:
        """Get token or return error dict."""
        token = _get_token()
        if not token:
            return {
                "error": "Outlook credentials not configured",
                "help": "Connect Outlook via hive.adenhq.com",
            }
        return token

    # ------------------------------------------------------------------ #
    # Categories
    # ------------------------------------------------------------------ #

    @mcp.tool()
    def outlook_list_categories() -> dict:
        """
        List all Outlook categories (color-coded tags).

        Categories in Outlook are color-tagged strings that can be applied to
        messages, events, and contacts. Unlike Gmail labels, categories have
        associated preset colors.

        Returns:
            Dict with "categories" list (each with displayName and color),
            or error dict with "error" and optional "help" keys.
        """
        token = _require_token()
        if isinstance(token, dict):
            return token

        try:
            response = _outlook_request("GET", "outlook/masterCategories", token)
        except httpx.HTTPError as e:
            return {"error": f"Request failed: {e}"}

        error = _handle_error(response)
        if error:
            return error

        data = response.json()
        categories = [
            {
                "displayName": cat.get("displayName", ""),
                "color": cat.get("color", ""),
            }
            for cat in data.get("value", [])
        ]
        return {"categories": categories, "count": len(categories)}

    @mcp.tool()
    def outlook_set_category(
        message_id: str,
        categories: list[str],
    ) -> dict:
        """
        Set categories on an Outlook message.

        Replaces all existing categories on the message with the provided list.
        Pass an empty list to remove all categories.

        Args:
            message_id: The Outlook message ID.
            categories: List of category display names to set on the message.
                        Pass [] to remove all categories.

        Returns:
            Dict with "success" and updated "categories",
            or error dict with "error" and optional "help" keys.
        """
        if not message_id:
            return {"error": "message_id is required"}
        try:
            message_id = _sanitize_path_param(message_id, "message_id")
        except ValueError as e:
            return {"error": str(e)}

        token = _require_token()
        if isinstance(token, dict):
            return token

        try:
            response = _outlook_request(
                "PATCH",
                f"messages/{message_id}",
                token,
                json={"categories": categories},
            )
        except httpx.HTTPError as e:
            return {"error": f"Request failed: {e}"}

        error = _handle_error(response)
        if error:
            return error

        data = response.json()
        return {
            "success": True,
            "message_id": message_id,
            "categories": data.get("categories", []),
        }

    @mcp.tool()
    def outlook_create_category(
        display_name: str,
        color: str = "preset0",
    ) -> dict:
        """
        Create a custom Outlook category with a color.

        Outlook categories use preset color values (preset0 through preset24).
        Common color mappings: preset0=Red, preset1=Orange, preset2=Brown,
        preset3=Yellow, preset4=Green, preset5=Teal, preset6=Olive,
        preset7=Blue, preset8=Purple, preset9=Cranberry.

        Args:
            display_name: Name for the new category.
            color: Preset color value (preset0 through preset24). Default: "preset0" (Red).

        Returns:
            Dict with "success", "displayName", and "color",
            or error dict with "error" and optional "help" keys.
        """
        if not display_name or not display_name.strip():
            return {"error": "display_name is required"}
        if color not in OUTLOOK_CATEGORY_COLORS:
            return {
                "error": f"Invalid color: {color}. Must be preset0 through preset24.",
            }

        token = _require_token()
        if isinstance(token, dict):
            return token

        try:
            response = _outlook_request(
                "POST",
                "outlook/masterCategories",
                token,
                json={"displayName": display_name, "color": color},
            )
        except httpx.HTTPError as e:
            return {"error": f"Request failed: {e}"}

        error = _handle_error(response)
        if error:
            return error

        data = response.json()
        return {
            "success": True,
            "displayName": data.get("displayName", display_name),
            "color": data.get("color", color),
        }

    # ------------------------------------------------------------------ #
    # Focused Inbox
    # ------------------------------------------------------------------ #

    @mcp.tool()
    def outlook_get_focused_inbox(
        inbox_type: Literal["focused", "other"] = "focused",
        max_results: int = 25,
    ) -> dict:
        """
        List messages from the Focused or Other inbox.

        Outlook's Focused Inbox automatically sorts important messages into
        "Focused" and less important ones into "Other". This has no Gmail equivalent.

        Args:
            inbox_type: Which inbox to list - "focused" or "other" (default: "focused").
            max_results: Maximum number of messages to return (default: 25, max: 500).

        Returns:
            Dict with "messages" list, "count", and "inbox_type",
            or error dict with "error" and optional "help" keys.
        """
        token = _require_token()
        if isinstance(token, dict):
            return token

        max_results = max(1, min(max_results, 500))

        # inferenceClassification: "focused" or "other"
        filter_value = inbox_type.lower()
        params: dict = {
            "$filter": f"inferenceClassification eq '{filter_value}'",
            "$top": max_results,
            "$orderby": "receivedDateTime desc",
            "$select": (
                "id,subject,from,receivedDateTime,bodyPreview,isRead,inferenceClassification"
            ),
        }

        try:
            response = _outlook_request("GET", "mailFolders/inbox/messages", token, params=params)
        except httpx.HTTPError as e:
            return {"error": f"Request failed: {e}"}

        error = _handle_error(response)
        if error:
            return error

        data = response.json()
        messages = [
            {
                "id": msg.get("id", ""),
                "subject": msg.get("subject", ""),
                "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                "date": msg.get("receivedDateTime", ""),
                "snippet": msg.get("bodyPreview", ""),
                "is_read": msg.get("isRead", False),
                "classification": msg.get("inferenceClassification", ""),
            }
            for msg in data.get("value", [])
        ]
        return {
            "messages": messages,
            "count": len(messages),
            "inbox_type": inbox_type,
        }

    # ------------------------------------------------------------------ #
    # Drafts
    # ------------------------------------------------------------------ #

    @mcp.tool()
    def outlook_create_draft(
        to: str,
        subject: str,
        html: str,
    ) -> dict:
        """
        Create a draft email in Outlook.

        Creates a message in the Drafts folder that can be reviewed and sent
        manually from Outlook. Mirrors gmail_create_draft for Outlook.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html: Email body as HTML string.

        Returns:
            Dict with "success", "draft_id", and "subject",
            or error dict with "error" and optional "help" keys.
        """
        if not to or not to.strip():
            return {"error": "Recipient email (to) is required"}
        if not subject or not subject.strip():
            return {"error": "Subject is required"}
        if not html:
            return {"error": "Email body (html) is required"}

        token = _require_token()
        if isinstance(token, dict):
            return token

        message_payload = {
            "subject": subject,
            "body": {"contentType": "html", "content": html},
            "toRecipients": [{"emailAddress": {"address": to}}],
        }

        try:
            # POST /me/messages creates a draft (unsent message)
            response = _outlook_request("POST", "messages", token, json=message_payload)
        except httpx.HTTPError as e:
            return {"error": f"Request failed: {e}"}

        error = _handle_error(response)
        if error:
            return error

        data = response.json()
        return {
            "success": True,
            "draft_id": data.get("id", ""),
            "subject": data.get("subject", subject),
        }

    # ------------------------------------------------------------------ #
    # Batch operations
    # ------------------------------------------------------------------ #

    @mcp.tool()
    def outlook_batch_get_messages(
        message_ids: list[str],
    ) -> dict:
        """
        Fetch multiple Outlook messages in a single batch request.

        Uses the Microsoft Graph $batch endpoint to retrieve multiple messages
        efficiently. Mirrors gmail_batch_get_messages for Outlook.

        Args:
            message_ids: List of Outlook message IDs to fetch (max 20 per batch).

        Returns:
            Dict with "messages" list, "count", and "errors" list,
            or error dict with "error" and optional "help" keys.
        """
        if not message_ids:
            return {"error": "message_ids list is required and must not be empty"}
        if len(message_ids) > 20:
            return {"error": "Maximum 20 message IDs per batch request"}

        for mid in message_ids:
            try:
                _sanitize_path_param(mid, "message_id")
            except ValueError as e:
                return {"error": str(e)}

        token = _require_token()
        if isinstance(token, dict):
            return token

        # Build batch request payload
        requests_payload = [
            {
                "id": str(i),
                "method": "GET",
                "url": (
                    f"/me/messages/{mid}?$select=id,subject,from,"
                    "receivedDateTime,bodyPreview,isRead,"
                    "toRecipients,ccRecipients,body"
                ),
            }
            for i, mid in enumerate(message_ids)
        ]

        try:
            response = httpx.post(
                "https://graph.microsoft.com/v1.0/$batch",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"requests": requests_payload},
                timeout=60.0,
            )
        except httpx.HTTPError as e:
            return {"error": f"Batch request failed: {e}"}

        if response.status_code == 401:
            return {
                "error": "Outlook token expired or invalid",
                "help": "Re-authorize via hive.adenhq.com",
            }
        if response.status_code != 200:
            return {
                "error": f"Outlook batch API error (HTTP {response.status_code}): {response.text}",
            }

        batch_data = response.json()
        messages = []
        errors = []

        for resp in batch_data.get("responses", []):
            resp_id = resp.get("id", "")
            status = resp.get("status", 0)
            body = resp.get("body", {})

            if status == 200:
                to_addrs = [
                    r.get("emailAddress", {}).get("address", "")
                    for r in body.get("toRecipients", [])
                ]
                cc_addrs = [
                    r.get("emailAddress", {}).get("address", "")
                    for r in body.get("ccRecipients", [])
                ]
                msg_body = body.get("body", {})
                messages.append(
                    {
                        "id": body.get("id", ""),
                        "subject": body.get("subject", ""),
                        "from": body.get("from", {}).get("emailAddress", {}).get("address", ""),
                        "to": ", ".join(to_addrs),
                        "cc": ", ".join(cc_addrs),
                        "date": body.get("receivedDateTime", ""),
                        "snippet": body.get("bodyPreview", ""),
                        "is_read": body.get("isRead", False),
                        "body_text": msg_body.get("content", "")
                        if msg_body.get("contentType") == "text"
                        else "",
                        "body_html": msg_body.get("content", "")
                        if msg_body.get("contentType") == "html"
                        else "",
                    }
                )
            else:
                idx = int(resp_id) if resp_id.isdigit() else resp_id
                mid = (
                    message_ids[idx] if isinstance(idx, int) and idx < len(message_ids) else resp_id
                )
                error_body = body.get("error", {})
                errors.append(
                    {
                        "message_id": mid,
                        "error": error_body.get("message", f"HTTP {status}"),
                    }
                )

        return {"messages": messages, "count": len(messages), "errors": errors}
