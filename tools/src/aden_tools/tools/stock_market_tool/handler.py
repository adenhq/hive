"""
Stock Market Tool - Fetches real-time stock prices and company information.

This tool enables Hive agents to access financial market data using the yfinance library.
It provides stock quotes, company fundamentals, and market data for business automation.

Example Usage:
    tool = StockMarketTool()
    price = tool.get_stock_price("AAPL")
    info = tool.get_company_info("MSFT")

Author: sohaibsattar0016 (Contributor)
License: Apache-2.0
"""

from dataclasses import dataclass
from typing import Any

import yfinance as yf


@dataclass
class StockPrice:
    """Represents a stock price quote with metadata."""

    ticker: str
    current_price: float
    currency: str
    market_state: str  # "REGULAR", "PRE", "POST", "CLOSED"
    previous_close: float
    day_change: float
    day_change_percent: float


@dataclass
class CompanyInfo:
    """Represents company fundamental information."""

    ticker: str
    name: str
    sector: str
    industry: str
    country: str
    website: str
    summary: str
    market_cap: int
    employees: int


class StockMarketToolError(Exception):
    """Base exception for StockMarketTool errors."""

    pass


class InvalidTickerError(StockMarketToolError):
    """Raised when a ticker symbol is invalid or not found."""

    pass


class MarketDataError(StockMarketToolError):
    """Raised when market data cannot be fetched."""

    pass


class StockMarketTool:
    """
    A tool for fetching stock market data using Yahoo Finance.

    This tool provides real-time stock prices, company information, and market data.
    It is designed to be used by Hive agents for business automation tasks involving
    financial data.

    Attributes:
        timeout (int): Request timeout in seconds. Default is 10.

    Example:
        >>> tool = StockMarketTool()
        >>> price = tool.get_stock_price("AAPL")
        >>> print(f"Apple stock: ${price.current_price}")
        Apple stock: $178.50

        >>> info = tool.get_company_info("MSFT")
        >>> print(f"Company: {info.name}, Sector: {info.sector}")
        Company: Microsoft Corporation, Sector: Technology
    """

    def __init__(self, timeout: int = 10) -> None:
        """
        Initialize the StockMarketTool.

        Args:
            timeout: Request timeout in seconds. Default is 10.
        """
        self.timeout = timeout

    def get_stock_price(self, ticker: str) -> StockPrice:
        """
        Fetch the current stock price for a given ticker symbol.

        This method retrieves real-time pricing data including current price,
        previous close, and daily change information.

        Args:
            ticker: The stock ticker symbol (e.g., "AAPL", "MSFT", "BTC-USD").
                    Supports stocks, ETFs, crypto, and indices.

        Returns:
            StockPrice: A dataclass containing price information:
                - ticker: The ticker symbol
                - current_price: Current trading price
                - currency: Price currency (e.g., "USD")
                - market_state: Current market state
                - previous_close: Previous day's closing price
                - day_change: Absolute price change today
                - day_change_percent: Percentage change today

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            MarketDataError: If market data cannot be retrieved.

        Example:
            >>> tool = StockMarketTool()
            >>> price = tool.get_stock_price("AAPL")
            >>> print(f"${price.current_price} ({price.day_change_percent:+.2f}%)")
        """
        ticker = ticker.strip().upper()

        if not ticker:
            raise InvalidTickerError("Ticker symbol cannot be empty")

        try:
            stock = yf.Ticker(ticker)

            # Try fast_info first (more reliable for crypto)
            try:
                fast_info = stock.fast_info
                current_price = float(fast_info.last_price) if fast_info.last_price else None
                previous_close = (
                    float(fast_info.previous_close) if fast_info.previous_close else None
                )
                currency = str(fast_info.currency) if fast_info.currency else "USD"
            except Exception:
                current_price = None
                previous_close = None
                currency = "USD"

            # Fallback to full info if fast_info failed
            market_state = "UNKNOWN"
            if current_price is None:
                try:
                    info = stock.info
                    if info and info.get("regularMarketPrice") is not None:
                        current_price = float(info.get("regularMarketPrice", 0))
                        previous_close = float(info.get("previousClose", current_price))
                        currency = str(info.get("currency", "USD"))
                        market_state = str(info.get("marketState", "UNKNOWN"))
                except Exception:
                    pass
            else:
                try:
                    info = stock.info
                    if info:
                        market_state = str(info.get("marketState", "UNKNOWN"))
                except Exception:
                    pass

            if current_price is None:
                raise InvalidTickerError(f"Ticker '{ticker}' not found or has no market data")

            if previous_close is None:
                previous_close = current_price

            day_change = current_price - previous_close
            day_change_percent = (day_change / previous_close * 100) if previous_close != 0 else 0.0

            return StockPrice(
                ticker=ticker,
                current_price=round(current_price, 2),
                currency=currency,
                market_state=market_state,
                previous_close=round(previous_close, 2),
                day_change=round(day_change, 2),
                day_change_percent=round(day_change_percent, 2),
            )

        except InvalidTickerError:
            raise
        except Exception as e:
            raise MarketDataError(f"Failed to fetch price for '{ticker}': {e!s}") from e

    def get_company_info(self, ticker: str) -> CompanyInfo:
        """
        Fetch company fundamental information for a given ticker symbol.

        This method retrieves company details including name, sector, industry,
        and a business summary. Best used with stock tickers (not crypto).

        Args:
            ticker: The stock ticker symbol (e.g., "AAPL", "MSFT", "GOOGL").
                    Works best with equity tickers, not crypto or indices.

        Returns:
            CompanyInfo: A dataclass containing company information:
                - ticker: The ticker symbol
                - name: Full company name
                - sector: Business sector (e.g., "Technology")
                - industry: Specific industry
                - country: Country of headquarters
                - website: Company website URL
                - summary: Business description
                - market_cap: Market capitalization in currency units
                - employees: Number of full-time employees

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            MarketDataError: If company data cannot be retrieved.

        Example:
            >>> tool = StockMarketTool()
            >>> info = tool.get_company_info("NVDA")
            >>> print(f"{info.name} ({info.sector})")
            >>> print(f"Market Cap: ${info.market_cap:,}")
        """
        ticker = ticker.strip().upper()

        if not ticker:
            raise InvalidTickerError("Ticker symbol cannot be empty")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or not info.get("shortName"):
                raise InvalidTickerError(
                    f"Ticker '{ticker}' not found or has no company data. "
                    "Note: Crypto tickers may not have company information."
                )

            return CompanyInfo(
                ticker=ticker,
                name=str(info.get("shortName", info.get("longName", "Unknown"))),
                sector=str(info.get("sector", "N/A")),
                industry=str(info.get("industry", "N/A")),
                country=str(info.get("country", "N/A")),
                website=str(info.get("website", "N/A")),
                summary=str(info.get("longBusinessSummary", "No description available")),
                market_cap=int(info.get("marketCap", 0)),
                employees=int(info.get("fullTimeEmployees", 0)),
            )

        except InvalidTickerError:
            raise
        except Exception as e:
            raise MarketDataError(f"Failed to fetch company info for '{ticker}': {e!s}") from e

    def get_price_dict(self, ticker: str) -> dict[str, Any]:
        """
        Get stock price as a dictionary (for MCP tool serialization).

        Args:
            ticker: The stock ticker symbol.

        Returns:
            Dictionary representation of the stock price.
        """
        price = self.get_stock_price(ticker)
        return {
            "ticker": price.ticker,
            "current_price": price.current_price,
            "currency": price.currency,
            "market_state": price.market_state,
            "previous_close": price.previous_close,
            "day_change": price.day_change,
            "day_change_percent": price.day_change_percent,
        }

    def get_company_dict(self, ticker: str) -> dict[str, Any]:
        """
        Get company info as a dictionary (for MCP tool serialization).

        Args:
            ticker: The stock ticker symbol.

        Returns:
            Dictionary representation of the company info.
        """
        info = self.get_company_info(ticker)
        return {
            "ticker": info.ticker,
            "name": info.name,
            "sector": info.sector,
            "industry": info.industry,
            "country": info.country,
            "website": info.website,
            "summary": info.summary,
            "market_cap": info.market_cap,
            "employees": info.employees,
        }
