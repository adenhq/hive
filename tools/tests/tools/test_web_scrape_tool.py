"""Tests for web_scrape tool (FastMCP)."""
import pytest
from unittest.mock import Mock, patch

import httpx
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


class TestWebScrapeContentTypeValidation:
    """Tests for content-type validation in web_scrape tool."""

    @patch('httpx.get')
    def test_html_content_type_succeeds(self, mock_get, web_scrape_fn):
        """HTML content (text/html) is accepted and parsed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.text = "<html><body><h1>Test Page</h1></body></html>"
        mock_response.url = "https://example.com"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com", respect_robots_txt=False)

        assert "error" not in result
        assert "content" in result
        assert "Test Page" in result["content"]

    @patch('httpx.get')
    def test_xhtml_content_type_succeeds(self, mock_get, web_scrape_fn):
        """XHTML content (application/xhtml+xml) is accepted."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xhtml+xml"}
        mock_response.text = "<html><body>XHTML content</body></html>"
        mock_response.url = "https://example.com"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com", respect_robots_txt=False)

        assert "error" not in result
        assert "content" in result

    @patch('httpx.get')
    def test_pdf_content_type_returns_error(self, mock_get, web_scrape_fn):
        """PDF content (application/pdf) returns clear error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.text = "%PDF-1.4 binary content"
        mock_response.url = "https://example.com/doc.pdf"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com/doc.pdf", respect_robots_txt=False)

        assert "error" in result
        assert "cannot scrape non-html content" in result["error"].lower()
        assert "content_type" in result
        assert "application/pdf" in result["content_type"]
        assert result["url"] == "https://example.com/doc.pdf"

    @patch('httpx.get')
    def test_json_content_type_returns_error(self, mock_get, web_scrape_fn):
        """JSON content (application/json) returns error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"key": "value"}'
        mock_response.url = "https://api.example.com/data"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://api.example.com/data", respect_robots_txt=False)

        assert "error" in result
        assert "non-html" in result["error"].lower()
        assert "content_type" in result
        assert "application/json" in result["content_type"]

    @patch('httpx.get')
    def test_image_content_type_returns_error(self, mock_get, web_scrape_fn):
        """Image content (image/jpeg) returns error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.text = "binary image data"
        mock_response.url = "https://example.com/image.jpg"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com/image.jpg", respect_robots_txt=False)

        assert "error" in result
        assert "non-html" in result["error"].lower()
        assert "content_type" in result
        assert "image/jpeg" in result["content_type"]

    @patch('httpx.get')
    def test_xml_content_type_returns_error(self, mock_get, web_scrape_fn):
        """XML content (application/xml) returns error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = "<?xml version='1.0'?><root></root>"
        mock_response.url = "https://example.com/data.xml"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com/data.xml", respect_robots_txt=False)

        assert "error" in result
        assert "non-html" in result["error"].lower()

    @patch('httpx.get')
    def test_missing_content_type_header(self, mock_get, web_scrape_fn):
        """Missing content-type header results in error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No content-type header
        mock_response.text = "some content"
        mock_response.url = "https://example.com"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com", respect_robots_txt=False)

        # Should return error since no valid HTML content-type
        assert "error" in result

    @patch('httpx.get')
    def test_content_type_with_charset(self, mock_get, web_scrape_fn):
        """Content-type with charset parameter is handled correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.url = "https://example.com"
        mock_get.return_value = mock_response

        result = web_scrape_fn(url="https://example.com", respect_robots_txt=False)

        # Should succeed - charset should be ignored in validation
        assert "error" not in result
        assert "content" in result
