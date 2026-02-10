"""
Generic API Connector Tool — call any REST API without building custom integrations.

Supports multiple auth methods (Bearer, API Key, Basic Auth, custom headers,
query-parameter auth) and exposes three tool functions:

- ``generic_api_get``  — convenience wrapper for GET requests.
- ``generic_api_post`` — convenience wrapper for POST requests.
- ``generic_api_request`` — full HTTP verb support (GET/POST/PUT/PATCH/DELETE).

All functions perform input validation, configurable retries with exponential
backoff, and return structured JSON responses.
"""

from __future__ import annotations

import base64
import os
import time
from typing import TYPE_CHECKING, Any, Literal

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 3
_MAX_URL_LENGTH = 2048


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_auth_headers(
    auth_method: str,
    api_token: str,
    custom_header_name: str | None = None,
) -> dict[str, str]:
    """Build auth headers based on the chosen auth method.

    Args:
        auth_method: One of ``bearer``, ``api_key``, ``basic``, ``custom_header``,
            ``query_param``.
        api_token: The credential value.
        custom_header_name: Header key when ``auth_method`` is ``custom_header``.

    Returns:
        A dict of HTTP headers to merge into the request.
    """
    method = auth_method.lower()
    if method == "bearer":
        return {"Authorization": f"Bearer {api_token}"}
    if method == "api_key":
        return {"Authorization": f"ApiKey {api_token}"}
    if method == "basic":
        # Expect ``api_token`` formatted as ``username:password``.
        encoded = base64.b64encode(api_token.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    if method == "custom_header":
        header = custom_header_name or "X-API-Key"
        return {header: api_token}
    # ``query_param`` — handled by the caller; no extra headers.
    return {}


def _resolve_auth_params(
    auth_method: str,
    api_token: str,
    query_param_name: str | None = None,
) -> dict[str, str]:
    """Build query-string auth parameters if applicable.

    Args:
        auth_method: The chosen auth method.
        api_token: The credential value.
        query_param_name: Query-string key name (default ``api_key``).

    Returns:
        A dict of query parameters (empty when auth is header-based).
    """
    if auth_method.lower() == "query_param":
        param = query_param_name or "api_key"
        return {param: api_token}
    return {}


def _execute_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    params: dict[str, str],
    body: dict[str, Any] | None,
    timeout: float,
    max_retries: int,
) -> dict[str, Any]:
    """Execute an HTTP request with retries and structured error handling.

    Args:
        method: HTTP verb.
        url: Fully-qualified URL.
        headers: Merged request headers.
        params: Query-string parameters.
        body: JSON body payload (ignored for GET / DELETE).
        timeout: Per-request timeout in seconds.
        max_retries: Number of retries on transient failures.

    Returns:
        Structured dict with ``status_code``, ``headers``, ``body``, and metadata.
    """
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            response = httpx.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=body if method.upper() in {"POST", "PUT", "PATCH"} else None,
                timeout=timeout,
            )

            # Retry on 429 / 5xx.
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue

            # Try to parse JSON body; fall back to raw text.
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "method": method.upper(),
                "url": url,
            }

        except httpx.TimeoutException:
            last_error = "Request timed out"
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 30))
                continue
        except httpx.RequestError as exc:
            last_error = f"Network error: {exc}"
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 30))
                continue

    return {"error": last_error or "Request failed after retries"}


# ---------------------------------------------------------------------------
# Public registration
# ---------------------------------------------------------------------------


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register generic API connector tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
        credentials: Optional credential store adapter.
    """

    def _get_api_token() -> str | None:
        """Resolve the API token from the credential store or environment.

        Returns:
            The token string, or ``None`` if not configured.
        """
        if credentials is not None:
            return credentials.get("generic_api")
        return os.getenv("GENERIC_API_TOKEN")

    # -----------------------------------------------------------------------
    # generic_api_get
    # -----------------------------------------------------------------------

    @mcp.tool()
    def generic_api_get(
        url: str,
        auth_method: Literal[
            "bearer", "api_key", "basic", "custom_header", "query_param", "none"
        ] = "bearer",
        custom_header_name: str = "",
        query_param_name: str = "",
        extra_headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict:
        """Perform a GET request against any REST API.

        Use this when you need to read data from an external or internal API
        that does not have a dedicated Hive integration.

        Args:
            url: The full URL to send the GET request to (max 2048 chars).
            auth_method: How to authenticate — ``bearer``, ``api_key``,
                ``basic`` (username:password in GENERIC_API_TOKEN),
                ``custom_header``, ``query_param``, or ``none``.
            custom_header_name: Header key when auth_method is ``custom_header``
                (default ``X-API-Key``).
            query_param_name: Query-string key when auth_method is ``query_param``
                (default ``api_key``).
            extra_headers: Additional headers to include in the request.
            params: Query-string parameters.
            timeout: Request timeout in seconds (default 30).

        Returns:
            Dict with ``status_code``, ``headers``, ``body``, ``method``, and
            ``url`` — or an ``error`` key on failure.
        """
        if not url or len(url) > _MAX_URL_LENGTH:
            return {"error": f"URL must be 1–{_MAX_URL_LENGTH} characters"}

        api_token = _get_api_token()
        if auth_method != "none" and not api_token:
            return {
                "error": "GENERIC_API_TOKEN not configured",
                "help": "Set the GENERIC_API_TOKEN environment variable "
                "or configure it in Hive credential store.",
            }

        merged_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth_method != "none":
            merged_headers.update(
                _resolve_auth_headers(auth_method, api_token, custom_header_name or None)
            )
        if extra_headers:
            merged_headers.update(extra_headers)

        merged_params = dict(params or {})
        if auth_method != "none":
            merged_params.update(
                _resolve_auth_params(auth_method, api_token, query_param_name or None)
            )

        return _execute_request(
            method="GET",
            url=url,
            headers=merged_headers,
            params=merged_params,
            body=None,
            timeout=timeout,
            max_retries=_MAX_RETRIES,
        )

    # -----------------------------------------------------------------------
    # generic_api_post
    # -----------------------------------------------------------------------

    @mcp.tool()
    def generic_api_post(
        url: str,
        body: dict[str, Any] | None = None,
        auth_method: Literal[
            "bearer", "api_key", "basic", "custom_header", "query_param", "none"
        ] = "bearer",
        custom_header_name: str = "",
        query_param_name: str = "",
        extra_headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict:
        """Perform a POST request against any REST API.

        Use this when you need to create a resource or send data to an API
        that does not have a dedicated Hive integration.

        Args:
            url: The full URL to send the POST request to (max 2048 chars).
            body: JSON-serializable body payload.
            auth_method: How to authenticate — ``bearer``, ``api_key``,
                ``basic``, ``custom_header``, ``query_param``, or ``none``.
            custom_header_name: Header key when auth_method is ``custom_header``.
            query_param_name: Query-string key when auth_method is ``query_param``.
            extra_headers: Additional headers to include in the request.
            params: Query-string parameters.
            timeout: Request timeout in seconds (default 30).

        Returns:
            Dict with ``status_code``, ``headers``, ``body``, ``method``, and
            ``url`` — or an ``error`` key on failure.
        """
        if not url or len(url) > _MAX_URL_LENGTH:
            return {"error": f"URL must be 1–{_MAX_URL_LENGTH} characters"}

        api_token = _get_api_token()
        if auth_method != "none" and not api_token:
            return {
                "error": "GENERIC_API_TOKEN not configured",
                "help": "Set the GENERIC_API_TOKEN environment variable "
                "or configure it in Hive credential store.",
            }

        merged_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth_method != "none":
            merged_headers.update(
                _resolve_auth_headers(auth_method, api_token, custom_header_name or None)
            )
        if extra_headers:
            merged_headers.update(extra_headers)

        merged_params = dict(params or {})
        if auth_method != "none":
            merged_params.update(
                _resolve_auth_params(auth_method, api_token, query_param_name or None)
            )

        return _execute_request(
            method="POST",
            url=url,
            headers=merged_headers,
            params=merged_params,
            body=body,
            timeout=timeout,
            max_retries=_MAX_RETRIES,
        )

    # -----------------------------------------------------------------------
    # generic_api_request
    # -----------------------------------------------------------------------

    @mcp.tool()
    def generic_api_request(
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET",
        body: dict[str, Any] | None = None,
        auth_method: Literal[
            "bearer", "api_key", "basic", "custom_header", "query_param", "none"
        ] = "bearer",
        custom_header_name: str = "",
        query_param_name: str = "",
        extra_headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict:
        """Perform an HTTP request with any method against any REST API.

        This is the full-featured connector for agents that need to call
        arbitrary endpoints (internal ERPs, legacy systems, third-party APIs)
        without a dedicated Hive integration.

        Supported HTTP methods: GET, POST, PUT, PATCH, DELETE.

        Args:
            url: The full URL (max 2048 chars).
            method: HTTP method to use (default ``GET``).
            body: JSON-serializable body payload (used for POST/PUT/PATCH).
            auth_method: How to authenticate — ``bearer``, ``api_key``,
                ``basic``, ``custom_header``, ``query_param``, or ``none``.
            custom_header_name: Header key when auth_method is ``custom_header``.
            query_param_name: Query-string key when auth_method is ``query_param``.
            extra_headers: Additional headers to include in the request.
            params: Query-string parameters.
            timeout: Request timeout in seconds (default 30).

        Returns:
            Dict with ``status_code``, ``headers``, ``body``, ``method``, and
            ``url`` — or an ``error`` key on failure.
        """
        if not url or len(url) > _MAX_URL_LENGTH:
            return {"error": f"URL must be 1–{_MAX_URL_LENGTH} characters"}

        upper_method = method.upper()
        if upper_method not in _ALLOWED_METHODS:
            return {
                "error": f"Unsupported HTTP method: {method}",
                "allowed": list(_ALLOWED_METHODS),
            }

        api_token = _get_api_token()
        if auth_method != "none" and not api_token:
            return {
                "error": "GENERIC_API_TOKEN not configured",
                "help": "Set the GENERIC_API_TOKEN environment variable "
                "or configure it in Hive credential store.",
            }

        merged_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth_method != "none":
            merged_headers.update(
                _resolve_auth_headers(auth_method, api_token, custom_header_name or None)
            )
        if extra_headers:
            merged_headers.update(extra_headers)

        merged_params = dict(params or {})
        if auth_method != "none":
            merged_params.update(
                _resolve_auth_params(auth_method, api_token, query_param_name or None)
            )

        return _execute_request(
            method=upper_method,
            url=url,
            headers=merged_headers,
            params=merged_params,
            body=body,
            timeout=timeout,
            max_retries=_MAX_RETRIES,
        )
