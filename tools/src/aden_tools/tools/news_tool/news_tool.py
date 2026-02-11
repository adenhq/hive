"""
News Tool - Search news using multiple providers.

Supports:
- NewsData.io (NEWSDATA_API_KEY)
- Finlight.me (FINLIGHT_API_KEY) for sentiment and optional fallback

Auto-detection: Tries NewsData first, then Finlight.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import TYPE_CHECKING

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

NEWSDATA_URL = "https://newsdata.io/api/1/news"
FINLIGHT_URL = "https://api.finlight.me/v1/news"


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register news tools with the MCP server."""

    def _get_credentials() -> dict[str, str | None]:
        """Get available news credentials."""
        if credentials is not None:
            return {
                "newsdata_api_key": credentials.get("newsdata"),
                "finlight_api_key": credentials.get("finlight"),
            }
        return {
            "newsdata_api_key": os.getenv("NEWSDATA_API_KEY"),
            "finlight_api_key": os.getenv("FINLIGHT_API_KEY"),
        }

    def _normalize_limit(limit: int | None, default: int = 10) -> int:
        """Normalize limit to a positive integer."""
        if limit is None:
            return default
        return max(limit, 1)

    def _clean_params(params: dict[str, str | int | None]) -> dict[str, str | int]:
        """Remove None/empty values from request params."""
        return {key: value for key, value in params.items() if value not in (None, "")}

    def _build_date_range(days_back: int) -> tuple[str, str]:
        """Build from/to date strings for the past N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        return start_date.isoformat(), end_date.isoformat()

    def _newsdata_error(response: httpx.Response) -> dict:
        """Map NewsData API errors to friendly messages."""
        if response.status_code == 401:
            return {"error": "Invalid NewsData API key"}
        if response.status_code == 429:
            return {"error": "NewsData rate limit exceeded. Try again later."}
        if response.status_code == 422:
            return {"error": "Invalid NewsData parameters"}
        return {"error": f"NewsData request failed: HTTP {response.status_code}"}

    def _finlight_error(response: httpx.Response) -> dict:
        """Map Finlight API errors to friendly messages."""
        if response.status_code == 401:
            return {"error": "Invalid Finlight API key"}
        if response.status_code == 429:
            return {"error": "Finlight rate limit exceeded. Try again later."}
        if response.status_code == 422:
            return {"error": "Invalid Finlight parameters"}
        return {"error": f"Finlight request failed: HTTP {response.status_code}"}

    def _format_article(
        title: str,
        source: str,
        published_at: str,
        url: str,
        snippet: str,
        sentiment: str | float | None = None,
    ) -> dict:
        """Normalize an article payload."""
        payload = {
            "title": title,
            "source": source,
            "date": published_at,
            "url": url,
            "snippet": snippet,
        }
        if sentiment is not None:
            payload["sentiment"] = sentiment
        return payload

    def _parse_newsdata_results(data: dict) -> list[dict]:
        """Parse NewsData results into normalized articles."""
        raw_results = data.get("results") or []
        return [
            _format_article(
                title=item.get("title", ""),
                source=item.get("source_id", ""),
                published_at=item.get("pubDate", ""),
                url=item.get("link", ""),
                snippet=item.get("description", ""),
            )
            for item in raw_results
        ]

    def _parse_finlight_results(
        data: dict,
        include_sentiment: bool = False,
    ) -> list[dict]:
        """Parse Finlight results into normalized articles."""
        raw_results = data.get("data") or data.get("results") or []
        results = []
        for item in raw_results:
            sentiment_value = None
            if include_sentiment:
                sentiment_value = item.get("sentiment") or item.get("sentiment_score")
            results.append(
                _format_article(
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    published_at=item.get("published_at", ""),
                    url=item.get("url", ""),
                    snippet=item.get("summary", "") or item.get("description", ""),
                    sentiment=sentiment_value,
                )
            )
        return results

    def _search_newsdata(
        query: str | None,
        from_date: str | None,
        to_date: str | None,
        language: str | None,
        limit: int,
        sources: str | None,
        category: str | None,
        country: str | None,
        api_key: str,
    ) -> dict:
        """Search NewsData API."""
        params = _clean_params(
            {
                "apikey": api_key,
                "q": query,
                "from_date": from_date,
                "to_date": to_date,
                "language": language,
                "category": category,
                "country": country,
                "size": limit,
            }
        )
        if sources:
            params["sources"] = sources

        response = httpx.get(NEWSDATA_URL, params=params, timeout=30.0)
        if response.status_code != 200:
            return _newsdata_error(response)

        data = response.json()
        results = _parse_newsdata_results(data)
        return {
            "results": results,
            "total": len(results),
            "provider": "newsdata",
        }

    def _search_finlight(
        query: str | None,
        from_date: str | None,
        to_date: str | None,
        language: str | None,
        limit: int,
        sources: str | None,
        category: str | None,
        country: str | None,
        api_key: str,
        include_sentiment: bool = False,
    ) -> dict:
        """Search Finlight API."""
        params = _clean_params(
            {
                "query": query,
                "from_date": from_date,
                "to_date": to_date,
                "language": language,
                "category": category,
                "country": country,
                "limit": limit,
            }
        )
        if sources:
            params["sources"] = sources

        response = httpx.get(
            FINLIGHT_URL,
            params=params,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        if response.status_code != 200:
            return _finlight_error(response)

        data = response.json()
        results = _parse_finlight_results(data, include_sentiment=include_sentiment)
        return {
            "results": results,
            "total": len(results),
            "provider": "finlight",
        }

    def _run_with_fallback(primary: dict, fallback: dict | None) -> dict:
        """Return primary result or fallback if primary errors."""
        if "error" not in primary:
            return primary
        if fallback is None or "error" in fallback:
            if fallback is None:
                return primary
            return {
                "error": "All providers failed",
                "providers": {"primary": primary, "fallback": fallback},
            }
        return fallback

    @mcp.tool()
    def news_search(
        query: str,
        from_date: str | None = None,
        to_date: str | None = None,
        language: str | None = "en",
        limit: int | None = 10,
        sources: str | None = None,
        category: str | None = None,
        country: str | None = None,
    ) -> dict:
        """
        Search news articles with filters.

        Args:
            query: Search query
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Language code (e.g., en)
            limit: Max number of results
            sources: Optional sources filter
            category: Optional category filter
            country: Optional country filter

        Returns:
            Dict with list of articles and provider metadata.
        """
        if not query:
            return {"error": "Query is required"}

        creds = _get_credentials()
        newsdata_key = creds["newsdata_api_key"]
        finlight_key = creds["finlight_api_key"]
        if not newsdata_key and not finlight_key:
            return {
                "error": "No news credentials configured",
                "help": "Set NEWSDATA_API_KEY or FINLIGHT_API_KEY environment variable",
            }

        limit_value = _normalize_limit(limit)

        try:
            primary = (
                _search_newsdata(
                    query=query,
                    from_date=from_date,
                    to_date=to_date,
                    language=language,
                    limit=limit_value,
                    sources=sources,
                    category=category,
                    country=country,
                    api_key=newsdata_key,
                )
                if newsdata_key
                else {"error": "NewsData credentials not configured"}
            )
            fallback = (
                _search_finlight(
                    query=query,
                    from_date=from_date,
                    to_date=to_date,
                    language=language,
                    limit=limit_value,
                    sources=sources,
                    category=category,
                    country=country,
                    api_key=finlight_key,
                )
                if finlight_key
                else None
            )
            result = _run_with_fallback(primary, fallback)
            result["query"] = query
            return result
        except httpx.TimeoutException:
            return {"error": "News search request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        except Exception as e:
            return {"error": f"News search failed: {e}"}

    @mcp.tool()
    def news_headlines(
        category: str,
        country: str,
        limit: int | None = 10,
    ) -> dict:
        """
        Get top news headlines by category and country.

        Args:
            category: Category (business, tech, finance, etc.)
            country: Country code (us, uk, etc.)
            limit: Max number of results

        Returns:
            Dict with list of headline articles and provider metadata.
        """
        if not category:
            return {"error": "Category is required"}
        if not country:
            return {"error": "Country is required"}

        creds = _get_credentials()
        newsdata_key = creds["newsdata_api_key"]
        finlight_key = creds["finlight_api_key"]
        if not newsdata_key and not finlight_key:
            return {
                "error": "No news credentials configured",
                "help": "Set NEWSDATA_API_KEY or FINLIGHT_API_KEY environment variable",
            }

        limit_value = _normalize_limit(limit)

        try:
            primary = (
                _search_newsdata(
                    query=None,
                    from_date=None,
                    to_date=None,
                    language=None,
                    limit=limit_value,
                    sources=None,
                    category=category,
                    country=country,
                    api_key=newsdata_key,
                )
                if newsdata_key
                else {"error": "NewsData credentials not configured"}
            )
            fallback = (
                _search_finlight(
                    query=None,
                    from_date=None,
                    to_date=None,
                    language=None,
                    limit=limit_value,
                    sources=None,
                    category=category,
                    country=country,
                    api_key=finlight_key,
                )
                if finlight_key
                else None
            )
            result = _run_with_fallback(primary, fallback)
            result["category"] = category
            result["country"] = country
            return result
        except httpx.TimeoutException:
            return {"error": "News headline request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        except Exception as e:
            return {"error": f"News headlines failed: {e}"}

    @mcp.tool()
    def news_by_company(
        company_name: str,
        days_back: int = 7,
        limit: int | None = 10,
        language: str | None = "en",
    ) -> dict:
        """
        Get news mentioning a specific company.

        Args:
            company_name: Company name to search for
            days_back: Days to look back (default 7)
            limit: Max number of results
            language: Language code (e.g., en)

        Returns:
            Dict with list of articles and provider metadata.
        """
        if not company_name:
            return {"error": "Company name is required"}
        if days_back < 0:
            return {"error": "days_back must be 0 or greater"}

        from_date, to_date = _build_date_range(days_back)

        creds = _get_credentials()
        newsdata_key = creds["newsdata_api_key"]
        finlight_key = creds["finlight_api_key"]
        if not newsdata_key and not finlight_key:
            return {
                "error": "No news credentials configured",
                "help": "Set NEWSDATA_API_KEY or FINLIGHT_API_KEY environment variable",
            }

        limit_value = _normalize_limit(limit)
        query = f'"{company_name}"'

        try:
            primary = (
                _search_newsdata(
                    query=query,
                    from_date=from_date,
                    to_date=to_date,
                    language=language,
                    limit=limit_value,
                    sources=None,
                    category=None,
                    country=None,
                    api_key=newsdata_key,
                )
                if newsdata_key
                else {"error": "NewsData credentials not configured"}
            )
            fallback = (
                _search_finlight(
                    query=query,
                    from_date=from_date,
                    to_date=to_date,
                    language=language,
                    limit=limit_value,
                    sources=None,
                    category=None,
                    country=None,
                    api_key=finlight_key,
                )
                if finlight_key
                else None
            )
            result = _run_with_fallback(primary, fallback)
            result["company_name"] = company_name
            result["days_back"] = days_back
            return result
        except httpx.TimeoutException:
            return {"error": "Company news request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        except Exception as e:
            return {"error": f"Company news failed: {e}"}

    @mcp.tool()
    def news_sentiment(
        query: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict:
        """
        Get news with sentiment analysis (Finlight provider).

        Args:
            query: Search query
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            Dict with list of sentiment-scored articles.
        """
        if not query:
            return {"error": "Query is required"}

        creds = _get_credentials()
        finlight_key = creds["finlight_api_key"]
        if not finlight_key:
            return {
                "error": "Finlight credentials not configured",
                "help": "Set FINLIGHT_API_KEY environment variable",
            }

        try:
            result = _search_finlight(
                query=query,
                from_date=from_date,
                to_date=to_date,
                language=None,
                limit=_normalize_limit(None),
                sources=None,
                category=None,
                country=None,
                api_key=finlight_key,
                include_sentiment=True,
            )
            result["query"] = query
            return result
        except httpx.TimeoutException:
            return {"error": "News sentiment request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        except Exception as e:
            return {"error": f"News sentiment failed: {e}"}
