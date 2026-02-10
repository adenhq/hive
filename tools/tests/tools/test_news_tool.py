"""Tests for news tool with multi-provider support (FastMCP)."""

from datetime import date as real_date

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.news_tool import news_tool, register_tools


class DummyResponse:
    """Simple mock response for httpx.get."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


@pytest.fixture
def news_tools(mcp: FastMCP):
    """Register and return the news tool functions."""
    register_tools(mcp)
    return mcp._tool_manager._tools


class TestNewsSearch:
    """Tests for news_search tool."""

    def test_news_search_newsdata_success(self, news_tools, monkeypatch):
        """NewsData provider returns normalized results."""
        monkeypatch.setenv("NEWSDATA_API_KEY", "news-key")
        monkeypatch.delenv("FINLIGHT_API_KEY", raising=False)

        captured: dict = {}

        def mock_get(url: str, params=None, timeout=30.0, headers=None):
            captured["url"] = url
            captured["params"] = params or {}
            return DummyResponse(
                200,
                {
                    "results": [
                        {
                            "title": "Funding Round",
                            "source_id": "techcrunch",
                            "pubDate": "2026-02-01",
                            "link": "https://example.com/article",
                            "description": "A funding round was announced.",
                        }
                    ]
                },
            )

        monkeypatch.setattr(httpx, "get", mock_get)

        result = news_tools["news_search"].fn(query="funding")

        assert result["provider"] == "newsdata"
        assert result["query"] == "funding"
        assert result["total"] == 1
        assert captured["params"]["q"] == "funding"

    def test_news_search_falls_back_to_finlight(self, news_tools, monkeypatch):
        """Fallback to Finlight when NewsData returns an error."""
        monkeypatch.setenv("NEWSDATA_API_KEY", "news-key")
        monkeypatch.setenv("FINLIGHT_API_KEY", "finlight-key")

        def mock_get(url: str, params=None, timeout=30.0, headers=None):
            if "newsdata.io" in url:
                return DummyResponse(401, {})
            return DummyResponse(
                200,
                {
                    "data": [
                        {
                            "title": "Market Update",
                            "source": "finlight",
                            "published_at": "2026-02-02",
                            "url": "https://example.com/fin",
                            "summary": "Markets moved today.",
                        }
                    ]
                },
            )

        monkeypatch.setattr(httpx, "get", mock_get)

        result = news_tools["news_search"].fn(query="markets")

        assert result["provider"] == "finlight"
        assert result["total"] == 1


class TestNewsByCompany:
    """Tests for news_by_company tool."""

    def test_news_by_company_date_filter(self, news_tools, monkeypatch):
        """news_by_company builds date filters and quoted company query."""
        monkeypatch.setenv("NEWSDATA_API_KEY", "news-key")
        monkeypatch.delenv("FINLIGHT_API_KEY", raising=False)

        class FakeDate(real_date):
            @classmethod
            def today(cls) -> real_date:
                return real_date(2026, 2, 10)

        monkeypatch.setattr(news_tool, "date", FakeDate)

        captured: dict = {}

        def mock_get(url: str, params=None, timeout=30.0, headers=None):
            captured["params"] = params or {}
            return DummyResponse(200, {"results": []})

        monkeypatch.setattr(httpx, "get", mock_get)

        result = news_tools["news_by_company"].fn(company_name="Acme", days_back=7)

        assert result["provider"] == "newsdata"
        assert captured["params"]["from_date"] == "2026-02-03"
        assert captured["params"]["to_date"] == "2026-02-10"
        assert captured["params"]["q"] == '"Acme"'


class TestNewsSentiment:
    """Tests for news_sentiment tool."""

    def test_news_sentiment_requires_finlight(self, news_tools, monkeypatch):
        """news_sentiment returns error when Finlight key missing."""
        monkeypatch.delenv("FINLIGHT_API_KEY", raising=False)
        monkeypatch.delenv("NEWSDATA_API_KEY", raising=False)

        result = news_tools["news_sentiment"].fn(query="Acme")

        assert "error" in result
        assert "Finlight credentials not configured" in result["error"]



