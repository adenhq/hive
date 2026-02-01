"""Tests for Greenhouse tool."""

import pytest
import httpx
from unittest.mock import MagicMock, patch

from aden_tools.tools.greenhouse_tool.greenhouse import GreenhouseClient


class TestGreenhouseClient:
    """Test Suite for GreenhouseClient."""

    @pytest.fixture
    def client(self):
        """Standard client with dummy key."""
        return GreenhouseClient(api_key="test_key")

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_auth_header_format(self, mock_request, client):
        """Test that Basic Auth is correctly formatted."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        # Make a call
        client.list_jobs()

        # Check call args
        call_args = mock_request.call_args
        auth_arg = call_args.kwargs.get("auth")

        # httpx handles auth tuple (user, pass)
        assert auth_arg == ("test_key", "")

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_list_jobs_pagination(self, mock_request, client):
        """Test that pagination correctly aggregates results."""
        # Setup mock for 2 pages
        # We request 510 items. per_page capped at 500.
        mock_page1 = MagicMock()
        mock_page1.status_code = 200
        mock_page1.json.return_value = [{"id": 1}] * 500  # Full page

        mock_page2 = MagicMock()
        mock_page2.status_code = 200
        mock_page2.json.return_value = [{"id": 2}] * 10  # Partial page

        mock_request.side_effect = [mock_page1, mock_page2]

        # Request 510 items (spanning 2 pages)
        jobs = client.list_jobs(limit=510)

        assert len(jobs) == 510
        assert mock_request.call_count == 2

        # Verify params
        call1_params = mock_request.call_args_list[0].kwargs["params"]
        assert call1_params["page"] == 1
        assert call1_params["per_page"] == 500

        call2_params = mock_request.call_args_list[1].kwargs["params"]
        assert call2_params["page"] == 2

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_add_candidate_structure(self, mock_request, client):
        """Test that candidate creation payload is correct."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_request.return_value = mock_response

        client.add_candidate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            job_id=99,
            phone="555-0100",
            notes="Strong hire"
        )

        call_params = mock_request.call_args.kwargs["json"]

        assert call_params["first_name"] == "John"
        assert call_params["last_name"] == "Doe"
        assert call_params["email_addresses"][0]["value"] == "john@example.com"
        assert call_params["applications"][0]["job_id"] == 99
        assert call_params["phone_numbers"][0]["value"] == "555-0100"
        assert call_params["notes"][0]["body"] == "Strong hire"


    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_get_job(self, mock_request, client):
        """Test retrieving a single job."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "title": "Engineer"}
        mock_request.return_value = mock_response

        job = client.get_job(123)
        assert job["id"] == 123
        assert job["title"] == "Engineer"

        args = mock_request.call_args
        assert args[0][1].endswith("/jobs/123")
        assert args[0][0] == "GET"

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_list_candidates_filters(self, mock_request, client):
        """Test listing candidates with filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client.list_candidates(
            limit=50,
            job_id=99,
            created_after="2023-01-01T00:00:00Z"
        )

        call_params = mock_request.call_args.kwargs["params"]
        assert call_params["job_id"] == 99
        assert call_params["created_after"] == "2023-01-01T00:00:00Z"
        assert "updated_after" not in call_params

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_get_candidate(self, mock_request, client):
        """Test retrieving a single candidate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 456, "first_name": "Jane"}
        mock_request.return_value = mock_response

        candidate = client.get_candidate(456)
        assert candidate["id"] == 456
        assert candidate["first_name"] == "Jane"
        assert mock_request.call_args[0][1].endswith("/candidates/456")

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_list_applications(self, mock_request, client):
        """Test listing applications with status filter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 789}]
        mock_request.return_value = mock_response

        client.list_applications(job_id=101, status="active")

        call_params = mock_request.call_args.kwargs["params"]
        assert call_params["job_id"] == 101
        assert call_params["status"] == "active"
        assert mock_request.call_args[0][1].endswith("/applications")

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_timeout_handling(self, mock_request, client):
        """Test handling of request timeouts."""
        mock_request.side_effect = httpx.TimeoutException("Connection timed out")

        result = client.list_jobs()
        # _get_paginated wraps error response in list if first page fails
        assert isinstance(result, list)
        assert result[0] == {"error": "Request timed out"}

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_network_error_handling(self, mock_request, client):
        """Test handling of general network errors."""
        mock_request.side_effect = httpx.RequestError("DNS failure")

        result = client.get_job(123)
        assert result == {"error": "Network error: DNS failure"}

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_unexpected_exception_handling(self, mock_request, client):
        """Test handling of unexpected exceptions."""
        mock_request.side_effect = Exception("Surprise!")

        result = client.get_job(123)
        assert result == {"error": "API request failed: Surprise!"}

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_error_handling_401(self, mock_request, client):
        """Test handling of invalid API key."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with pytest.raises(
            ValueError, match="Authenticaton failed: Invalid Greenhouse API key"
        ):
            client.list_jobs()

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_error_handling_403(self, mock_request, client):
        """Test handling of permission/HTTPS errors."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response

        with pytest.raises(PermissionError):
            client.list_jobs()

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_error_handling_404(self, mock_request, client):
        """Test 404 returns error dict, not exception."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        result = client.get_job(999)
        assert "error" in result
        assert result["status"] == 404

    @patch("aden_tools.tools.greenhouse_tool.greenhouse.httpx.request")
    def test_rate_limit_handling(self, mock_request, client):
        """Test 429 returns error dict."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response

        result = client.list_jobs()
        # list_jobs returns a List[dict] because _get_paginated returns a list
        # If error occurs, _get_paginated returns [response] -> [{error:...}]
        assert isinstance(result, list)
        assert len(result) > 0
        assert "error" in result[0]
        assert result[0]["status"] == 429
