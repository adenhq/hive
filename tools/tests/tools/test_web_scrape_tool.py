"""Tests for web_scrape tool (FastMCP)."""

import socket
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.web_scrape_tool import register_tools
from aden_tools.tools.web_scrape_tool.web_scrape_tool import (
    _check_url_target,
    _is_internal_address,
)

# Shared patch path prefix
_MOD = "aden_tools.tools.web_scrape_tool.web_scrape_tool"


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


class TestWebScrapeToolLinkConversion:
    """Tests for link URL conversion (relative to absolute)."""

    def _mock_response(self, html_content, final_url="https://example.com/page"):
        """Create a mock httpx response object with valid HTML content-type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.url = final_url
        mock_response.headers = MagicMock()
        mock_response.headers.get = MagicMock(return_value="text/html; charset=utf-8")
        return mock_response

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_relative_links_converted_to_absolute(self, mock_get, _mock_check, web_scrape_fn):
        """Relative URLs like ../page are converted to absolute URLs."""
        html = """
        <html>
            <body>
                <a href="../home">Home</a>
                <a href="page.html">Next Page</a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html, "https://example.com/blog/post")

        result = web_scrape_fn(url="https://example.com/blog/post", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Verify relative URLs are converted to absolute
        assert "Home" in hrefs
        assert hrefs["Home"] == "https://example.com/home", f"Got {hrefs['Home']}"

        assert "Next Page" in hrefs
        expected = "https://example.com/blog/page.html"
        assert hrefs["Next Page"] == expected, f"Got {hrefs['Next Page']}"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_root_relative_links_converted(self, mock_get, _mock_check, web_scrape_fn):
        """Root-relative URLs like /about are converted to absolute URLs."""
        html = """
        <html>
            <body>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html, "https://example.com/blog/post")

        result = web_scrape_fn(url="https://example.com/blog/post", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Root-relative URLs should resolve to domain root
        assert hrefs["About"] == "https://example.com/about"
        assert hrefs["Contact"] == "https://example.com/contact"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_absolute_links_unchanged(self, mock_get, _mock_check, web_scrape_fn):
        """Absolute URLs remain unchanged."""
        html = """
        <html>
            <body>
                <a href="https://other.com">Other Site</a>
                <a href="https://example.com/page">Internal</a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html)

        result = web_scrape_fn(url="https://example.com", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Absolute URLs should remain unchanged
        assert hrefs["Other Site"] == "https://other.com"
        assert hrefs["Internal"] == "https://example.com/page"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_links_after_redirects(self, mock_get, _mock_check, web_scrape_fn):
        """Links are resolved relative to final URL after redirects."""
        html = """
        <html>
            <body>
                <a href="../prev">Previous</a>
                <a href="next">Next</a>
            </body>
        </html>
        """
        # Simulate a 302 redirect followed by a 200 response
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"location": "https://example.com/new/location"}

        final_response = self._mock_response(html, "https://example.com/new/location")

        mock_get.side_effect = [redirect_response, final_response]

        result = web_scrape_fn(url="https://example.com/old/url", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Links should be resolved relative to FINAL URL, not requested URL
        assert hrefs["Previous"] == "https://example.com/prev", (
            "Links should resolve relative to final URL after redirects"
        )
        assert hrefs["Next"] == "https://example.com/new/next"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_fragment_links_preserved(self, mock_get, _mock_check, web_scrape_fn):
        """Fragment links (anchors) are preserved."""
        html = """
        <html>
            <body>
                <a href="#section1">Section 1</a>
                <a href="/page#section2">Page Section 2</a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html, "https://example.com/page")

        result = web_scrape_fn(url="https://example.com/page", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Fragment links should be converted correctly
        assert hrefs["Section 1"] == "https://example.com/page#section1"
        assert hrefs["Page Section 2"] == "https://example.com/page#section2"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_query_parameters_preserved(self, mock_get, _mock_check, web_scrape_fn):
        """Query parameters in URLs are preserved."""
        html = """
        <html>
            <body>
                <a href="page?id=123">View Item</a>
                <a href="/search?q=test&sort=date">Search</a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html, "https://example.com/blog/post")

        result = web_scrape_fn(url="https://example.com/blog/post", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        hrefs = {link["text"]: link["href"] for link in links}

        # Query parameters should be preserved
        assert "id=123" in hrefs["View Item"]
        assert "q=test" in hrefs["Search"]
        assert "sort=date" in hrefs["Search"]

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_empty_href_skipped(self, mock_get, _mock_check, web_scrape_fn):
        """Links with empty or whitespace text are skipped."""
        html = """
        <html>
            <body>
                <a href="/valid">Valid Link</a>
                <a href="/empty"></a>
                <a href="/whitespace">   </a>
            </body>
        </html>
        """
        mock_get.return_value = self._mock_response(html)

        result = web_scrape_fn(url="https://example.com", include_links=True)

        assert "error" not in result
        assert "links" in result
        links = result["links"]
        texts = [link["text"] for link in links]

        # Only valid links should be included
        assert "Valid Link" in texts
        # Empty and whitespace-only text should be filtered
        assert "" not in texts
        assert len([t for t in texts if not t.strip()]) == 0


# ---------------------------------------------------------------------------
# SSRF Protection Tests
# ---------------------------------------------------------------------------


class TestIsInternalAddress:
    """Tests for _is_internal_address — pure IP range checks, no mocking."""

    def test_loopback_ipv4(self):
        assert _is_internal_address("127.0.0.1") is True

    def test_loopback_ipv4_high(self):
        assert _is_internal_address("127.255.255.254") is True

    def test_loopback_ipv6(self):
        assert _is_internal_address("::1") is True

    def test_private_10_range(self):
        assert _is_internal_address("10.0.0.1") is True

    def test_private_172_range(self):
        assert _is_internal_address("172.16.0.1") is True

    def test_private_172_upper_bound(self):
        assert _is_internal_address("172.31.255.255") is True

    def test_private_192_168(self):
        assert _is_internal_address("192.168.1.1") is True

    def test_link_local_aws_metadata(self):
        """169.254.169.254 is the cloud metadata endpoint."""
        assert _is_internal_address("169.254.169.254") is True

    def test_link_local_ipv6(self):
        assert _is_internal_address("fe80::1") is True

    def test_ipv6_private(self):
        assert _is_internal_address("fc00::1") is True

    def test_reserved_zero(self):
        assert _is_internal_address("0.0.0.0") is True

    def test_multicast(self):
        assert _is_internal_address("224.0.0.1") is True

    def test_ipv6_zone_id_stripped(self):
        """Zone identifiers like %eth0 must be stripped before checking."""
        assert _is_internal_address("fe80::1%eth0") is True

    def test_public_ipv4(self):
        assert _is_internal_address("8.8.8.8") is False

    def test_public_ipv4_example(self):
        assert _is_internal_address("93.184.216.34") is False

    def test_public_ipv6(self):
        assert _is_internal_address("2607:f8b0:4004:800::200e") is False

    def test_invalid_string_blocked(self):
        """Unparseable strings are treated as internal (fail closed)."""
        assert _is_internal_address("not-an-ip") is True


def _fake_addrinfo(ip: str, port: int = 443) -> list[tuple]:
    """Build a minimal getaddrinfo-style result list."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


class TestCheckUrlTarget:
    """Tests for _check_url_target — mock DNS resolution."""

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_public_hostname_allowed(self, mock_dns):
        mock_dns.return_value = _fake_addrinfo("93.184.216.34")
        assert _check_url_target("https://example.com/page") is None

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_private_hostname_blocked(self, mock_dns):
        mock_dns.return_value = _fake_addrinfo("10.0.0.1")
        result = _check_url_target("https://evil.com/steal")
        assert result is not None
        assert "internal" in result.lower()

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_loopback_hostname_blocked(self, mock_dns):
        mock_dns.return_value = _fake_addrinfo("127.0.0.1")
        result = _check_url_target("https://sneaky.com/")
        assert result is not None

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_metadata_ip_blocked(self, mock_dns):
        mock_dns.return_value = _fake_addrinfo("169.254.169.254")
        result = _check_url_target("https://metadata.attacker.com/")
        assert result is not None

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_dual_stack_any_private_blocked(self, mock_dns):
        """If any resolved IP is internal, block even if others are public."""
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
        ]
        result = _check_url_target("https://dual-homed.example.com/")
        assert result is not None

    @patch(f"{_MOD}.socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN"))
    def test_dns_failure_returns_error(self, _mock_dns):
        result = _check_url_target("https://nonexistent.invalid/")
        assert result is not None
        assert "DNS" in result

    def test_raw_private_ip_blocked(self):
        """Direct IP literal like http://127.0.0.1 is blocked without DNS."""
        result = _check_url_target("http://127.0.0.1/admin")
        assert result is not None

    def test_raw_ipv6_loopback_blocked(self):
        result = _check_url_target("http://[::1]/secret")
        assert result is not None

    def test_missing_hostname(self):
        result = _check_url_target("http:///no-host")
        assert result is not None


class TestFetchWithSsrfGuardRedirects:
    """Tests for _fetch_with_ssrf_guard redirect handling."""

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_to_private_ip_blocked(self, mock_get, mock_check):
        """A public URL redirecting to a private IP is caught."""
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"location": "http://10.0.0.1/internal"}
        mock_get.return_value = redirect

        # First call: URL passes check. Second call: redirect target is private.
        mock_check.side_effect = [None, "Blocked: internal address"]

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://safe.com/", headers={})
        assert isinstance(result, dict)
        assert "error" in result

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_to_metadata_blocked(self, mock_get, mock_check):
        """Redirect to cloud metadata endpoint is blocked."""
        redirect = MagicMock()
        redirect.status_code = 307
        redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
        mock_get.return_value = redirect

        mock_check.side_effect = [None, "Blocked: internal address"]

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://legit.com/", headers={})
        assert isinstance(result, dict)
        assert "error" in result

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_valid_redirect_followed(self, mock_get, mock_check):
        """A redirect between two public URLs succeeds."""
        redirect_resp = MagicMock()
        redirect_resp.status_code = 301
        redirect_resp.headers = {"location": "https://www.example.com/"}

        final_resp = MagicMock()
        final_resp.status_code = 200

        mock_get.side_effect = [redirect_resp, final_resp]

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://example.com/", headers={})
        assert isinstance(result, tuple)
        response, final_url = result
        assert response.status_code == 200
        assert final_url == "https://www.example.com/"

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_too_many_redirects(self, mock_get, _mock_check):
        """Exceeding the redirect limit returns an error."""
        # Each call redirects to a unique URL to avoid loop detection
        call_count = 0

        def unique_redirect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 302
            resp.headers = {"location": f"/page-{call_count}"}
            return resp

        mock_get.side_effect = unique_redirect

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://example.com/start", headers={})
        assert isinstance(result, dict)
        assert "Too many redirects" in result["error"]

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_loop_detected(self, mock_get, _mock_check):
        """A redirect that points back to the same URL is caught."""
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"location": "https://example.com/loop"}
        mock_get.return_value = redirect

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://example.com/loop", headers={})
        assert isinstance(result, dict)
        assert "loop" in result["error"].lower()

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_to_non_http_blocked(self, mock_get, _mock_check):
        """Redirects to non-HTTP schemes are rejected."""
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"location": "ftp://internal.corp/data"}
        mock_get.return_value = redirect

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://example.com/", headers={})
        assert isinstance(result, dict)
        assert "scheme" in result["error"].lower()

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_missing_location_header(self, mock_get, _mock_check):
        """A 302 without a Location header returns an error."""
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {}
        mock_get.return_value = redirect

        from aden_tools.tools.web_scrape_tool.web_scrape_tool import _fetch_with_ssrf_guard

        result = _fetch_with_ssrf_guard("https://example.com/", headers={})
        assert isinstance(result, dict)
        assert "Location" in result["error"]


class TestWebScrapeSSRF:
    """Integration tests: SSRF protection through the web_scrape tool function."""

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_blocks_private_url(self, mock_dns, web_scrape_fn):
        """Direct private IP URL is blocked before any request is made."""
        result = web_scrape_fn(url="http://192.168.1.1/admin")
        assert "error" in result
        assert result.get("blocked_by_ssrf_protection") is True

    @patch(f"{_MOD}.socket.getaddrinfo")
    def test_blocks_localhost(self, mock_dns, web_scrape_fn):
        """Localhost hostname is blocked after DNS resolution."""
        mock_dns.return_value = _fake_addrinfo("127.0.0.1")
        result = web_scrape_fn(url="http://localhost/secret")
        assert "error" in result

    @patch(f"{_MOD}._check_url_target", return_value=None)
    @patch(f"{_MOD}.httpx.get")
    def test_allows_public_url(self, mock_get, _mock_check, web_scrape_fn):
        """A normal public URL returns content successfully."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Hello world</p></body></html>"
        mock_resp.headers = MagicMock()
        mock_resp.headers.get = MagicMock(return_value="text/html; charset=utf-8")
        mock_get.return_value = mock_resp

        result = web_scrape_fn(url="https://example.com/")
        assert "error" not in result
        assert "Hello world" in result["content"]

    @patch(f"{_MOD}.socket.getaddrinfo")
    @patch(f"{_MOD}.httpx.get")
    def test_redirect_ssrf_blocked(self, mock_get, mock_dns, web_scrape_fn):
        """A public URL that redirects to a metadata endpoint is blocked."""
        # DNS: first lookup (safe.com) is public, second (169.254.169.254) is internal
        def dns_side_effect(host, *args, **kwargs):
            if host == "safe.com":
                return _fake_addrinfo("93.184.216.34")
            if host == "169.254.169.254":
                return _fake_addrinfo("169.254.169.254")
            raise socket.gaierror("unknown host")

        mock_dns.side_effect = dns_side_effect

        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
        mock_get.return_value = redirect

        result = web_scrape_fn(url="https://safe.com/page")
        assert "error" in result
        assert result.get("blocked_by_ssrf_protection") is True
