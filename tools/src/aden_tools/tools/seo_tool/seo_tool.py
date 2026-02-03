"""
SEO Audit Tool - Analyze webpages for on-page SEO optimization.

This tool provides comprehensive SEO health reports for webpages, helping
agents automate technical marketing tasks and ensure content is optimized
for search engines.

Use cases:
- Content agents checking blog posts for SEO issues before publishing
- Competitor analysis to extract heading structures and keywords
- Periodic audits to detect SEO regressions after deployments
"""

from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# SEO best practice limits
TITLE_MIN_LENGTH = 30
TITLE_MAX_LENGTH = 60
META_DESC_MIN_LENGTH = 120
META_DESC_MAX_LENGTH = 160

# User agent for requests
USER_AGENT = "AdenSEOBot/1.0 (+https://github.com/adenhq/hive)"


def _analyze_title(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze the title tag for SEO best practices.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with title analysis including content, length, and issues
    """
    title_tag = soup.find("title")
    if not title_tag or not title_tag.string:
        return {
            "present": False,
            "content": None,
            "length": 0,
            "optimal": False,
            "issues": ["Missing title tag"],
        }

    title = title_tag.string.strip()
    length = len(title)

    issues = []
    if length < TITLE_MIN_LENGTH:
        issues.append(f"Too short ({length} chars, recommended min {TITLE_MIN_LENGTH})")
    if length > TITLE_MAX_LENGTH:
        issues.append(f"Too long ({length} chars, recommended max {TITLE_MAX_LENGTH})")

    return {
        "present": True,
        "content": title,
        "length": length,
        "optimal": TITLE_MIN_LENGTH <= length <= TITLE_MAX_LENGTH,
        "issues": issues,
    }


def _analyze_meta_description(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze the meta description tag for SEO best practices.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with meta description analysis
    """
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content"):
        return {
            "present": False,
            "content": None,
            "length": 0,
            "optimal": False,
            "issues": ["Missing meta description"],
        }

    content = meta["content"].strip()
    length = len(content)

    issues = []
    if length < META_DESC_MIN_LENGTH:
        issues.append(
            f"Too short ({length} chars, recommended min {META_DESC_MIN_LENGTH})"
        )
    if length > META_DESC_MAX_LENGTH:
        issues.append(
            f"Too long ({length} chars, recommended max {META_DESC_MAX_LENGTH})"
        )

    return {
        "present": True,
        "content": content,
        "length": length,
        "optimal": META_DESC_MIN_LENGTH <= length <= META_DESC_MAX_LENGTH,
        "issues": issues,
    }


def _analyze_headings(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze heading hierarchy H1-H6 for proper structure.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with heading structure analysis
    """
    headings: dict[str, dict[str, Any]] = {}
    hierarchy: list[dict[str, Any]] = []

    for level in range(1, 7):
        tag = f"h{level}"
        found = soup.find_all(tag)
        headings[tag] = {
            "count": len(found),
            "content": [h.get_text(strip=True)[:100] for h in found[:5]],
        }
        for h in found:
            hierarchy.append({"level": level, "text": h.get_text(strip=True)[:100]})

    issues = []
    if headings["h1"]["count"] == 0:
        issues.append("Missing H1 tag - every page should have exactly one H1")
    elif headings["h1"]["count"] > 1:
        issues.append(
            f"Multiple H1 tags found ({headings['h1']['count']}) - "
            "only one H1 recommended per page"
        )

    # Check for heading hierarchy gaps
    prev_level = 0
    for item in hierarchy:
        if item["level"] > prev_level + 1 and prev_level > 0:
            issues.append(
                f"Heading hierarchy gap: H{prev_level} followed by H{item['level']}"
            )
            break
        prev_level = item["level"]

    return {
        "structure": headings,
        "hierarchy": hierarchy[:20],
        "h1_count": headings["h1"]["count"],
        "total_headings": sum(h["count"] for h in headings.values()),
        "issues": issues,
    }


def _analyze_images(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze image alt text coverage for accessibility and SEO.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with image analysis including alt text coverage
    """
    images = soup.find_all("img")
    total = len(images)

    if total == 0:
        return {
            "total": 0,
            "with_alt": 0,
            "missing_alt_count": 0,
            "coverage_percent": 100.0,
            "missing_alt_examples": [],
            "optimal": True,
            "issues": [],
        }

    missing_alt = []
    empty_alt = []
    for img in images:
        alt = img.get("alt")
        src = img.get("src", img.get("data-src", "unknown"))[:100]
        if alt is None:
            missing_alt.append(src)
        elif alt.strip() == "":
            empty_alt.append(src)

    missing_count = len(missing_alt)
    with_alt = total - missing_count - len(empty_alt)
    coverage = (with_alt / total * 100) if total > 0 else 100

    issues = []
    if missing_count > 0:
        issues.append(f"{missing_count} image(s) missing alt attribute")
    if len(empty_alt) > 0:
        issues.append(f"{len(empty_alt)} image(s) have empty alt attribute")

    return {
        "total": total,
        "with_alt": with_alt,
        "missing_alt_count": missing_count,
        "empty_alt_count": len(empty_alt),
        "coverage_percent": round(coverage, 1),
        "missing_alt_examples": missing_alt[:5],
        "optimal": missing_count == 0 and len(empty_alt) == 0,
        "issues": issues,
    }


def _analyze_canonical(soup: BeautifulSoup, url: str) -> dict[str, Any]:
    """Verify canonical tag presence and correctness.

    Args:
        soup: BeautifulSoup parsed HTML document
        url: The URL being analyzed

    Returns:
        Dict with canonical tag analysis
    """
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if not canonical or not canonical.get("href"):
        return {
            "present": False,
            "href": None,
            "self_referencing": False,
            "issues": ["Missing canonical tag - helps prevent duplicate content issues"],
        }

    href = canonical["href"].strip()

    # Normalize URLs for comparison
    normalized_url = url.rstrip("/").lower()
    normalized_href = href.rstrip("/").lower()

    return {
        "present": True,
        "href": href,
        "self_referencing": normalized_href == normalized_url,
        "issues": [],
    }


def _analyze_meta_robots(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze meta robots tag for indexing directives.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with robots meta tag analysis
    """
    robots = soup.find("meta", attrs={"name": "robots"})
    if not robots or not robots.get("content"):
        return {
            "present": False,
            "content": None,
            "indexable": True,
            "followable": True,
            "issues": [],
        }

    content = robots["content"].lower()
    directives = [d.strip() for d in content.split(",")]

    indexable = "noindex" not in directives
    followable = "nofollow" not in directives

    issues = []
    if not indexable:
        issues.append("Page is set to noindex - will not appear in search results")
    if not followable:
        issues.append("Page is set to nofollow - links will not be crawled")

    return {
        "present": True,
        "content": content,
        "directives": directives,
        "indexable": indexable,
        "followable": followable,
        "issues": issues,
    }


def _analyze_open_graph(soup: BeautifulSoup) -> dict[str, Any]:
    """Analyze Open Graph tags for social sharing.

    Args:
        soup: BeautifulSoup parsed HTML document

    Returns:
        Dict with Open Graph analysis
    """
    og_tags = {}
    required_tags = ["og:title", "og:description", "og:image", "og:url"]

    for tag in soup.find_all("meta", attrs={"property": True}):
        prop = tag.get("property", "")
        if prop.startswith("og:"):
            og_tags[prop] = tag.get("content", "")

    missing = [tag for tag in required_tags if tag not in og_tags]

    issues = []
    if missing:
        issues.append(f"Missing Open Graph tags: {', '.join(missing)}")

    return {
        "present": len(og_tags) > 0,
        "tags": og_tags,
        "missing_required": missing,
        "issues": issues,
    }


def _calculate_score(
    title: dict,
    meta_desc: dict,
    headings: dict,
    images: dict,
    canonical: dict,
) -> dict[str, Any]:
    """Calculate overall SEO score based on all factors.

    Args:
        title: Title analysis result
        meta_desc: Meta description analysis result
        headings: Headings analysis result
        images: Images analysis result
        canonical: Canonical analysis result

    Returns:
        Dict with overall score, grade, and summary of issues
    """
    score = 100
    issues = []

    # Title (20 points)
    if not title["present"]:
        score -= 20
        issues.append("Missing title tag (-20)")
    elif not title["optimal"]:
        score -= 10
        issues.append("Title length not optimal (-10)")

    # Meta description (20 points)
    if not meta_desc["present"]:
        score -= 20
        issues.append("Missing meta description (-20)")
    elif not meta_desc["optimal"]:
        score -= 10
        issues.append("Meta description length not optimal (-10)")

    # H1 tag (20 points)
    h1_count = headings.get("h1_count", 0)
    if h1_count == 0:
        score -= 20
        issues.append("Missing H1 tag (-20)")
    elif h1_count > 1:
        score -= 10
        issues.append(f"Multiple H1 tags: {h1_count} found (-10)")

    # Images alt text (20 points)
    if not images["optimal"]:
        missing = images.get("missing_alt_count", 0) + images.get("empty_alt_count", 0)
        penalty = min(20, missing * 2)
        score -= penalty
        if penalty > 0:
            issues.append(f"{missing} images with alt text issues (-{penalty})")

    # Canonical (10 points)
    if not canonical["present"]:
        score -= 10
        issues.append("Missing canonical tag (-10)")

    # Heading hierarchy (10 points)
    if headings.get("issues"):
        for issue in headings["issues"]:
            if "gap" in issue.lower():
                score -= 5
                issues.append("Heading hierarchy issues (-5)")
                break

    score = max(0, score)

    # Determine grade
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "max_score": 100,
        "issues": issues,
        "passed": score >= 70,
    }


def register_tools(mcp: FastMCP) -> None:
    """Register SEO audit tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def analyze_on_page(url: str) -> dict:
        """
        Analyze a webpage for on-page SEO health and optimization opportunities.

        Returns a comprehensive SEO health report including:
        - Title tag analysis (presence, length, content)
        - Meta description check (presence, length, content)
        - Heading hierarchy structure (H1-H6)
        - Image alt text coverage
        - Canonical tag verification
        - Meta robots directives
        - Open Graph tags for social sharing
        - Overall SEO score and grade

        Args:
            url: The URL of the webpage to analyze (must be publicly accessible)

        Returns:
            Dict with comprehensive SEO health report, or error dict on failure
        """
        # Validate URL
        if not url or not url.strip():
            return {"error": "URL cannot be empty"}

        if not url.startswith(("http://", "https://")):
            return {"error": "URL must start with http:// or https://"}

        try:
            response = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            return {"error": f"Request timed out after 30 seconds: {url}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error {e.response.status_code}: {url}"}
        except httpx.RequestError as e:
            return {"error": f"Failed to fetch URL: {e}"}

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Run all analyses
        title = _analyze_title(soup)
        meta_desc = _analyze_meta_description(soup)
        headings = _analyze_headings(soup)
        images = _analyze_images(soup)
        canonical = _analyze_canonical(soup, url)
        robots = _analyze_meta_robots(soup)
        open_graph = _analyze_open_graph(soup)

        # Calculate overall score
        overall = _calculate_score(title, meta_desc, headings, images, canonical)

        return {
            "url": url,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "title": title,
            "meta_description": meta_desc,
            "headings": headings,
            "images": images,
            "canonical": canonical,
            "robots": robots,
            "open_graph": open_graph,
            "overall_score": overall,
        }
