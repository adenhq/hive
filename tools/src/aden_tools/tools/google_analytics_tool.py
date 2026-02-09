"""
Google Analytics Data API v1 tools.

Provides read-only access to Google Analytics 4 (GA4) data for website traffic
and marketing performance analysis.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from ..credentials import CredentialStoreAdapter

logger = logging.getLogger(__name__)


def register_google_analytics(
    mcp: FastMCP,
    credentials: Optional[CredentialStoreAdapter] = None,
) -> None:
    """
    Register Google Analytics tools.

    Args:
        mcp: FastMCP server instance.
        credentials: Optional credential store adapter.
    """

    def _get_client():
        """
        Initialize and return the Google Analytics Data API client.

        Returns:
            BetaAnalyticsDataClient instance.

        Raises:
            ValueError: If credentials are not configured.
        """
        # Check for credentials path
        creds_path = None
        if credentials:
            creds_path = credentials.get("google_analytics")

        if not creds_path:
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            raise ValueError(
                "Google Analytics credentials not found. "
                "Please set GOOGLE_APPLICATION_CREDENTIALS environment variable "
                "to the path of your service account JSON key file."
            )

        # Set the environment variable for the Google client library
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            return BetaAnalyticsDataClient()
        except ImportError:
            raise ImportError(
                "google-analytics-data package is required. "
                "Install with: pip install google-analytics-data"
            )

    def _format_report_response(response) -> Dict[str, Any]:
        """
        Format the API response into a readable dictionary.

        Args:
            response: RunReportResponse from the API.

        Returns:
            Dict with formatted data.
        """
        rows = []
        dimension_headers = [h.name for h in response.dimension_headers]
        metric_headers = [h.name for h in response.metric_headers]

        for row in response.rows:
            row_data = {}
            for i, dim in enumerate(row.dimension_values):
                row_data[dimension_headers[i]] = dim.value
            for i, met in enumerate(row.metric_values):
                row_data[metric_headers[i]] = met.value
            rows.append(row_data)

        return {
            "row_count": response.row_count,
            "dimensions": dimension_headers,
            "metrics": metric_headers,
            "rows": rows,
        }

    @mcp.tool()
    def ga_run_report(
        property_id: str,
        metrics: List[str],
        dimensions: Optional[List[str]] = None,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 100,
    ) -> str:
        """
        Run a custom Google Analytics 4 report.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456" or just "123456").
            metrics: Metrics to retrieve (e.g., ["sessions", "totalUsers", "conversions"]).
            dimensions: Dimensions to group by (e.g., ["pagePath", "sessionSource"]).
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo").
            end_date: End date (e.g., "today").
            limit: Max rows to return (1-10000).

        Returns:
            JSON string with report data or error message.
        """
        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            client = _get_client()

            # Normalize property_id
            if not property_id.startswith("properties/"):
                property_id = f"properties/{property_id}"

            # Build request
            request = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                metrics=[Metric(name=m) for m in metrics],
                limit=limit,
            )

            if dimensions:
                request.dimensions = [Dimension(name=d) for d in dimensions]

            response = client.run_report(request)
            result = _format_report_response(response)
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    def ga_get_realtime(
        property_id: str,
        metrics: Optional[List[str]] = None,
    ) -> str:
        """
        Get real-time analytics data (active users, current pages).

        Args:
            property_id: GA4 property ID (e.g., "properties/123456" or just "123456").
            metrics: Metrics to retrieve (default: ["activeUsers"]).

        Returns:
            JSON string with real-time data or error message.
        """
        try:
            from google.analytics.data_v1beta.types import (
                Metric,
                RunRealtimeReportRequest,
            )

            client = _get_client()

            if not property_id.startswith("properties/"):
                property_id = f"properties/{property_id}"

            if not metrics:
                metrics = ["activeUsers"]

            request = RunRealtimeReportRequest(
                property=property_id,
                metrics=[Metric(name=m) for m in metrics],
            )

            response = client.run_realtime_report(request)

            rows = []
            metric_headers = [h.name for h in response.metric_headers]
            for row in response.rows:
                row_data = {}
                for i, met in enumerate(row.metric_values):
                    row_data[metric_headers[i]] = met.value
                rows.append(row_data)

            result = {
                "row_count": response.row_count,
                "metrics": metric_headers,
                "rows": rows,
            }
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    def ga_get_top_pages(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 10,
    ) -> str:
        """
        Get top pages by views and engagement.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456" or just "123456").
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo").
            end_date: End date (e.g., "today").
            limit: Max rows to return.

        Returns:
            JSON string with top pages, their views, avg engagement time, and bounce rate.
        """
        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                OrderBy,
                RunReportRequest,
            )

            client = _get_client()

            if not property_id.startswith("properties/"):
                property_id = f"properties/{property_id}"

            request = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[
                    Dimension(name="pagePath"),
                    Dimension(name="pageTitle"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate"),
                ],
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                        desc=True,
                    )
                ],
                limit=limit,
            )

            response = client.run_report(request)
            result = _format_report_response(response)
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    def ga_get_traffic_sources(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 10,
    ) -> str:
        """
        Get traffic breakdown by source/medium.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456" or just "123456").
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo").
            end_date: End date (e.g., "today").
            limit: Max rows to return.

        Returns:
            JSON string with traffic sources, sessions, users, and conversions per source.
        """
        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                OrderBy,
                RunReportRequest,
            )

            client = _get_client()

            if not property_id.startswith("properties/"):
                property_id = f"properties/{property_id}"

            request = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="newUsers"),
                    Metric(name="conversions"),
                ],
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                        desc=True,
                    )
                ],
                limit=limit,
            )

            response = client.run_report(request)
            result = _format_report_response(response)
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
