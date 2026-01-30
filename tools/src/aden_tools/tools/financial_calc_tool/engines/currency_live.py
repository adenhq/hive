"""
Live Currency Conversion Engine using the Frankfurter API.
Deterministic, non-LLM implementation for high-precision financial conversion.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Frankfurter API documentation: https://www.frankfurter.app/docs/
BASE_URL = "https://api.frankfurter.app"


async def convert_currency(
    amount: float | Decimal,
    from_currency: str = "USD",
    to_currency: str = "EUR",
    date: str = "latest",
) -> dict[str, Any]:
    """
    Fetch real-time or historical exchange rates and perform conversion.

    Args:
        amount: The numeric amount to convert.
        from_currency: 3-letter ISO currency code to convert from.
        to_currency: 3-letter ISO currency code to convert to.
        date: 'latest' or a date string in 'YYYY-MM-DD' format.

    Returns:
        Dict containing the conversion result, rate, and metadata.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    # Handle same-currency conversion immediately
    if from_currency == to_currency:
        return {
            "success": True,
            "amount": float(amount),
            "from": from_currency,
            "to": to_currency,
            "rate": 1.0,
            "result": float(amount),
            "date": "N/A",
            "provider": "identity",
        }

    try:
        # Construct URL
        url = f"{BASE_URL}/{date}"
        params = {"amount": float(amount), "from": from_currency, "to": to_currency}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 404:
                return {
                    "error": f"Invalid currency code or date: "
                    f"{from_currency}, {to_currency}, {date}"
                }

            response.raise_for_status()
            data = response.json()

            # The Frankfurter API returns:
            # { "amount": 10.0, "base": "USD", "date": "2024-05-21", "rates": { "EUR": 9.2 } }

            if "rates" not in data or to_currency not in data["rates"]:
                return {"error": f"Currency {to_currency} not found in exchange data."}

            rate = data["rates"][to_currency]
            # API already applied the amount if passed as param, but we recalculate
            # for transparency if needed, or just use their result.
            # Frankfurter returns the result directly in 'rates' when 'amount' is provided.
            result = data["rates"][to_currency]

            return {
                "success": True,
                "amount": float(amount),
                "from": from_currency,
                "to": to_currency,
                "rate": float(rate) / float(amount) if float(amount) != 0 else 0,
                "result": float(result),
                "date": data.get("date"),
                "provider": "Frankfurter API",
            }

    except httpx.HTTPStatusError as e:
        return {"error": f"API Error: {e.response.status_code} - {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Network Error tracking exchange rates: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error in currency conversion: {str(e)}"}


async def get_supported_currencies() -> dict[str, Any]:
    """Fetch the list of supported currencies from the API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/currencies")
            response.raise_for_status()
            return {"success": True, "currencies": response.json()}
    except Exception as e:
        return {"error": f"Failed to fetch supported currencies: {str(e)}"}
