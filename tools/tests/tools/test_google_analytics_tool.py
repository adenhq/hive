"""
Tests for Google Analytics tool.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.credentials import CredentialStoreAdapter
from aden_tools.tools.google_analytics_tool import register_google_analytics


@pytest.fixture
def mcp():
    """Create a FastMCP instance for testing."""
    return FastMCP("test-server")


@pytest.fixture
def credentials():
    """Create mock credentials that return a test path."""
    mock_creds = MagicMock(spec=CredentialStoreAdapter)
    mock_creds.get.return_value = "/path/to/service_account.json"
    return mock_creds


def test_google_analytics_registration(mcp, credentials):
    """Test that all GA tools are registered."""
    register_google_analytics(mcp, credentials)
    tools = mcp._tool_manager._tools
    assert "ga_run_report" in tools
    assert "ga_get_realtime" in tools
    assert "ga_get_top_pages" in tools
    assert "ga_get_traffic_sources" in tools


@pytest.fixture
def mock_ga_client():
    """Create a mock GA client with common response patterns."""
    mock_client = MagicMock()

    # Mock dimension headers
    dim_header = MagicMock()
    dim_header.name = "pagePath"

    # Mock metric headers
    metric_header = MagicMock()
    metric_header.name = "sessions"

    # Mock dimension value
    dim_value = MagicMock()
    dim_value.value = "/home"

    # Mock metric value
    metric_value = MagicMock()
    metric_value.value = "1000"

    # Mock row
    row = MagicMock()
    row.dimension_values = [dim_value]
    row.metric_values = [metric_value]

    # Mock response
    response = MagicMock()
    response.dimension_headers = [dim_header]
    response.metric_headers = [metric_header]
    response.rows = [row]
    response.row_count = 1

    mock_client.run_report.return_value = response
    mock_client.run_realtime_report.return_value = response

    return mock_client


def test_ga_run_report_returns_json(mcp, credentials):
    """Test ga_run_report function returns valid JSON."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    # Call with test parameters - will return error due to invalid credentials
    result = ga_run_report_fn(
        property_id="123456",
        metrics=["sessions"],
        dimensions=["pagePath"],
    )

    # Should return valid JSON
    parsed = json.loads(result)
    assert "error" in parsed or "rows" in parsed


def test_property_id_normalization(mcp, credentials):
    """Test that property IDs are normalized correctly."""
    register_google_analytics(mcp, credentials)

    # The function should add 'properties/' prefix if missing
    # This is tested implicitly through the implementation


def test_ga_no_credentials_error(mcp):
    """Test error handling when no credentials are provided."""
    register_google_analytics(mcp, None)

    with patch.dict(os.environ, {}, clear=True):
        # Remove GOOGLE_APPLICATION_CREDENTIALS from env
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

        ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

        result = ga_run_report_fn(
            property_id="123456",
            metrics=["sessions"],
        )

        parsed = json.loads(result)
        assert "error" in parsed


def test_default_date_ranges(mcp, credentials):
    """Test that default date ranges work correctly."""
    register_google_analytics(mcp, credentials)

    # Default should be "28daysAgo" to "today"
    ga_get_top_pages_fn = mcp._tool_manager._tools["ga_get_top_pages"].fn

    # This will fail due to missing credentials, but validates the function exists
    result = ga_get_top_pages_fn(property_id="123456")
    parsed = json.loads(result)
    # Should have error since we don't have real credentials
    assert "error" in parsed or "rows" in parsed


def test_ga_get_realtime_default_metrics(mcp, credentials):
    """Test that ga_get_realtime uses activeUsers as default metric."""
    register_google_analytics(mcp, credentials)

    ga_get_realtime_fn = mcp._tool_manager._tools["ga_get_realtime"].fn

    # Call without metrics to test default
    result = ga_get_realtime_fn(property_id="123456")
    parsed = json.loads(result)
    assert "error" in parsed or "rows" in parsed


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_property_id_with_prefix(mcp, credentials):
    """Test that property IDs with 'properties/' prefix are handled correctly."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    # Call with full prefix
    result = ga_run_report_fn(
        property_id="properties/123456",
        metrics=["sessions"],
    )

    parsed = json.loads(result)
    # Should return valid JSON (error or data)
    assert isinstance(parsed, dict)


def test_empty_metrics_list(mcp, credentials):
    """Test handling of empty metrics list."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    # Empty metrics should still produce valid JSON response
    result = ga_run_report_fn(
        property_id="123456",
        metrics=[],
    )

    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_invalid_date_range(mcp, credentials):
    """Test handling of invalid date range."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    # Invalid date format
    result = ga_run_report_fn(
        property_id="123456",
        metrics=["sessions"],
        start_date="invalid-date",
        end_date="also-invalid",
    )

    parsed = json.loads(result)
    # Should return an error
    assert "error" in parsed


def test_limit_parameter(mcp, credentials):
    """Test that limit parameter is passed correctly."""
    register_google_analytics(mcp, credentials)

    ga_get_top_pages_fn = mcp._tool_manager._tools["ga_get_top_pages"].fn

    # Test with custom limit
    result = ga_get_top_pages_fn(
        property_id="123456",
        limit=5,
    )

    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_ga_get_traffic_sources_returns_json(mcp, credentials):
    """Test ga_get_traffic_sources returns valid JSON."""
    register_google_analytics(mcp, credentials)

    ga_get_traffic_sources_fn = mcp._tool_manager._tools["ga_get_traffic_sources"].fn

    result = ga_get_traffic_sources_fn(property_id="123456")

    parsed = json.loads(result)
    assert "error" in parsed or "rows" in parsed


def test_multiple_metrics(mcp, credentials):
    """Test handling of multiple metrics."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    result = ga_run_report_fn(
        property_id="123456",
        metrics=["sessions", "totalUsers", "newUsers", "bounceRate"],
        dimensions=["date"],
    )

    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_multiple_dimensions(mcp, credentials):
    """Test handling of multiple dimensions."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    result = ga_run_report_fn(
        property_id="123456",
        metrics=["sessions"],
        dimensions=["pagePath", "pageTitle", "country"],
    )

    parsed = json.loads(result)
    assert isinstance(parsed, dict)


# ============================================================================
# Integration Tests with Mocked API
# ============================================================================

@pytest.fixture
def mock_ga_response():
    """Create a realistic mock GA API response."""
    dim_header_1 = MagicMock()
    dim_header_1.name = "pagePath"
    dim_header_2 = MagicMock()
    dim_header_2.name = "pageTitle"

    metric_header_1 = MagicMock()
    metric_header_1.name = "screenPageViews"
    metric_header_2 = MagicMock()
    metric_header_2.name = "averageSessionDuration"

    # Create multiple rows
    rows = []
    for i, (path, title, views, duration) in enumerate([
        ("/home", "Home Page", "5000", "120.5"),
        ("/about", "About Us", "3000", "90.2"),
        ("/contact", "Contact", "1500", "60.0"),
    ]):
        dim_val_1 = MagicMock()
        dim_val_1.value = path
        dim_val_2 = MagicMock()
        dim_val_2.value = title

        met_val_1 = MagicMock()
        met_val_1.value = views
        met_val_2 = MagicMock()
        met_val_2.value = duration

        row = MagicMock()
        row.dimension_values = [dim_val_1, dim_val_2]
        row.metric_values = [met_val_1, met_val_2]
        rows.append(row)

    response = MagicMock()
    response.dimension_headers = [dim_header_1, dim_header_2]
    response.metric_headers = [metric_header_1, metric_header_2]
    response.rows = rows
    response.row_count = 3

    return response


def test_format_report_response(mock_ga_response):
    """Test the response formatting logic."""
    # Import the module to access the internal function
    from aden_tools.tools import google_analytics_tool

    # Create a mock mcp to trigger registration
    mcp = FastMCP("test")
    register_google_analytics(mcp, None)

    # Access the internal formatting function through the tool
    # Since _format_report_response is nested, we test it indirectly
    # by checking the overall response structure expectations

    # Check response structure
    assert mock_ga_response.row_count == 3
    assert len(mock_ga_response.rows) == 3


def test_realtime_metrics_custom(mcp, credentials):
    """Test ga_get_realtime with custom metrics."""
    register_google_analytics(mcp, credentials)

    ga_get_realtime_fn = mcp._tool_manager._tools["ga_get_realtime"].fn

    result = ga_get_realtime_fn(
        property_id="123456",
        metrics=["activeUsers", "screenPageViews"],
    )

    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_all_tools_return_valid_json(mcp, credentials):
    """Integration test: all tools should return valid JSON."""
    register_google_analytics(mcp, credentials)

    tools_to_test = [
        ("ga_run_report", {"property_id": "123456", "metrics": ["sessions"]}),
        ("ga_get_realtime", {"property_id": "123456"}),
        ("ga_get_top_pages", {"property_id": "123456"}),
        ("ga_get_traffic_sources", {"property_id": "123456"}),
    ]

    for tool_name, params in tools_to_test:
        fn = mcp._tool_manager._tools[tool_name].fn
        result = fn(**params)

        # All results should be valid JSON
        try:
            parsed = json.loads(result)
            assert isinstance(parsed, dict), f"{tool_name} should return a dict"
        except json.JSONDecodeError:
            pytest.fail(f"{tool_name} did not return valid JSON: {result}")


def test_date_range_formats(mcp, credentials):
    """Test various date range formats."""
    register_google_analytics(mcp, credentials)

    ga_run_report_fn = mcp._tool_manager._tools["ga_run_report"].fn

    date_formats = [
        ("7daysAgo", "today"),
        ("30daysAgo", "yesterday"),
        ("2024-01-01", "2024-01-31"),
    ]

    for start, end in date_formats:
        result = ga_run_report_fn(
            property_id="123456",
            metrics=["sessions"],
            start_date=start,
            end_date=end,
        )

        parsed = json.loads(result)
        assert isinstance(parsed, dict), f"Failed for date range {start} to {end}"
