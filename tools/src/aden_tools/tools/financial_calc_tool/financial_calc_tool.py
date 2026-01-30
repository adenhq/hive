"""
Financial Calculator Toolkit - Deterministic Financial Tools.

This toolkit provides high-precision mathematical models and live data fetching
for financial applications without using LLMs for core logic.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from .engines.currency_live import convert_currency, get_supported_currencies


def register_tools(mcp: FastMCP) -> None:
    """Register financial calculator tools with the MCP server."""

    @mcp.tool()
    async def financial_currency_convert(
        amount: float, from_currency: str = "USD", to_currency: str = "EUR", date: str = "latest"
    ) -> dict[str, Any]:
        """
        Convert an amount from one currency to another using live market data.

        Args:
            amount: The amount to convert (e.g., 100.50)
            from_currency: 3-letter ISO code to convert from (default: USD)
            to_currency: 3-letter ISO code to convert to (default: EUR)
            date: 'latest' or a date in 'YYYY-MM-DD' format for historical rates.

        Returns:
            Dict with conversion result, exchange rate, and source metadata.
        """
        # Input validation
        if amount < 0:
            return {"error": "Amount must be a non-negative number."}

        if len(from_currency) != 3 or len(to_currency) != 3:
            return {"error": "Currency codes must be 3-letter ISO codes (e.g., USD, EUR)."}

        return await convert_currency(amount, from_currency, to_currency, date)

    @mcp.tool()
    async def financial_supported_currencies() -> dict[str, Any]:
        """
        Get a list of all supported currency codes and their full names.

        Returns:
            Dict containing a map of currency codes to names.
        """
        return await get_supported_currencies()

    @mcp.tool()
    def financial_math_fv(
        rate: float, nper: int, pmt: float, pv: float = 0.0, when: str = "end"
    ) -> dict[str, Any]:
        """
        Calculate the Future Value (FV) of an investment.

        Args:
            rate: Interest rate per period (e.g., 0.05 for 5%)
            nper: Number of payment periods
            pmt: Payment made each period
            pv: Present value (default: 0.0)
            when: When payments are due: 'begin' (1) or 'end' (0) (default: 'end')

        Returns:
            Dict with the calculated future value.
        """
        try:
            # Deterministic TVM math
            # Formula: fv = -pv*(1+rate)**nper - pmt*(1+rate*when)/rate*((1+rate)**nper - 1)
            # where when=1 if begin, 0 if end

            p_when = 1 if when.lower() == "begin" else 0

            if rate == 0:
                result = -(pv + pmt * nper)
            else:
                term = (1 + rate) ** nper
                result = -(pv * term + pmt * (1 + rate * p_when) / rate * (term - 1))

            return {
                "success": True,
                "calculation": "Future Value",
                "result": round(float(result), 2),
                "params": {"rate": rate, "nper": nper, "pmt": pmt, "pv": pv, "when": when},
            }
        except Exception as e:
            return {"error": f"Math error in FV calculation: {str(e)}"}
