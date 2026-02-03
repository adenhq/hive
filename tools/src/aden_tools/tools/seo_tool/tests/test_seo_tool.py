"""
Unit tests for the SEO Audit Tool.

These tests use mocked HTTP responses to verify SEO analysis functionality
without making actual network requests.
"""

from unittest.mock import MagicMock, patch

import httpx
from bs4 import BeautifulSoup

from aden_tools.tools.seo_tool.seo_tool import (
    META_DESC_MAX_LENGTH,
    META_DESC_MIN_LENGTH,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    _analyze_canonical,
    _analyze_headings,
    _analyze_images,
    _analyze_meta_description,
    _analyze_meta_robots,
    _analyze_open_graph,
    _analyze_title,
    _calculate_score,
)

# Sample HTML fixtures
MINIMAL_HTML = """
<!DOCTYPE html>
<html>
<head></head>
<body><p>Hello</p></body>
</html>
"""

OPTIMAL_HTML = (
    "<!DOCTYPE html>\n<html>\n<head>\n"
    "    <title>This is an optimal title for SEO purposes test</title>\n"
    '    <meta name="description" content="This is a well-crafted meta '
    "description that provides detailed and valuable information about "
    'the page content for search engines.">\n'
    '    <link rel="canonical" href="https://example.com/page">\n'
    '    <meta name="robots" content="index, follow">\n'
    '    <meta property="og:title" content="Page Title">\n'
    '    <meta property="og:description" content="Page description">\n'
    '    <meta property="og:image" content="https://example.com/image.jpg">\n'
    '    <meta property="og:url" content="https://example.com/page">\n'
    "</head>\n<body>\n"
    "    <h1>Main Heading</h1>\n"
    "    <h2>Section 1</h2>\n"
    "    <p>Content here</p>\n"
    "    <h2>Section 2</h2>\n"
    '    <img src="image1.jpg" alt="Descriptive alt text">\n'
    '    <img src="image2.jpg" alt="Another image description">\n'
    "</body>\n</html>"
)

ISSUES_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Short</title>
    <meta name="description" content="Too short">
</head>
<body>
    <h1>First H1</h1>
    <h1>Second H1 - Multiple!</h1>
    <h3>Skipped H2 - Hierarchy Gap</h3>
    <img src="no-alt.jpg">
    <img src="empty-alt.jpg" alt="">
    <img src="good.jpg" alt="Good description">
</body>
</html>
"""

NOINDEX_HTML = (
    "<!DOCTYPE html>\n<html>\n<head>\n"
    "    <title>Noindex Page Title Example for Testing SEO</title>\n"
    '    <meta name="description" content="This page is set to noindex '
    'so search engines will not index it.">\n'
    '    <meta name="robots" content="noindex, nofollow">\n'
    "</head>\n<body>\n"
    "    <h1>Private Page</h1>\n"
    "</body>\n</html>"
)


class TestAnalyzeTitle:
    """Tests for title tag analysis."""

    def test_missing_title(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_title(soup)
        assert result["present"] is False
        assert result["content"] is None
        assert "Missing title tag" in result["issues"]

    def test_short_title(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        result = _analyze_title(soup)
        assert result["present"] is True
        assert result["content"] == "Short"
        assert result["length"] == 5
        assert result["optimal"] is False
        assert any("Too short" in issue for issue in result["issues"])

    def test_optimal_title(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_title(soup)
        assert result["present"] is True
        assert result["optimal"] is True
        assert TITLE_MIN_LENGTH <= result["length"] <= TITLE_MAX_LENGTH
        assert len(result["issues"]) == 0

    def test_long_title(self):
        html = f"<html><head><title>{'x' * 100}</title></head></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = _analyze_title(soup)
        assert result["optimal"] is False
        assert any("Too long" in issue for issue in result["issues"])


class TestAnalyzeMetaDescription:
    """Tests for meta description analysis."""

    def test_missing_meta_description(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_meta_description(soup)
        assert result["present"] is False
        assert "Missing meta description" in result["issues"]

    def test_short_meta_description(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        result = _analyze_meta_description(soup)
        assert result["present"] is True
        assert result["optimal"] is False
        assert any("Too short" in issue for issue in result["issues"])

    def test_optimal_meta_description(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_meta_description(soup)
        assert result["present"] is True
        assert result["optimal"] is True
        assert META_DESC_MIN_LENGTH <= result["length"] <= META_DESC_MAX_LENGTH

    def test_long_meta_description(self):
        html = f'<html><head><meta name="description" content="{"x" * 300}"></head></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _analyze_meta_description(soup)
        assert result["optimal"] is False
        assert any("Too long" in issue for issue in result["issues"])


class TestAnalyzeHeadings:
    """Tests for heading structure analysis."""

    def test_no_headings(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_headings(soup)
        assert result["h1_count"] == 0
        assert result["total_headings"] == 0
        assert any("Missing H1" in issue for issue in result["issues"])

    def test_multiple_h1(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        result = _analyze_headings(soup)
        assert result["h1_count"] == 2
        assert any("Multiple H1" in issue for issue in result["issues"])

    def test_heading_hierarchy_gap(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        result = _analyze_headings(soup)
        assert any("gap" in issue.lower() for issue in result["issues"])

    def test_proper_hierarchy(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_headings(soup)
        assert result["h1_count"] == 1
        assert not any("gap" in issue.lower() for issue in result["issues"])


class TestAnalyzeImages:
    """Tests for image alt text analysis."""

    def test_no_images(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_images(soup)
        assert result["total"] == 0
        assert result["optimal"] is True

    def test_images_with_alt(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_images(soup)
        assert result["total"] == 2
        assert result["with_alt"] == 2
        assert result["missing_alt_count"] == 0
        assert result["coverage_percent"] == 100.0
        assert result["optimal"] is True

    def test_images_missing_alt(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        result = _analyze_images(soup)
        assert result["total"] == 3
        assert result["missing_alt_count"] == 1
        assert result["empty_alt_count"] == 1
        assert result["optimal"] is False


class TestAnalyzeCanonical:
    """Tests for canonical tag analysis."""

    def test_missing_canonical(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_canonical(soup, "https://example.com")
        assert result["present"] is False
        assert any("Missing canonical" in issue for issue in result["issues"])

    def test_present_canonical(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_canonical(soup, "https://example.com/page")
        assert result["present"] is True
        assert result["href"] == "https://example.com/page"
        assert result["self_referencing"] is True

    def test_non_self_referencing(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_canonical(soup, "https://example.com/different")
        assert result["self_referencing"] is False


class TestAnalyzeMetaRobots:
    """Tests for meta robots analysis."""

    def test_no_robots_tag(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_meta_robots(soup)
        assert result["present"] is False
        assert result["indexable"] is True
        assert result["followable"] is True

    def test_noindex_nofollow(self):
        soup = BeautifulSoup(NOINDEX_HTML, "html.parser")
        result = _analyze_meta_robots(soup)
        assert result["present"] is True
        assert result["indexable"] is False
        assert result["followable"] is False
        assert any("noindex" in issue.lower() for issue in result["issues"])

    def test_index_follow(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_meta_robots(soup)
        assert result["present"] is True
        assert result["indexable"] is True
        assert result["followable"] is True


class TestAnalyzeOpenGraph:
    """Tests for Open Graph tag analysis."""

    def test_missing_og_tags(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        result = _analyze_open_graph(soup)
        assert result["present"] is False
        assert len(result["missing_required"]) == 4

    def test_complete_og_tags(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        result = _analyze_open_graph(soup)
        assert result["present"] is True
        assert "og:title" in result["tags"]
        assert "og:description" in result["tags"]
        assert "og:image" in result["tags"]
        assert "og:url" in result["tags"]
        assert len(result["missing_required"]) == 0


class TestCalculateScore:
    """Tests for overall score calculation."""

    def test_perfect_score(self):
        soup = BeautifulSoup(OPTIMAL_HTML, "html.parser")
        title = _analyze_title(soup)
        meta_desc = _analyze_meta_description(soup)
        headings = _analyze_headings(soup)
        images = _analyze_images(soup)
        canonical = _analyze_canonical(soup, "https://example.com/page")

        result = _calculate_score(title, meta_desc, headings, images, canonical)
        assert result["score"] >= 90
        assert result["grade"] in ["A", "B"]
        assert result["passed"] is True

    def test_low_score(self):
        soup = BeautifulSoup(MINIMAL_HTML, "html.parser")
        title = _analyze_title(soup)
        meta_desc = _analyze_meta_description(soup)
        headings = _analyze_headings(soup)
        images = _analyze_images(soup)
        canonical = _analyze_canonical(soup, "https://example.com")

        result = _calculate_score(title, meta_desc, headings, images, canonical)
        assert result["score"] < 50
        assert result["grade"] == "F"
        assert result["passed"] is False

    def test_medium_score_with_issues(self):
        soup = BeautifulSoup(ISSUES_HTML, "html.parser")
        title = _analyze_title(soup)
        meta_desc = _analyze_meta_description(soup)
        headings = _analyze_headings(soup)
        images = _analyze_images(soup)
        canonical = _analyze_canonical(soup, "https://example.com")

        result = _calculate_score(title, meta_desc, headings, images, canonical)
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ["A", "B", "C", "D", "F"]


class TestIntegration:
    """Integration tests for the full analyze_on_page function."""

    @patch("aden_tools.tools.seo_tool.seo_tool.httpx.get")
    def test_analyze_valid_url(self, mock_get):
        """Test analyzing a valid URL with mocked response."""
        mock_response = MagicMock()
        mock_response.text = OPTIMAL_HTML
        mock_response.status_code = 200
        mock_response.url = "https://example.com/page"
        mock_get.return_value = mock_response

        from aden_tools.tools.seo_tool import analyze_on_page as standalone_analyze

        # Use the module-level function
        result = standalone_analyze("https://example.com/page")

        assert "url" in result
        assert "title" in result
        assert "meta_description" in result
        assert "headings" in result
        assert "images" in result
        assert "overall_score" in result

    def test_empty_url(self):
        """Test that empty URL returns error."""
        from aden_tools.tools.seo_tool import analyze_on_page

        result = analyze_on_page("")
        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_invalid_url_scheme(self):
        """Test that non-HTTP URL returns error."""
        from aden_tools.tools.seo_tool import analyze_on_page

        result = analyze_on_page("ftp://example.com")
        assert "error" in result
        assert "http" in result["error"].lower()

    @patch("httpx.get")
    def test_timeout_error(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = httpx.TimeoutException("Timed out")

        from aden_tools.tools.seo_tool import analyze_on_page

        result = analyze_on_page("https://example.com")
        assert "error" in result
        assert "timed out" in result["error"].lower()

    @patch("httpx.get")
    def test_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        from aden_tools.tools.seo_tool import analyze_on_page

        result = analyze_on_page("https://example.com")
        assert "error" in result
        assert "404" in result["error"]
