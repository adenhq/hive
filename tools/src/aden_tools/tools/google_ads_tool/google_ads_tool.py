"""
Google Ads Tool - Campaign monitoring and management.

Provides three MCP tools for interacting with Google Ads API:
- ads_get_campaign_metrics: Retrieve campaign performance metrics
- ads_list_campaigns: List active campaigns
- ads_pause_campaign: Pause an active campaign

All endpoints use OAuth2 authentication via Google Ads API credentials.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from fastmcp import FastMCP
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

_MISSING_CREDENTIALS_ERROR = {
    "error": "Google Ads credentials not configured",
    "help": (
        "Set the following environment variables:\n"
        "- GOOGLE_ADS_DEVELOPER_TOKEN\n"
        "- GOOGLE_ADS_CLIENT_ID\n"
        "- GOOGLE_ADS_CLIENT_SECRET\n"
        "- GOOGLE_ADS_REFRESH_TOKEN\n"
        "Get credentials at https://developers.google.com/google-ads/api/docs/get-started"
    ),
}


class _GoogleAdsClientWrapper:
    """Internal wrapper for Google Ads API client."""

    def __init__(
        self,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        """Initialize Google Ads client with OAuth2 credentials.

        Args:
            developer_token: Google Ads API developer token
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            refresh_token: OAuth2 refresh token
        """
        self._credentials = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        }
        self._client = GoogleAdsClient.load_from_dict(self._credentials)

    def get_service(self, service_name: str):
        """Get a Google Ads API service.

        Args:
            service_name: Name of the service (e.g., 'GoogleAdsService')

        Returns:
            Service instance
        """
        return self._client.get_service(service_name)

    def get_campaign_metrics(
        self,
        customer_id: str,
        date_range: Literal["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"],
    ) -> dict:
        """Retrieve campaign performance metrics.

        Args:
            customer_id: Google Ads customer ID (without hyphens)
            date_range: Date range for metrics

        Returns:
            Dict with campaign metrics including impressions, clicks, cost, CTR, and conversions
        """
        try:
            ga_service = self.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.ctr,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.average_cpc
                FROM campaign
                WHERE segments.date DURING {date_range}
                ORDER BY metrics.impressions DESC
            """

            # Remove hyphens from customer ID
            customer_id_clean = customer_id.replace("-", "")

            response = ga_service.search(customer_id=customer_id_clean, query=query)

            campaigns = []
            for row in response:
                campaign = row.campaign
                metrics = row.metrics

                # Convert cost from micros to currency
                cost = metrics.cost_micros / 1_000_000 if metrics.cost_micros else 0

                # Calculate ROAS if conversions_value exists
                roas = (
                    (metrics.conversions_value / cost) if cost > 0 and metrics.conversions_value else 0
                )

                campaigns.append(
                    {
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "status": campaign.status.name,
                        "impressions": metrics.impressions,
                        "clicks": metrics.clicks,
                        "cost": round(cost, 2),
                        "ctr": round(metrics.ctr * 100, 2) if metrics.ctr else 0,  # Convert to percentage
                        "conversions": metrics.conversions,
                        "conversions_value": round(metrics.conversions_value, 2) if metrics.conversions_value else 0,
                        "average_cpc": round(metrics.average_cpc / 1_000_000, 2) if metrics.average_cpc else 0,
                        "roas": round(roas, 2),
                    }
                )

            return {
                "customer_id": customer_id,
                "date_range": date_range,
                "campaigns": campaigns,
                "total_campaigns": len(campaigns),
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except GoogleAdsException as ex:
            error_messages = []
            for error in ex.failure.errors:
                error_messages.append(f"{error.error_code.name}: {error.message}")
            return {"error": f"Google Ads API error: {'; '.join(error_messages)}"}
        except Exception as e:
            return {"error": f"Failed to retrieve campaign metrics: {str(e)}"}

    def list_campaigns(
        self,
        customer_id: str,
        status: Literal["ENABLED", "PAUSED", "REMOVED", "ALL"] = "ENABLED",
    ) -> dict:
        """List campaigns with optional status filter.

        Args:
            customer_id: Google Ads customer ID (without hyphens)
            status: Campaign status filter (ENABLED, PAUSED, REMOVED, or ALL)

        Returns:
            Dict with list of campaigns
        """
        try:
            ga_service = self.get_service("GoogleAdsService")

            # Build query with optional status filter
            where_clause = ""
            if status != "ALL":
                where_clause = f"WHERE campaign.status = {status}"

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.start_date,
                    campaign.end_date,
                    campaign_budget.amount_micros
                FROM campaign
                {where_clause}
                ORDER BY campaign.name
            """

            # Remove hyphens from customer ID
            customer_id_clean = customer_id.replace("-", "")

            response = ga_service.search(customer_id=customer_id_clean, query=query)

            campaigns = []
            for row in response:
                campaign = row.campaign
                budget = row.campaign_budget if hasattr(row, "campaign_budget") else None

                campaigns.append(
                    {
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "status": campaign.status.name,
                        "channel_type": campaign.advertising_channel_type.name,
                        "start_date": campaign.start_date if campaign.start_date else None,
                        "end_date": campaign.end_date if campaign.end_date else None,
                        "budget": (
                            round(budget.amount_micros / 1_000_000, 2)
                            if budget and budget.amount_micros
                            else None
                        ),
                    }
                )

            return {
                "customer_id": customer_id,
                "status_filter": status,
                "campaigns": campaigns,
                "total_campaigns": len(campaigns),
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except GoogleAdsException as ex:
            error_messages = []
            for error in ex.failure.errors:
                error_messages.append(f"{error.error_code.name}: {error.message}")
            return {"error": f"Google Ads API error: {'; '.join(error_messages)}"}
        except Exception as e:
            return {"error": f"Failed to list campaigns: {str(e)}"}

    def pause_campaign(self, customer_id: str, campaign_id: int) -> dict:
        """Pause an active campaign.

        Args:
            customer_id: Google Ads customer ID (without hyphens)
            campaign_id: Campaign ID to pause

        Returns:
            Dict with operation result
        """
        try:
            campaign_service = self.get_service("CampaignService")

            # Remove hyphens from customer ID
            customer_id_clean = customer_id.replace("-", "")

            # Create campaign operation
            campaign_operation = self._client.get_type("CampaignOperation")
            campaign = campaign_operation.update
            campaign.resource_name = campaign_service.campaign_path(customer_id_clean, campaign_id)

            # Set status to PAUSED
            campaign.status = self._client.enums.CampaignStatusEnum.PAUSED

            # Set update mask
            self._client.copy_from(
                campaign_operation.update_mask,
                self._client.get_type("FieldMask")(paths=["status"]),
            )

            # Execute the operation
            response = campaign_service.mutate_campaigns(
                customer_id=customer_id_clean,
                operations=[campaign_operation],
            )

            return {
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "status": "PAUSED",
                "resource_name": response.results[0].resource_name,
                "paused_at": datetime.utcnow().isoformat(),
            }

        except GoogleAdsException as ex:
            error_messages = []
            for error in ex.failure.errors:
                error_messages.append(f"{error.error_code.name}: {error.message}")
            return {"error": f"Google Ads API error: {'; '.join(error_messages)}"}
        except Exception as e:
            return {"error": f"Failed to pause campaign: {str(e)}"}


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Google Ads tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        credentials: Optional credential store adapter
    """

    def _get_credentials() -> dict[str, str] | None:
        """Get Google Ads credentials from credential store or environment.

        Returns:
            Dict with developer_token, client_id, client_secret, and refresh_token,
            or None if credentials are not available
        """
        if credentials is not None:
            creds = credentials.get("google_ads")
            if creds:
                # Credentials should be a dict with the required keys
                if isinstance(creds, dict):
                    return creds
                # If it's a string, it might be JSON
                import json

                try:
                    return json.loads(creds)
                except (json.JSONDecodeError, TypeError):
                    return None

        # Fall back to environment variables
        developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

        if all([developer_token, client_id, client_secret, refresh_token]):
            return {
                "developer_token": developer_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }

        return None

    def _make_client() -> _GoogleAdsClientWrapper | None:
        """Create a Google Ads client if credentials are available.

        Returns:
            _GoogleAdsClientWrapper instance or None if credentials are missing
        """
        creds = _get_credentials()
        if not creds:
            return None

        return _GoogleAdsClientWrapper(
            developer_token=creds["developer_token"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            refresh_token=creds["refresh_token"],
        )

    # ── Tool 1: Get Campaign Metrics ───────────────────────────────────

    @mcp.tool()
    def ads_get_campaign_metrics(
        customer_id: str,
        date_range: Literal["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"] = "LAST_7_DAYS",
    ) -> dict:
        """
        Retrieve campaign performance metrics for a Google Ads account.

        Use this to monitor campaign performance, track ROAS, CTR, and other key metrics.
        Ideal for daily performance checks and identifying underperforming campaigns.

        Args:
            customer_id: Google Ads customer ID (e.g., "123-456-7890" or "1234567890")
            date_range: Date range for metrics. Options:
                - TODAY: Today's data
                - YESTERDAY: Yesterday's data
                - LAST_7_DAYS: Last 7 days (default)
                - LAST_30_DAYS: Last 30 days
                - THIS_MONTH: Current month to date
                - LAST_MONTH: Previous month

        Returns:
            Dict with campaign metrics including:
            - campaign_id: Campaign identifier
            - campaign_name: Campaign name
            - status: Campaign status (ENABLED, PAUSED, etc.)
            - impressions: Number of ad impressions
            - clicks: Number of clicks
            - cost: Total cost in currency
            - ctr: Click-through rate (percentage)
            - conversions: Number of conversions
            - conversions_value: Total conversion value
            - average_cpc: Average cost per click
            - roas: Return on ad spend
        """
        if not customer_id:
            return {"error": "customer_id is required"}

        client = _make_client()
        if client is None:
            return _MISSING_CREDENTIALS_ERROR

        return client.get_campaign_metrics(customer_id=customer_id, date_range=date_range)

    # ── Tool 2: List Campaigns ─────────────────────────────────────────

    @mcp.tool()
    def ads_list_campaigns(
        customer_id: str,
        status: Literal["ENABLED", "PAUSED", "REMOVED", "ALL"] = "ENABLED",
    ) -> dict:
        """
        List campaigns in a Google Ads account with optional status filter.

        Use this to see all active campaigns, check campaign configurations,
        or audit campaign statuses.

        Args:
            customer_id: Google Ads customer ID (e.g., "123-456-7890" or "1234567890")
            status: Filter campaigns by status. Options:
                - ENABLED: Only active campaigns (default)
                - PAUSED: Only paused campaigns
                - REMOVED: Only removed campaigns
                - ALL: All campaigns regardless of status

        Returns:
            Dict with list of campaigns including:
            - campaign_id: Campaign identifier
            - campaign_name: Campaign name
            - status: Campaign status
            - channel_type: Advertising channel (SEARCH, DISPLAY, etc.)
            - start_date: Campaign start date
            - end_date: Campaign end date (if set)
            - budget: Daily budget amount
        """
        if not customer_id:
            return {"error": "customer_id is required"}

        client = _make_client()
        if client is None:
            return _MISSING_CREDENTIALS_ERROR

        return client.list_campaigns(customer_id=customer_id, status=status)

    # ── Tool 3: Pause Campaign ─────────────────────────────────────────

    @mcp.tool()
    def ads_pause_campaign(
        customer_id: str,
        campaign_id: int,
    ) -> dict:
        """
        Pause an active Google Ads campaign.

        Use this to stop an underperforming campaign or temporarily halt spending.
        This is a safer alternative to removing a campaign, as it can be easily resumed.

        Args:
            customer_id: Google Ads customer ID (e.g., "123-456-7890" or "1234567890")
            campaign_id: Campaign ID to pause (numeric ID from ads_list_campaigns)

        Returns:
            Dict with operation result including:
            - customer_id: Customer ID
            - campaign_id: Campaign ID that was paused
            - status: New status (PAUSED)
            - resource_name: Google Ads resource name
            - paused_at: Timestamp when campaign was paused
        """
        if not customer_id:
            return {"error": "customer_id is required"}
        if not campaign_id:
            return {"error": "campaign_id is required"}

        client = _make_client()
        if client is None:
            return _MISSING_CREDENTIALS_ERROR

        return client.pause_campaign(customer_id=customer_id, campaign_id=campaign_id)
