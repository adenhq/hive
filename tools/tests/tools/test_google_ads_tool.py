"""Tests for Google Ads tool with FastMCP."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.google_ads_tool import register_tools

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def mcp():
    """Create a FastMCP instance for testing."""
    return FastMCP("test-server")


@pytest.fixture
def ads_get_campaign_metrics_fn(mcp: FastMCP):
    """Register and return the ads_get_campaign_metrics tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["ads_get_campaign_metrics"].fn


@pytest.fixture
def ads_list_campaigns_fn(mcp: FastMCP):
    """Register and return the ads_list_campaigns tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["ads_list_campaigns"].fn


@pytest.fixture
def ads_pause_campaign_fn(mcp: FastMCP):
    """Register and return the ads_pause_campaign tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["ads_pause_campaign"].fn


# ── Credential Tests ──────────────────────────────────────────────────


class TestGoogleAdsCredentials:
    """Test credential handling for all Google Ads tools."""

    def test_get_campaign_metrics_no_credentials_returns_error(
        self, ads_get_campaign_metrics_fn, monkeypatch
    ):
        """Get campaign metrics without credentials returns helpful error."""
        monkeypatch.delenv("GOOGLE_ADS_DEVELOPER_TOKEN", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_REFRESH_TOKEN", raising=False)

        result = ads_get_campaign_metrics_fn(customer_id="123-456-7890")

        assert "error" in result
        assert "not configured" in result["error"]
        assert "help" in result

    def test_list_campaigns_no_credentials_returns_error(
        self, ads_list_campaigns_fn, monkeypatch
    ):
        """List campaigns without credentials returns helpful error."""
        monkeypatch.delenv("GOOGLE_ADS_DEVELOPER_TOKEN", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_REFRESH_TOKEN", raising=False)

        result = ads_list_campaigns_fn(customer_id="123-456-7890")

        assert "error" in result
        assert "not configured" in result["error"]

    def test_pause_campaign_no_credentials_returns_error(
        self, ads_pause_campaign_fn, monkeypatch
    ):
        """Pause campaign without credentials returns helpful error."""
        monkeypatch.delenv("GOOGLE_ADS_DEVELOPER_TOKEN", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("GOOGLE_ADS_REFRESH_TOKEN", raising=False)

        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=12345)

        assert "error" in result
        assert "not configured" in result["error"]


# ── Input Validation Tests ────────────────────────────────────────────


class TestInputValidation:
    """Test input validation across tools."""

    def test_get_campaign_metrics_no_customer_id(self, ads_get_campaign_metrics_fn):
        """Get campaign metrics without customer_id returns error."""
        result = ads_get_campaign_metrics_fn(customer_id="")

        assert "error" in result
        assert "required" in result["error"].lower()

    def test_list_campaigns_no_customer_id(self, ads_list_campaigns_fn):
        """List campaigns without customer_id returns error."""
        result = ads_list_campaigns_fn(customer_id="")

        assert "error" in result
        assert "required" in result["error"].lower()

    def test_pause_campaign_no_customer_id(self, ads_pause_campaign_fn):
        """Pause campaign without customer_id returns error."""
        result = ads_pause_campaign_fn(customer_id="", campaign_id=12345)

        assert "error" in result
        assert "required" in result["error"].lower()

    def test_pause_campaign_no_campaign_id(self, ads_pause_campaign_fn):
        """Pause campaign without campaign_id returns error."""
        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=None)

        assert "error" in result
        assert "required" in result["error"].lower()


# ── Get Campaign Metrics Tests ────────────────────────────────────────


class TestAdsGetCampaignMetrics:
    """Tests for ads_get_campaign_metrics tool."""

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_get_campaign_metrics_success(
        self, mock_client_class, ads_get_campaign_metrics_fn, monkeypatch
    ):
        """Successful campaign metrics retrieval returns formatted results."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        # Mock the client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the get_campaign_metrics method
        mock_client.get_campaign_metrics.return_value = {
            "customer_id": "123-456-7890",
            "date_range": "LAST_7_DAYS",
            "campaigns": [
                {
                    "campaign_id": 12345678,
                    "campaign_name": "Summer Sale 2024",
                    "status": "ENABLED",
                    "impressions": 150000,
                    "clicks": 3500,
                    "cost": 875.50,
                    "ctr": 2.33,
                    "conversions": 125,
                    "conversions_value": 3500.00,
                    "average_cpc": 0.25,
                    "roas": 4.00,
                }
            ],
            "total_campaigns": 1,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_get_campaign_metrics_fn(
            customer_id="123-456-7890", date_range="LAST_7_DAYS"
        )

        assert result["total_campaigns"] == 1
        assert result["campaigns"][0]["campaign_name"] == "Summer Sale 2024"
        assert result["campaigns"][0]["impressions"] == 150000
        assert result["campaigns"][0]["roas"] == 4.00

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_get_campaign_metrics_empty_results(
        self, mock_client_class, ads_get_campaign_metrics_fn, monkeypatch
    ):
        """Campaign metrics with no campaigns returns empty list."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_campaign_metrics.return_value = {
            "customer_id": "123-456-7890",
            "date_range": "LAST_7_DAYS",
            "campaigns": [],
            "total_campaigns": 0,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_get_campaign_metrics_fn(customer_id="123-456-7890")

        assert result["total_campaigns"] == 0
        assert result["campaigns"] == []

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_get_campaign_metrics_api_error(
        self, mock_client_class, ads_get_campaign_metrics_fn, monkeypatch
    ):
        """API error returns error message."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_campaign_metrics.return_value = {
            "error": "Google Ads API error: AUTHENTICATION_ERROR: Invalid developer token"
        }

        result = ads_get_campaign_metrics_fn(customer_id="123-456-7890")

        assert "error" in result
        assert "AUTHENTICATION_ERROR" in result["error"]

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_get_campaign_metrics_different_date_ranges(
        self, mock_client_class, ads_get_campaign_metrics_fn, monkeypatch
    ):
        """Test different date range options."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        for date_range in ["TODAY", "YESTERDAY", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"]:
            mock_client.get_campaign_metrics.return_value = {
                "customer_id": "123-456-7890",
                "date_range": date_range,
                "campaigns": [],
                "total_campaigns": 0,
                "retrieved_at": "2024-02-16T18:30:00.000000",
            }

            result = ads_get_campaign_metrics_fn(
                customer_id="123-456-7890", date_range=date_range
            )

            assert result["date_range"] == date_range


# ── List Campaigns Tests ──────────────────────────────────────────────


class TestAdsListCampaigns:
    """Tests for ads_list_campaigns tool."""

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_list_campaigns_success(
        self, mock_client_class, ads_list_campaigns_fn, monkeypatch
    ):
        """Successful campaign listing returns formatted results."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_campaigns.return_value = {
            "customer_id": "123-456-7890",
            "status_filter": "ENABLED",
            "campaigns": [
                {
                    "campaign_id": 12345678,
                    "campaign_name": "Summer Sale 2024",
                    "status": "ENABLED",
                    "channel_type": "SEARCH",
                    "start_date": "2024-06-01",
                    "end_date": "2024-08-31",
                    "budget": 100.00,
                },
                {
                    "campaign_id": 87654321,
                    "campaign_name": "Winter Campaign",
                    "status": "ENABLED",
                    "channel_type": "DISPLAY",
                    "start_date": "2024-12-01",
                    "end_date": None,
                    "budget": 200.00,
                },
            ],
            "total_campaigns": 2,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_list_campaigns_fn(customer_id="123-456-7890", status="ENABLED")

        assert result["total_campaigns"] == 2
        assert result["campaigns"][0]["campaign_name"] == "Summer Sale 2024"
        assert result["campaigns"][0]["channel_type"] == "SEARCH"
        assert result["campaigns"][1]["campaign_name"] == "Winter Campaign"

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_list_campaigns_different_statuses(
        self, mock_client_class, ads_list_campaigns_fn, monkeypatch
    ):
        """Test different status filters."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        for status in ["ENABLED", "PAUSED", "REMOVED", "ALL"]:
            mock_client.list_campaigns.return_value = {
                "customer_id": "123-456-7890",
                "status_filter": status,
                "campaigns": [],
                "total_campaigns": 0,
                "retrieved_at": "2024-02-16T18:30:00.000000",
            }

            result = ads_list_campaigns_fn(customer_id="123-456-7890", status=status)

            assert result["status_filter"] == status

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_list_campaigns_empty_results(
        self, mock_client_class, ads_list_campaigns_fn, monkeypatch
    ):
        """List campaigns with no results returns empty list."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_campaigns.return_value = {
            "customer_id": "123-456-7890",
            "status_filter": "ENABLED",
            "campaigns": [],
            "total_campaigns": 0,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_list_campaigns_fn(customer_id="123-456-7890")

        assert result["total_campaigns"] == 0
        assert result["campaigns"] == []

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_list_campaigns_api_error(
        self, mock_client_class, ads_list_campaigns_fn, monkeypatch
    ):
        """API error returns error message."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_campaigns.return_value = {
            "error": "Google Ads API error: CUSTOMER_NOT_FOUND: Customer not found"
        }

        result = ads_list_campaigns_fn(customer_id="999-999-9999")

        assert "error" in result
        assert "CUSTOMER_NOT_FOUND" in result["error"]


# ── Pause Campaign Tests ──────────────────────────────────────────────


class TestAdsPauseCampaign:
    """Tests for ads_pause_campaign tool."""

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_pause_campaign_success(
        self, mock_client_class, ads_pause_campaign_fn, monkeypatch
    ):
        """Successful campaign pause returns confirmation."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.pause_campaign.return_value = {
            "customer_id": "123-456-7890",
            "campaign_id": 12345678,
            "status": "PAUSED",
            "resource_name": "customers/1234567890/campaigns/12345678",
            "paused_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=12345678)

        assert result["status"] == "PAUSED"
        assert result["campaign_id"] == 12345678
        assert "paused_at" in result

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_pause_campaign_not_found(
        self, mock_client_class, ads_pause_campaign_fn, monkeypatch
    ):
        """Pausing non-existent campaign returns error."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.pause_campaign.return_value = {
            "error": "Google Ads API error: CAMPAIGN_NOT_FOUND: Campaign not found"
        }

        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=99999999)

        assert "error" in result
        assert "CAMPAIGN_NOT_FOUND" in result["error"]

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_pause_campaign_already_paused(
        self, mock_client_class, ads_pause_campaign_fn, monkeypatch
    ):
        """Pausing already paused campaign still succeeds."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.pause_campaign.return_value = {
            "customer_id": "123-456-7890",
            "campaign_id": 12345678,
            "status": "PAUSED",
            "resource_name": "customers/1234567890/campaigns/12345678",
            "paused_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=12345678)

        assert result["status"] == "PAUSED"

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_pause_campaign_permission_denied(
        self, mock_client_class, ads_pause_campaign_fn, monkeypatch
    ):
        """Pausing campaign without permission returns error."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.pause_campaign.return_value = {
            "error": "Google Ads API error: PERMISSION_DENIED: User does not have permission"
        }

        result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=12345678)

        assert "error" in result
        assert "PERMISSION_DENIED" in result["error"]


# ── Integration Tests ─────────────────────────────────────────────────


class TestGoogleAdsIntegration:
    """Integration tests for Google Ads tools."""

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_workflow_list_then_pause(
        self,
        mock_client_class,
        ads_list_campaigns_fn,
        ads_pause_campaign_fn,
        monkeypatch,
    ):
        """Test workflow: list campaigns, then pause one."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Step 1: List campaigns
        mock_client.list_campaigns.return_value = {
            "customer_id": "123-456-7890",
            "status_filter": "ENABLED",
            "campaigns": [
                {
                    "campaign_id": 12345678,
                    "campaign_name": "Test Campaign",
                    "status": "ENABLED",
                    "channel_type": "SEARCH",
                    "start_date": "2024-01-01",
                    "end_date": None,
                    "budget": 100.00,
                }
            ],
            "total_campaigns": 1,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        list_result = ads_list_campaigns_fn(customer_id="123-456-7890")
        assert list_result["total_campaigns"] == 1
        campaign_id = list_result["campaigns"][0]["campaign_id"]

        # Step 2: Pause the campaign
        mock_client.pause_campaign.return_value = {
            "customer_id": "123-456-7890",
            "campaign_id": campaign_id,
            "status": "PAUSED",
            "resource_name": f"customers/1234567890/campaigns/{campaign_id}",
            "paused_at": "2024-02-16T18:30:00.000000",
        }

        pause_result = ads_pause_campaign_fn(customer_id="123-456-7890", campaign_id=campaign_id)
        assert pause_result["status"] == "PAUSED"
        assert pause_result["campaign_id"] == campaign_id

    @patch("aden_tools.tools.google_ads_tool.google_ads_tool._GoogleAdsClientWrapper")
    def test_customer_id_with_hyphens_normalized(
        self, mock_client_class, ads_list_campaigns_fn, monkeypatch
    ):
        """Customer ID with hyphens is accepted and normalized."""
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_campaigns.return_value = {
            "customer_id": "123-456-7890",
            "status_filter": "ENABLED",
            "campaigns": [],
            "total_campaigns": 0,
            "retrieved_at": "2024-02-16T18:30:00.000000",
        }

        result = ads_list_campaigns_fn(customer_id="123-456-7890")

        assert result["customer_id"] == "123-456-7890"
