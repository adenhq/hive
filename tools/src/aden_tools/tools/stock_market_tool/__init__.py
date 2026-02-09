"""
Stock Market Tool - Fetches real-time stock prices and company information.

This module provides MCP-compatible tools for accessing financial market data
using the Yahoo Finance API (yfinance library).

Tools:
    - stock_get_price: Get current stock price for a ticker
    - stock_get_company_info: Get company fundamentals for a ticker

Example:
    from aden_tools.tools.stock_market_tool import register_tools
    register_tools(mcp)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

from .handler import (
    CompanyInfo,
    InvalidTickerError,
    MarketDataError,
    StockMarketTool,
    StockMarketToolError,
    StockPrice,
)

# Module-level tool instance (lazy initialization)
_tool_instance: StockMarketTool | None = None


def _get_tool() -> StockMarketTool:
    """Get or create the singleton StockMarketTool instance."""
    global _tool_instance
    if _tool_instance is None:
        _tool_instance = StockMarketTool()
    return _tool_instance


def register_tools(mcp: FastMCP) -> None:
    """
    Register stock market tools with a FastMCP server.

    This function registers the following tools:
        - stock_get_price: Fetch current stock price and daily change
        - stock_get_company_info: Fetch company fundamentals

    Args:
        mcp: FastMCP server instance to register tools with.

    Example:
        from fastmcp import FastMCP
        from aden_tools.tools.stock_market_tool import register_tools

        mcp = FastMCP("my-server")
        register_tools(mcp)
    """

    @mcp.tool()
    def stock_get_price(ticker: str) -> dict:
        """
        Get the current stock price for a ticker symbol.

        Fetches real-time pricing data including current price, previous close,
        and daily change percentage. Supports stocks, ETFs, crypto (e.g., BTC-USD),
        and market indices.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "BTC-USD", "^GSPC")

        Returns:
            Dictionary containing:
                - ticker: The ticker symbol
                - current_price: Current trading price
                - currency: Price currency (e.g., "USD")
                - market_state: Current market state (REGULAR, PRE, POST, CLOSED)
                - previous_close: Previous day's closing price
                - day_change: Absolute price change today
                - day_change_percent: Percentage change today

        Examples:
            >>> stock_get_price("AAPL")
            {"ticker": "AAPL", "current_price": 178.50, "currency": "USD", ...}

            >>> stock_get_price("BTC-USD")
            {"ticker": "BTC-USD", "current_price": 42150.00, "currency": "USD", ...}
        """
        try:
            tool = _get_tool()
            return tool.get_price_dict(ticker)
        except InvalidTickerError as e:
            return {"error": str(e), "error_type": "invalid_ticker"}
        except MarketDataError as e:
            return {"error": str(e), "error_type": "market_data_error"}
        except Exception as e:
            return {"error": f"Unexpected error: {e!s}", "error_type": "unknown_error"}

    @mcp.tool()
    def stock_get_company_info(ticker: str) -> dict:
        """
        Get company fundamental information for a stock ticker.

        Fetches company details including name, sector, industry, market cap,
        and business description. Works best with equity tickers (not crypto).

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "GOOGL", "NVDA")

        Returns:
            Dictionary containing:
                - ticker: The ticker symbol
                - name: Full company name
                - sector: Business sector (e.g., "Technology")
                - industry: Specific industry classification
                - country: Country of headquarters
                - website: Company website URL
                - summary: Business description
                - market_cap: Market capitalization in currency units
                - employees: Number of full-time employees

        Examples:
            >>> stock_get_company_info("NVDA")
            {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", ...}

        Note:
            Crypto tickers (e.g., "BTC-USD") may not have company information.
            Use stock_get_price for crypto price data instead.
        """
        try:
            tool = _get_tool()
            return tool.get_company_dict(ticker)
        except InvalidTickerError as e:
            return {"error": str(e), "error_type": "invalid_ticker"}
        except MarketDataError as e:
            return {"error": str(e), "error_type": "market_data_error"}
        except Exception as e:
            return {"error": f"Unexpected error: {e!s}", "error_type": "unknown_error"}


__all__ = [
    "register_tools",
    "StockMarketTool",
    "StockPrice",
    "CompanyInfo",
    "StockMarketToolError",
    "InvalidTickerError",
    "MarketDataError",
]
