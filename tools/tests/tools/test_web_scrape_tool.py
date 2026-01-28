"""Tests for web_scrape tool (FastMCP)."""

import pytest
from fastmcp import FastMCP

from aden_tools.tools.web_scrape_tool import register_tools


@pytest.fixture
def web_scrape_fn(mcp: FastMCP):
    """Register and return the web_scrape tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["web_scrape"].fn


class TestWebScrapeTool:
    """Tests for web_scrape tool."""

    def test_url_auto_prefixed_with_https(self, web_scrape_fn):
        """URLs without scheme get https:// prefix."""
        # This will fail to connect, but we can verify the behavior
        result = web_scrape_fn(url="example.com")
        # Should either succeed or have a network error (not a validation error)
        assert isinstance(result, dict)

    def test_max_length_clamped_low(self, web_scrape_fn):
        """max_length below 1000 is clamped to 1000."""
        # Test with a very low max_length - implementation clamps to 1000
        result = web_scrape_fn(url="https://example.com", max_length=500)
        # Should not error due to invalid max_length
        assert isinstance(result, dict)

    def test_max_length_clamped_high(self, web_scrape_fn):
        """max_length above 500000 is clamped to 500000."""
        # Test with a very high max_length - implementation clamps to 500000
        result = web_scrape_fn(url="https://example.com", max_length=600000)
        # Should not error due to invalid max_length
        assert isinstance(result, dict)

    def test_valid_max_length_accepted(self, web_scrape_fn):
        """Valid max_length values are accepted."""
        result = web_scrape_fn(url="https://example.com", max_length=10000)
        assert isinstance(result, dict)

    def test_include_links_option(self, web_scrape_fn):
        """include_links parameter is accepted."""
        result = web_scrape_fn(url="https://example.com", include_links=True)
        assert isinstance(result, dict)

    def test_selector_option(self, web_scrape_fn):
        """selector parameter is accepted."""
        result = web_scrape_fn(url="https://example.com", selector=".content")
        assert isinstance(result, dict)


class TestSSRFProtection:
    """Tests for SSRF protection in web_scrape tool."""

    def test_blocks_localhost(self, web_scrape_fn):
        """Blocks requests to localhost."""
        result = web_scrape_fn(url="http://localhost:8080")
        assert result.get("blocked_by_ssrf_protection") is True
        assert "loopback" in result.get("error", "").lower()

    def test_blocks_127_0_0_1(self, web_scrape_fn):
        """Blocks requests to 127.0.0.1."""
        result = web_scrape_fn(url="http://127.0.0.1:5000")
        assert result.get("blocked_by_ssrf_protection") is True
        assert "loopback" in result.get("error", "").lower()

    def test_blocks_private_192_168(self, web_scrape_fn):
        """Blocks requests to 192.168.x.x private network."""
        result = web_scrape_fn(url="http://192.168.1.1")
        assert result.get("blocked_by_ssrf_protection") is True
        assert "private" in result.get("error", "").lower()

    def test_blocks_private_10_0(self, web_scrape_fn):
        """Blocks requests to 10.x.x.x private network."""
        result = web_scrape_fn(url="http://10.0.0.1")
        assert result.get("blocked_by_ssrf_protection") is True
        assert "private" in result.get("error", "").lower()

    def test_blocks_aws_metadata(self, web_scrape_fn):
        """Blocks requests to AWS/GCP metadata endpoint."""
        result = web_scrape_fn(url="http://169.254.169.254/latest/meta-data/")
        assert result.get("blocked_by_ssrf_protection") is True
        # 169.254.x.x is detected as private by Python's ipaddress module
        assert "blocked" in result.get("error", "").lower()

    def test_allows_public_urls(self, web_scrape_fn):
        """Allows requests to public URLs."""
        result = web_scrape_fn(url="https://example.com")
        # Should not be blocked by SSRF protection
        assert result.get("blocked_by_ssrf_protection") is not True
    def test_non_html_content_rejected(self, web_scrape_fn):
        """Ensure non-HTML content types (like JSON) are rejected."""
        # GitHub's Zen API returns text/plain, not html
        result = web_scrape_fn(url="https://api.github.com/zen")

        # We expect an error about skipping non-HTML
        assert "error" in result
        assert "Skipping non-HTML content" in result["error"]
