import pytest
from fastmcp import FastMCP
from aden_tools.tools.financial_calc_tool import register_tools


@pytest.fixture
def mcp():
    server = FastMCP("test")
    register_tools(server)
    return server


@pytest.mark.asyncio
async def test_financial_math_fv(mcp):
    """Test Future Value calculation."""
    # FV(rate=0.05, nper=10, pmt=-100, pv=-1000)
    # Rate 5%, 10 periods, $100 payment, $1000 initial
    tool_fn = mcp._tool_manager._tools["financial_math_fv"].fn
    result = tool_fn(rate=0.05, nper=10, pmt=-100, pv=-1000)

    assert result["success"] is True
    # Formula: 1000 * (1.05^10) + 100 * ((1.05^10 - 1) / 0.05)
    # 1.05^10 is ~1.62889
    # 1000 * 1.62889 = 1628.89
    # 100 * (0.62889 / 0.05) = 100 * 12.5778 = 1257.78
    # Total = 1628.89 + 1257.78 = 2886.67
    assert result["result"] == 2886.68  # Rounding might differ slightly


@pytest.mark.asyncio
async def test_financial_currency_convert_simple(mcp):
    """Test same-currency conversion (deterministic)."""
    tool_fn = mcp._tool_manager._tools["financial_currency_convert"].fn
    result = await tool_fn(amount=100.0, from_currency="USD", to_currency="USD")

    assert result["success"] is True
    assert result["result"] == 100.0
    assert result["rate"] == 1.0
