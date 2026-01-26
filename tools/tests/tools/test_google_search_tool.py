"""Tests for google_search tool (FastMCP)."""

import pytest

from fastmcp import FastMCP
from aden_tools.tools.google_search_tool import register_tools


@pytest.fixture
def google_search_fn(mcp: FastMCP):
    """Register and return the google_search tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["google_search"].fn


class TestGoogleSearchTool:
    """Tests for google_search tool."""

    def test_search_missing_api_key(self, google_search_fn, monkeypatch):
        """Search without API key returns helpful error."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

        result = google_search_fn(query="test query")

        assert "error" in result
        assert "GOOGLE_API_KEY" in result["error"]
        assert "help" in result

    def test_search_missing_cse_id(self, google_search_fn, monkeypatch):
        """Search with API key but missing CSE ID returns helpful error."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

        result = google_search_fn(query="test query")

        assert "error" in result
        assert "GOOGLE_CSE_ID" in result["error"]
        assert "help" in result

    def test_empty_query_returns_error(self, google_search_fn, monkeypatch):
        """Empty query returns error."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")

        result = google_search_fn(query="")

        assert "error" in result
        assert (
            "1-500" in result["error"].lower() or "character" in result["error"].lower()
        )

    def test_long_query_returns_error(self, google_search_fn, monkeypatch):
        """Query exceeding 500 chars returns error."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")

        result = google_search_fn(query="x" * 501)

        assert "error" in result

    def test_num_results_clamped_to_valid_range(self, google_search_fn, monkeypatch):
        """num_results outside 1-10 is clamped (not error)."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")

        result = google_search_fn(query="test", num_results=0)
        assert isinstance(result, dict)

        result = google_search_fn(query="test", num_results=100)
        assert isinstance(result, dict)

    def test_default_parameters(self, google_search_fn, monkeypatch):
        """Default parameters are set correctly."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")

        result = google_search_fn(query="test")
        assert isinstance(result, dict)

    def test_custom_language_and_country(self, google_search_fn, monkeypatch):
        """Custom language and country parameters are accepted."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")

        result = google_search_fn(query="test", language="id", country="id")
        assert isinstance(result, dict)
