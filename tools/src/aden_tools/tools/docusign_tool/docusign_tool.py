"""
DocuSign eSignature Tool - Manage envelopes and documents via DocuSign API v2.1.

Supports:
- OAuth 2.0 Access Tokens (DOCUSIGN_ACCESS_TOKEN)
- Credential management via aden_tools.credentials

API Reference: https://developers.docusign.com/docs/esign-rest-api/reference/
"""

from __future__ import annotations

import base64
import datetime
import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


class _DocuSignClient:
    """Internal client wrapping DocuSign eSignature API v2.1 calls."""

    def __init__(self, access_token: str, account_id: str, base_uri: str):
        self._token = access_token
        self._account_id = account_id
        self._base_uri = base_uri.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def _api_base(self) -> str:
        return f"{self._base_uri}/restapi/v2.1/accounts/{self._account_id}"

    def _handle_response(self, response: httpx.Response) -> dict[str, Any] | bytes:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid or expired DocuSign access token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions"}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code >= 400:
            try:
                detail = response.json()
                message = detail.get("message", detail.get("errorCode", response.text))
            except Exception:
                message = response.text
            return {"error": f"DocuSign API error (HTTP {response.status_code}): {message}"}

        # Handle binary content (PDFs)
        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" in content_type:
             return response.content

        return response.json()

    def create_envelope(
        self,
        template_id: str,
        signer_email: str,
        signer_name: str,
        role_name: str = "Signer",
        email_subject: str | None = None,
        email_body: str | None = None,
        tab_values: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create and send an envelope from a template."""
        # Construct the envelope definition
        # Basic template role assignment
        template_role = {
            "email": signer_email,
            "name": signer_name,
            "roleName": role_name,
        }

        if tab_values:
            # Populate tabs (form fields)
            tabs = {}
            # Assuming text tabs for simplicity, can be expanded
            text_tabs = []
            for label, value in tab_values.items():
                text_tabs.append({"tabLabel": label, "value": value})
            if text_tabs:
                 tabs["textTabs"] = text_tabs
            template_role["tabs"] = tabs

        payload = {
            "templateId": template_id,
            "templateRoles": [template_role],
            "status": "sent",  # Immediately send the envelope
        }

        if email_subject:
            payload["emailSubject"] = email_subject
        if email_body:
            payload["emailBlurb"] = email_body

        response = httpx.post(
            f"{self._api_base}/envelopes",
            headers=self._headers,
            json=payload,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_envelope(self, envelope_id: str) -> dict[str, Any]:
        """Get envelope status and details."""
        response = httpx.get(
            f"{self._api_base}/envelopes/{envelope_id}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_envelopes(
        self,
        limit: int = 25,
        status: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        search_text: str | None = None,
    ) -> dict[str, Any]:
        """List envelopes matching criteria."""
        params = {"count": str(limit)}
        if from_date:
            params["from_date"] = from_date
        else:
            # DocuSign requires from_date if no specific folder/status filter implies it
            # Defaulting to 30 days ago
            last_30_days = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
            params["from_date"] = last_30_days.isoformat()

        if status:
            params["status"] = status
        if to_date:
            params["to_date"] = to_date
        if search_text:
            params["search_text"] = search_text

        response = httpx.get(
            f"{self._api_base}/envelopes",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_document(self, envelope_id: str, document_id: str = "combined") -> dict[str, Any]:
        """Download a document from an envelope."""
        response = httpx.get(
            f"{self._api_base}/envelopes/{envelope_id}/documents/{document_id}",
            headers=self._headers,
            timeout=60.0,  # PDFs can be large
        )
        result = self._handle_response(response)

        if isinstance(result, bytes):
            # Return base64 encoded string for safe transport
            return {
                "envelopeId": envelope_id,
                "documentId": document_id,
                "content_base64": base64.b64encode(result).decode("utf-8"),
                "mime_type": "application/pdf"
            }
        return result


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register DocuSign tools with the MCP server."""

    def _get_config() -> dict[str, str] | None:
        """Get DocuSign credentials from manager or environment."""
        token = None
        account_id = None
        base_uri = None

        if credentials is not None:
            # Try getting from credential store
            creds = credentials.get("docusign")
            if creds:
                token = creds.get("access_token")
                # Credential store might flatten these or keep them separate
                # Adjusted based on typical adapter behavior
                account_id = creds.get("additional", {}).get("DOCUSIGN_ACCOUNT_ID") or os.getenv("DOCUSIGN_ACCOUNT_ID")
                base_uri = creds.get("additional", {}).get("DOCUSIGN_BASE_URI") or os.getenv("DOCUSIGN_BASE_URI")

                if token and account_id and base_uri:
                     return {
                        "access_token": token,
                        "account_id": account_id,
                        "base_uri": base_uri,
                    }

        # Fallback to environment variables
        token = os.getenv("DOCUSIGN_ACCESS_TOKEN")
        account_id = os.getenv("DOCUSIGN_ACCOUNT_ID")
        base_uri = os.getenv("DOCUSIGN_BASE_URI")

        if token and account_id and base_uri:
            return {
                "access_token": token,
                "account_id": account_id,
                "base_uri": base_uri,
            }
        return None

    def _get_client() -> _DocuSignClient | dict[str, str]:
        """Get a DocuSign client or error."""
        config = _get_config()
        if not config:
            return {
                "error": "DocuSign credentials not configured",
                "help": (
                    "Set DOCUSIGN_ACCESS_TOKEN, DOCUSIGN_ACCOUNT_ID, and DOCUSIGN_BASE_URI "
                    "environment variables."
                ),
            }
        return _DocuSignClient(**config)

    @mcp.tool()
    def docusign_create_envelope(
        template_id: str,
        signer_email: str,
        signer_name: str,
        role_name: str = "Signer",
        email_subject: str | None = None,
        email_body: str | None = None,
        tab_values: dict[str, str] | None = None,
    ) -> dict:
        """
        Send a document for signature using a template.

        Args:
            template_id: The ID of the DocuSign template to use
            signer_email: Email address of the signer
            signer_name: Full name of the signer
            role_name: (Optional) Role name in the template (default: "Signer")
            email_subject: (Optional) Subject line for the email
            email_body: (Optional) Body text for the email
            tab_values: (Optional) Dictionary of label->value pairs to pre-fill fields

        Returns:
            Dict with envelope details (envelopeId, status, etc.) or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_envelope(
                template_id,
                signer_email,
                signer_name,
                role_name,
                email_subject,
                email_body,
                tab_values,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def docusign_get_envelope_status(
        envelope_id: str,
    ) -> dict:
        """
        Check the status of an envelope.

        Args:
            envelope_id: The ID of the envelope to check

        Returns:
            Dict with status, created/sent dates, and recipient info
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_envelope(envelope_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def docusign_list_envelopes(
        limit: int = 25,
        status: str | None = None,
        from_date: str | None = None,
        search_text: str | None = None,
    ) -> dict:
        """
        List envelopes with optional filtering.

        Args:
            limit: Maximum number of results (default 25)
            status: Filter by status (e.g., "sent", "completed", "declined")
            from_date: Start date for query (ISO 8601 format, e.g., 2023-01-01T00:00:00Z)
            search_text: Filter by text in envelope subject or sender/recipient names

        Returns:
            Dict with list of envelopes
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_envelopes(
                limit=limit,
                status=status,
                from_date=from_date,
                search_text=search_text,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def docusign_download_document(
        envelope_id: str,
        document_id: str = "combined",
    ) -> dict:
        """
        Download a signed document from an envelope.

        Args:
            envelope_id: The ID of the envelope
            document_id: (Optional) ID of specific document, or "combined" for all (default: combined)

        Returns:
            Dict containing base64 encoded PDF content
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_document(envelope_id, document_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
