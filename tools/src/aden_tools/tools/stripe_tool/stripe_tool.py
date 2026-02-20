"""
Stripe Tool - Interact with Stripe customers, payments, and invoices.

API Reference: https://docs.stripe.com/api
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

STRIPE_API_BASE = "https://api.stripe.com/v1"


def _sanitize_error_message(error: Exception) -> str:
    """Sanitize error messages to prevent token leaks."""
    error_str = str(error)
    if "Authorization" in error_str or "Bearer" in error_str:
        return "Network error occurred"
    return f"Network error: {error_str}"


class _StripeClient:
    """Internal client wrapping Stripe REST API v1 calls."""

    def __init__(self, token: str):
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Stripe API response format."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Stripe token"}
        if response.status_code == 403:
            return {"error": "Forbidden - check token permissions"}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "Rate limit exceeded"}
        if response.status_code >= 400:
            try:
                error_data = response.json().get("error", {})
                detail = error_data.get("message", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Stripe API error (HTTP {response.status_code}): {detail}"}

        try:
            return {"success": True, "data": response.json()}
        except Exception:
            return {"success": True, "data": {}}

    def list_customers(self, limit: int = 10) -> dict[str, Any]:
        """List Stripe customers."""
        params = {"limit": min(limit, 100)}
        response = httpx.get(
            f"{STRIPE_API_BASE}/customers",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_customer(self, email: str, name: str | None = None) -> dict[str, Any]:
        """Create a new Stripe customer."""
        data = {"email": email}
        if name:
            data["name"] = name
        response = httpx.post(
            f"{STRIPE_API_BASE}/customers",
            headers=self._headers,
            data=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_payment_intents(self, limit: int = 10) -> dict[str, Any]:
        """List Stripe payment intents."""
        params = {"limit": min(limit, 100)}
        response = httpx.get(
            f"{STRIPE_API_BASE}/payment_intents",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_payment_link(self, price_id: str, quantity: int = 1) -> dict[str, Any]:
        """Create a Stripe payment link for a product price."""
        data = {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": quantity,
        }
        response = httpx.post(
            f"{STRIPE_API_BASE}/payment_links",
            headers=self._headers,
            data=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_invoices(self, limit: int = 10) -> dict[str, Any]:
        """List Stripe invoices."""
        params = {"limit": min(limit, 100)}
        response = httpx.get(
            f"{STRIPE_API_BASE}/invoices",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Stripe tools with the MCP server."""

    def _get_token() -> str | None:
        """Get Stripe token from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("stripe")
            if token is not None and not isinstance(token, str):
                raise TypeError(
                    f"Expected string from credentials.get('stripe'), got {type(token).__name__}"
                )
            return token
        return os.getenv("STRIPE_SECRET_KEY")

    def _get_client() -> _StripeClient | dict[str, str]:
        """Get a Stripe client, or return an error dict if no credentials."""
        token = _get_token()
        if not token:
            return {
                "error": "Stripe credentials not configured",
                "help": (
                    "Set STRIPE_SECRET_KEY environment variable "
                    "or configure via credential store. "
                    "Get a key at https://dashboard.stripe.com/apikeys"
                ),
            }
        return _StripeClient(token)

    @mcp.tool()
    def stripe_list_customers(limit: int = 10) -> dict:
        """
        List your Stripe customers.

        Args:
            limit: Maximum number of customers to return (1-100, default 10)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_customers(limit=limit)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}

    @mcp.tool()
    def stripe_create_customer(email: str, name: str | None = None) -> dict:
        """
        Create a new customer in your Stripe account.

        Args:
            email: Customer's email address
            name: Customer's full name (optional)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_customer(email=email, name=name)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}

    @mcp.tool()
    def stripe_list_payments(limit: int = 10) -> dict:
        """
        List recent Stripe payment intents.

        Args:
            limit: Maximum number of payments to return (1-100, default 10)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_payment_intents(limit=limit)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}

    @mcp.tool()
    def stripe_create_payment_link(price_id: str, quantity: int = 1) -> dict:
        """
        Create a public Stripe payment link for a specific price.

        Args:
            price_id: ID of the Stripe Price object
            quantity: Quantity of the item (default 1)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_payment_link(price_id=price_id, quantity=quantity)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}

    @mcp.tool()
    def stripe_list_invoices(limit: int = 10) -> dict:
        """
        List your Stripe invoices.

        Args:
            limit: Maximum number of invoices to return (1-100, default 10)
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_invoices(limit=limit)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}
