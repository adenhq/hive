"""
Web Scrape Tool - Extract content from web pages.

Uses httpx for requests and BeautifulSoup for HTML parsing.
Returns clean text content from web pages.
Respect robots.txt by default for ethical scraping.
Includes SSRF protection to prevent internal network access.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any, List
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# Cache for robots.txt parsers (domain -> parser)
_robots_cache: dict[str, RobotFileParser | None] = {}

# User-Agent for the scraper - identifies as a bot for transparency
USER_AGENT = "AdenBot/1.0 (https://adenhq.com; web scraping tool)"

# Browser-like User-Agent for actual page requests
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is private, reserved, or localhost.
    
    Args:
        ip: IP address string (IPv4 or IPv6)
        
    Returns:
        True if IP is private/reserved/localhost, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # Check for private, loopback, link-local, multicast, reserved
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        # Invalid IP address format
        return True  # Block invalid IPs to be safe


def _resolve_and_validate_url(url: str) -> tuple[bool, str]:
    """
    Resolve hostname to IP and validate it's not targeting internal resources.
    
    Args:
        url: Full URL to validate
        
    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return False, "Invalid URL: no hostname found"
        
        # Special case: block direct IP addresses
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if _is_private_ip(hostname):
                return False, f"Access to private/internal IP addresses is blocked: {hostname}"
        except ValueError:
            # Not a direct IP, continue with DNS resolution
            pass
        
        # Resolve hostname to IP address(es)
        try:
            # Get all IP addresses for the hostname
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            
            # Check each resolved IP
            for info in addr_info:
                ip = info[4][0]
                
                # Remove IPv6 zone identifier if present (e.g., "fe80::1%eth0" -> "fe80::1")
                if '%' in ip:
                    ip = ip.split('%')[0]
                
                if _is_private_ip(ip):
                    return False, f"Hostname '{hostname}' resolves to private/internal IP: {ip}"
            
            # All IPs are public, allow the request
            return True, f"Hostname '{hostname}' resolved to public IP(s)"
            
        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{hostname}': {str(e)}"
        except Exception as e:
            return False, f"Error resolving hostname '{hostname}': {str(e)}"
            
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def _get_robots_parser(base_url: str, timeout: float = 10.0) -> RobotFileParser | None:
    """
    Fetch and parse robots.txt for a domain.
    
    Args:
        base_url: Base URL of the domain (e.g., 'https://example.com')
        timeout: Timeout for fetching robots.txt
        
    Returns:
        RobotFileParser if robots.txt exists and was parsed, None otherwise
    """
    if base_url in _robots_cache:
        return _robots_cache[base_url]
    
    robots_url = f"{base_url}/robots.txt"
    parser = RobotFileParser()
    
    try:
        response = httpx.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        )
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            _robots_cache[base_url] = parser
            return parser
        else:
            # No robots.txt or error (4xx/5xx) - allow all by convention
            _robots_cache[base_url] = None
            return None
    except (httpx.TimeoutException, httpx.RequestError):
        # Can't fetch robots.txt - allow but don't cache (might be temporary)
        return None


def _is_allowed_by_robots(url: str) -> tuple[bool, str]:
    """
    Check if URL is allowed by robots.txt.
    
    Args:
        url: Full URL to check
        
    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"
    
    parser = _get_robots_parser(base_url)
    
    if parser is None:
        # No robots.txt found or couldn't fetch - all paths allowed
        return True, "No robots.txt found or not accessible"
    
    # Check both our bot user-agent and wildcard
    if parser.can_fetch(USER_AGENT, path) and parser.can_fetch("*", path):
        return True, "Allowed by robots.txt"
    else:
        return False, f"Blocked by robots.txt for path: {path}"


def register_tools(mcp: FastMCP) -> None:
    """Register web scrape tools with the MCP server."""

    @mcp.tool()
    def web_scrape(
        url: str,
        selector: str | None = None,
        include_links: bool = False,
        max_length: int = 50000,
        respect_robots_txt: bool = True,
    ) -> dict:
        """
        Scrape and extract text content from a webpage.

        Use when you need to read the content of a specific URL,
        extract data from a website, or read articles/documentation.

        Args:
            url: URL of the webpage to scrape
            selector: CSS selector to target specific content (e.g., 'article', '.main-content')
            include_links: Include extracted links in the response
            max_length: Maximum length of extracted text (1000-500000)
            respect_robots_txt: Whether to respect robots.txt rules (default: True)

        Returns:
            Dict with scraped content (url, title, description, content, length) or error dict
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # SSRF Protection: Validate URL doesn't target internal resources
            allowed, reason = _resolve_and_validate_url(url)
            if not allowed:
                return {
                    "error": f"SSRF Protection: {reason}",
                    "blocked_by_ssrf_protection": True,
                    "url": url,
                }

            # Check robots.txt if enabled
            if respect_robots_txt:
                allowed, reason = _is_allowed_by_robots(url)
                if not allowed:
                    return {
                        "error": f"Scraping blocked: {reason}",
                        "blocked_by_robots_txt": True,
                        "url": url,
                    }

            # Validate max_length
            if max_length < 1000:
                max_length = 1000
            elif max_length > 500000:
                max_length = 500000

            # Make request
            response = httpx.get(
                url,
                headers={
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
                timeout=30.0,
            )

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: Failed to fetch URL"}

            # Validate Content-Type to prevent parsing non-HTML content
            content_type = response.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ["text/html", "application/xhtml+xml"]):
                return {
                    "error": f"Skipping non-HTML content (Content-Type: {content_type})",
                    "url": url,
                    "skipped": True
                }

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove noise elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
                tag.decompose()

            # Get title and description
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Target content
            if selector:
                content_elem = soup.select_one(selector)
                if not content_elem:
                    return {"error": f"No elements found matching selector: {selector}"}
                text = content_elem.get_text(separator=" ", strip=True)
            else:
                # Auto-detect main content
                main_content = (
                    soup.find("article")
                    or soup.find("main")
                    or soup.find(attrs={"role": "main"})
                    or soup.find(class_=["content", "post", "entry", "article-body"])
                    or soup.find("body")
                )
                text = main_content.get_text(separator=" ", strip=True) if main_content else ""

            # Clean up whitespace
            text = " ".join(text.split())

            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "..."

            result: dict[str, Any] = {
                "url": str(response.url),
                "title": title,
                "description": description,
                "content": text,
                "length": len(text),
                "robots_txt_respected": respect_robots_txt,
            }

            # Extract links if requested
            if include_links:
                links: List[dict[str, str]] = []
                for a in soup.find_all("a", href=True)[:50]:
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if link_text and href:
                        links.append({"text": link_text, "href": href})
                result["links"] = links

            return result

        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Scraping failed: {str(e)}"}