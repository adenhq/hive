"""
SEO Audit Tool - Analyze webpages for on-page SEO optimization.

Provides comprehensive SEO health reports including title tags, meta descriptions,
heading hierarchy, image alt text coverage, and canonical tag verification.
"""

from .seo_tool import register_tools

__all__ = ["register_tools"]


# Standalone usage function
def analyze_on_page(url: str) -> dict:
    """
    Convenience function to analyze SEO without setting up MCP.

    For standalone usage, import and call directly:
        from aden_tools.tools.seo_tool import analyze_on_page
        result = analyze_on_page("https://example.com")

    Args:
        url: The URL of the webpage to analyze

    Returns:
        Dict with comprehensive SEO health report
    """
    import httpx
    from bs4 import BeautifulSoup

    from .seo_tool import (
        USER_AGENT,
        _analyze_canonical,
        _analyze_headings,
        _analyze_images,
        _analyze_meta_description,
        _analyze_meta_robots,
        _analyze_open_graph,
        _analyze_title,
        _calculate_score,
    )

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

    soup = BeautifulSoup(response.text, "html.parser")

    title = _analyze_title(soup)
    meta_desc = _analyze_meta_description(soup)
    headings = _analyze_headings(soup)
    images = _analyze_images(soup)
    canonical = _analyze_canonical(soup, url)
    robots = _analyze_meta_robots(soup)
    open_graph = _analyze_open_graph(soup)
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
