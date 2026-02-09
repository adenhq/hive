#!/usr/bin/env python3
"""
Stock Market Tool - Verification Script

This script tests the StockMarketTool to verify it works correctly.
Run with: uv run python test_stock.py

Expected output:
- AAPL stock price and company info
- BTC-USD crypto price
- Error handling for invalid ticker
"""

import sys
from pathlib import Path

# Add the tools/src to the path so we can import aden_tools
tools_src = Path(__file__).parent / "tools" / "src"
sys.path.insert(0, str(tools_src))

from aden_tools.tools.stock_market_tool.handler import (
    StockMarketTool,
    InvalidTickerError,
    MarketDataError,
)


def test_stock_price():
    """Test fetching stock prices."""
    print("=" * 60)
    print("TEST 1: Stock Price Fetching")
    print("=" * 60)

    tool = StockMarketTool()

    # Test AAPL (Apple)
    print("\n📈 Fetching AAPL (Apple Inc.)...")
    try:
        price = tool.get_stock_price("AAPL")
        print(f"   Ticker: {price.ticker}")
        print(f"   Current Price: ${price.current_price} {price.currency}")
        print(f"   Previous Close: ${price.previous_close}")
        print(f"   Day Change: ${price.day_change} ({price.day_change_percent:+.2f}%)")
        print(f"   Market State: {price.market_state}")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    # Test BTC-USD (Bitcoin)
    print("\n🪙 Fetching BTC-USD (Bitcoin)...")
    try:
        price = tool.get_stock_price("BTC-USD")
        print(f"   Ticker: {price.ticker}")
        print(f"   Current Price: ${price.current_price:,.2f} {price.currency}")
        print(f"   Previous Close: ${price.previous_close:,.2f}")
        print(f"   Day Change: ${price.day_change:,.2f} ({price.day_change_percent:+.2f}%)")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    return True


def test_company_info():
    """Test fetching company information."""
    print("\n" + "=" * 60)
    print("TEST 2: Company Info Fetching")
    print("=" * 60)

    tool = StockMarketTool()

    # Test MSFT (Microsoft)
    print("\n🏢 Fetching MSFT (Microsoft Corporation)...")
    try:
        info = tool.get_company_info("MSFT")
        print(f"   Ticker: {info.ticker}")
        print(f"   Name: {info.name}")
        print(f"   Sector: {info.sector}")
        print(f"   Industry: {info.industry}")
        print(f"   Country: {info.country}")
        print(f"   Website: {info.website}")
        print(f"   Market Cap: ${info.market_cap:,}")
        print(f"   Employees: {info.employees:,}")
        print(f"   Summary: {info.summary[:100]}...")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    return True


def test_error_handling():
    """Test error handling for invalid tickers."""
    print("\n" + "=" * 60)
    print("TEST 3: Error Handling")
    print("=" * 60)

    tool = StockMarketTool()

    # Test invalid ticker
    print("\n⚠️ Testing invalid ticker 'INVALIDTICKER123'...")
    try:
        tool.get_stock_price("INVALIDTICKER123")
        print("   ❌ FAILED: Expected an error but got a result")
        return False
    except InvalidTickerError as e:
        print(f"   Caught expected error: {e}")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ❌ FAILED: Got unexpected error type: {type(e).__name__}: {e}")
        return False

    # Test empty ticker
    print("\n⚠️ Testing empty ticker ''...")
    try:
        tool.get_stock_price("")
        print("   ❌ FAILED: Expected an error but got a result")
        return False
    except InvalidTickerError as e:
        print(f"   Caught expected error: {e}")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ❌ FAILED: Got unexpected error type: {type(e).__name__}: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("\n" + "🧪 " + "=" * 56 + " 🧪")
    print("       STOCK MARKET TOOL - VERIFICATION TESTS")
    print("🧪 " + "=" * 56 + " 🧪\n")

    all_passed = True

    if not test_stock_price():
        all_passed = False

    if not test_company_info():
        all_passed = False

    if not test_error_handling():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The Stock Market Tool is working correctly.")
    else:
        print("❌ SOME TESTS FAILED. Please check the output above.")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
