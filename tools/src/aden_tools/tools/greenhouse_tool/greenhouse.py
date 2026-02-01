"""Greenhouse Harvest API client implementation."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://harvest.greenhouse.io/v1"
DEFAULT_TIMEOUT = 30.0


class GreenhouseClient:
    """Client for Greenhouse Harvest API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the Greenhouse client.

        Args:
            api_key: Greenhouse Harvest API Key. If None, tries GREENHOUSE_API_KEY env var.
            base_url: API base URL (default: https://harvest.greenhouse.io/v1)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GREENHOUSE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Greenhouse API key is required. Set GREENHOUSE_API_KEY environment variable "
                "or pass api_key to the constructor."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Configure Basic Auth (API key as username, empty password)
        self.auth = (self.api_key, "")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """
        Make an HTTP request to the Greenhouse API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/jobs')
            params: Query parameters
            json_data: JSON request body

        Returns:
            JSON response data or raises error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = httpx.request(
                method,
                url,
                auth=self.auth,
                params=params,
                json=json_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 401:
                raise ValueError("Authenticaton failed: Invalid Greenhouse API key")
            elif response.status_code == 403:
                raise PermissionError("Access denied: Check permissions or use HTTPS")
            elif response.status_code == 404:
                return {"error": "Resource not found", "status": 404}
            elif response.status_code == 429:
                return {"error": "Rate limit exceeded", "status": 429}

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}"}
        except (ValueError, PermissionError):
            # Re-raise auth/permission errors so they aren't swallowed by broad Exception catch
            raise
        except Exception as e:
            # Catch other unexpected errors and return as error dict
            return {"error": f"API request failed: {str(e)}"}

    def _get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Handle pagination to retrieve lists of items.

        Args:
            endpoint: API endpoint
            params: Query parameters
            limit: Maximum items to return

        Returns:
            List of collected items
        """
        items: list[dict[str, Any]] = []
        page = 1
        per_page = min(limit, 500)  # Max allowed by Greenhouse is 500

        current_params = (params or {}).copy()
        current_params["per_page"] = per_page

        while len(items) < limit:
            current_params["page"] = page
            # Pass a copy to avoid reference sharing in mocks/logging/subsequent calls
            response = self._make_request("GET", endpoint, params=current_params.copy())

            if isinstance(response, dict) and "error" in response:
                if not items:  # Return error if first page fails
                    return [response]
                break  # Return what we have if later pages fail

            if not isinstance(response, list):
                # Unexpected response format
                break

            if not response:
                break

            items.extend(response)

            # Check if we should stop
            # If we got fewer items than page size, it's the last page
            if len(response) < per_page:
                break

            page += 1

        return items[:limit]

    def list_jobs(
        self,
        limit: int = 50,
        status: str = "open",
        department_id: int | None = None,
        office_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """List job postings."""
        params = {"status": status}
        if department_id:
            params["department_id"] = department_id
        if office_id:
            params["office_id"] = office_id

        return self._get_paginated("jobs", params=params, limit=limit)

    def get_job(self, job_id: int) -> dict[str, Any]:
        """Get detailed job information."""
        return self._make_request("GET", f"jobs/{job_id}")

    def list_candidates(
        self,
        limit: int = 50,
        job_id: int | None = None,
        stage: str | None = None,
        created_after: str | None = None,
        updated_after: str | None = None,
    ) -> list[dict[str, Any]]:
        """List candidates."""
        params: dict[str, Any] = {}
        if job_id:
            params["job_id"] = job_id
        if created_after:
            params["created_after"] = created_after
        if updated_after:
            params["updated_after"] = updated_after

        # Note: 'stage' filtering needs to be handled post-fetch if API doesn't support it directly
        candidates = self._get_paginated("candidates", params=params, limit=limit)

        return candidates

    def get_candidate(self, candidate_id: int) -> dict[str, Any]:
        """Get full candidate details."""
        return self._make_request("GET", f"candidates/{candidate_id}")

    def add_candidate(
        self,
        first_name: str,
        last_name: str,
        email: str,
        job_id: int,
        phone: str | None = None,
        source: str | None = None,
        resume_url: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Submit new candidate."""
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email_addresses": [{"value": email, "type": "personal"}],
            "applications": [{"job_id": job_id}]
        }

        if phone:
            data["phone_numbers"] = [{"value": phone, "type": "mobile"}]

        if resume_url:
            if not notes:
                notes = ""
            notes += f"\n\nResume URL: {resume_url}"

        if notes:
             data["notes"] = [{"body": notes, "visibility": "admin_only"}]

        return self._make_request("POST", "candidates", json_data=data)

    def list_applications(
        self,
        job_id: int,
        limit: int = 50,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List applications for a job."""
        params = {"job_id": job_id}
        if status:
            params["status"] = status

        return self._get_paginated("applications", params=params, limit=limit)
