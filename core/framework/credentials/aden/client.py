"""
Aden Credential Client.

HTTP client for communicating with the Aden authentication server.
The Aden server handles OAuth2 authorization flows and token management.
This client fetches tokens and delegates refresh operations to Aden.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# --- Exception Hierarchy ---

class AdenClientError(Exception):
    """Base exception for Aden client errors."""
    pass


class AdenAuthenticationError(AdenClientError):
    """Raised when API key is invalid or revoked."""
    pass


class AdenNotFoundError(AdenClientError):
    """Raised when integration is not found."""
    pass


class AdenRefreshError(AdenClientError):
    """Raised when token refresh fails."""

    def __init__(
        self,
        message: str,
        requires_reauthorization: bool = False,
        reauthorization_url: str | None = None,
    ):
        super().__init__(message)
        self.requires_reauthorization = requires_reauthorization
        self.reauthorization_url = reauthorization_url


class AdenRateLimitError(AdenClientError):
    """Raised when rate limited."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


# --- Configuration and Response Models ---

@dataclass
class AdenClientConfig:
    """Configuration for Aden API client."""

    base_url: str
    api_key: str | None = None
    tenant_id: str | None = None
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """Load API key from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.environ.get("ADEN_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "Aden API key not provided. Pass api_key to AdenClientConfig "
                    "or set the ADEN_API_KEY environment variable."
                )


@dataclass
class AdenCredentialResponse:
    """Response from Aden server containing credential data."""

    integration_id: str
    integration_type: str
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdenCredentialResponse:
        """Create from API response dictionary."""
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        return cls(
            integration_id=data["integration_id"],
            integration_type=data["integration_type"],
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scopes=data.get("scopes", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AdenIntegrationInfo:
    """Information about an available integration."""

    integration_id: str
    integration_type: str
    status: str
    expires_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdenIntegrationInfo:
        """Create from API response dictionary."""
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        return cls(
            integration_id=data["integration_id"],
            integration_type=data.get("provider", data["integration_id"]),
            status=data.get("status", "unknown"),
            expires_at=expires_at,
        )


# --- Core Client Logic ---

class AdenCredentialClient:
    """HTTP client for Aden credential server."""

    def __init__(self, config: AdenClientConfig):
        self.config = config
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client with default headers."""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "hive-credential-store/1.0",
            }
            if self.config.tenant_id:
                headers["X-Tenant-ID"] = self.config.tenant_id

            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=headers,
            )
        return self._client

    def _safe_json_parse(self, response: httpx.Response) -> Any:
        """
        Safely parse JSON response and raise AdenClientError on failure.
        
        ENHANCEMENT: This method prevents crashes (JSONDecodeError) when proxies 
        (Nginx/Cloudflare) return HTML error pages instead of JSON.
        """
        # Guard against empty bodies (e.g., 204 No Content)
        if not response.content:
            return {}

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as e:
            # ENHANCEMENT: Provide a body preview to help developers see the non-JSON content
            body_preview = response.text[:200] if response.text else "Empty Body"
            raise AdenClientError(
                f"Failed to parse Aden server response as JSON. "
                f"Status: {response.status_code}. "
                f"Preview: {body_preview}"
            ) from e

    def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a request with exponential backoff retry logic."""
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.config.retry_attempts):
            try:
                response = client.request(method, path, **kwargs)

                # Classification of HTTP Errors
                if response.status_code == 401:
                    raise AdenAuthenticationError("Agent API key is invalid or revoked")

                if response.status_code == 404:
                    raise AdenNotFoundError(f"Integration not found: {path}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise AdenRateLimitError(
                        "Rate limited by Aden server",
                        retry_after=retry_after,
                    )

                if response.status_code == 400:
                    # FIX: Use safe parser to handle potential HTML 400 pages
                    data = self._safe_json_parse(response)
                    if data.get("error") == "refresh_failed":
                        raise AdenRefreshError(
                            data.get("message", "Token refresh failed"),
                            requires_reauthorization=data.get("requires_reauthorization", False),
                            reauthorization_url=data.get("reauthorization_url"),
                        )

                # Ensure we catch other 4xx/5xx status codes
                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2**attempt)
                    logger.warning(
                        f"Aden request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    raise AdenClientError(f"Failed to connect to Aden server: {e}") from e

            except (
                AdenAuthenticationError,
                AdenNotFoundError,
                AdenRefreshError,
                AdenRateLimitError,
            ):
                # Don't retry client-side or specific business logic errors
                raise

        raise AdenClientError(
            f"Request failed after {self.config.retry_attempts} attempts"
        ) from last_error

    def get_credential(self, integration_id: str) -> AdenCredentialResponse | None:
        """Fetch the current access token for a specific integration."""
        try:
            response = self._request_with_retry("GET", f"/v1/credentials/{integration_id}")
            # FIX: Robust parsing prevents unhandled crashes here
            data = self._safe_json_parse(response)
            return AdenCredentialResponse.from_dict(data)
        except AdenNotFoundError:
            return None

    def request_refresh(self, integration_id: str) -> AdenCredentialResponse:
        """Force the Aden server to refresh the integration token."""
        response = self._request_with_retry("POST", f"/v1/credentials/{integration_id}/refresh")
        data = self._safe_json_parse(response)
        return AdenCredentialResponse.from_dict(data)

    def list_integrations(self) -> list[AdenIntegrationInfo]:
        """Fetch all connected integrations for the current tenant."""
        response = self._request_with_retry("GET", "/v1/credentials")
        data = self._safe_json_parse(response)
        return [AdenIntegrationInfo.from_dict(item) for item in data.get("integrations", [])]

    def validate_token(self, integration_id: str) -> dict[str, Any]:
        """Check if a token is valid without full credential fetching."""
        response = self._request_with_retry("GET", f"/v1/credentials/{integration_id}/validate")
        return self._safe_json_parse(response)

    def report_usage(
        self,
        integration_id: str,
        operation: str,
        status: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Optional telemetry reporting for analytics."""
        try:
            self._request_with_retry(
                "POST",
                f"/v1/credentials/{integration_id}/usage",
                json={
                    "operation": operation,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": metadata or {},
                },
            )
        except Exception as e:
            # Usage reporting should never crash the main thread
            logger.warning(f"Failed to report usage for '{integration_id}': {e}")

    def health_check(self) -> dict[str, Any]:
        """Check server availability and return latency metrics."""
        try:
            client = self._get_client()
            response = client.get("/health")
            if response.status_code == 200:
                data = self._safe_json_parse(response)
                data["latency_ms"] = response.elapsed.total_seconds() * 1000
                return data
            return {
                "status": "degraded",
                "error": f"Unexpected status code: {response.status_code}",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> AdenCredentialClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()