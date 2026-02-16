# Google Ads Tool

Campaign monitoring and management for Google Ads via the Google Ads API.

## Overview

This tool provides three MCP tools for interacting with Google Ads:

1. **ads_get_campaign_metrics** - Retrieve campaign performance metrics (impressions, clicks, cost, CTR, ROAS)
2. **ads_list_campaigns** - List campaigns with optional status filtering
3. **ads_pause_campaign** - Pause an active campaign

## Use Cases

### Growth Agent
Monitor ad spend and performance daily:
```python
# Check if any campaign exceeds budget with poor performance
metrics = ads_get_campaign_metrics(
    customer_id="123-456-7890",
    date_range="TODAY"
)

for campaign in metrics["campaigns"]:
    if campaign["cost"] > 500 and campaign["ctr"] < 1.0:
        # Pause underperforming campaign
        ads_pause_campaign(
            customer_id="123-456-7890",
            campaign_id=campaign["campaign_id"]
        )
```

### Reporting Agent
Generate weekly performance summaries:
```python
# Get top performing keywords for the marketing team
metrics = ads_get_campaign_metrics(
    customer_id="123-456-7890",
    date_range="LAST_7_DAYS"
)

# Sort by ROAS and generate report
top_campaigns = sorted(
    metrics["campaigns"],
    key=lambda x: x["roas"],
    reverse=True
)[:10]
```

## Authentication

This tool requires Google Ads API credentials. You need:

1. **Developer Token** - Get from Google Ads API Center
2. **OAuth2 Credentials** - Client ID, Client Secret, and Refresh Token

### Setup Steps

1. **Get a Developer Token**:
   - Go to [Google Ads API Center](https://ads.google.com/aw/apicenter)
   - Apply for API access
   - Once approved, copy your developer token

2. **Create OAuth2 Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google Ads API
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download the client ID and client secret

3. **Generate Refresh Token**:
   ```bash
   # Install google-ads library
   pip install google-ads

   # Run OAuth flow to get refresh token
   python -m google.ads.googleads.oauth2.get_refresh_token \
       --client_id=YOUR_CLIENT_ID \
       --client_secret=YOUR_CLIENT_SECRET
   ```

4. **Set Environment Variables**:
   ```bash
   export GOOGLE_ADS_DEVELOPER_TOKEN="your-developer-token"
   export GOOGLE_ADS_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   export GOOGLE_ADS_CLIENT_SECRET="your-client-secret"
   export GOOGLE_ADS_REFRESH_TOKEN="your-refresh-token"
   ```

## Tool Reference

### ads_get_campaign_metrics

Retrieve campaign performance metrics for analysis and monitoring.

**Parameters:**
- `customer_id` (str, required): Google Ads customer ID (e.g., "123-456-7890")
- `date_range` (str, optional): Date range for metrics. Options:
  - `"TODAY"` - Today's data
  - `"YESTERDAY"` - Yesterday's data
  - `"LAST_7_DAYS"` - Last 7 days (default)
  - `"LAST_30_DAYS"` - Last 30 days
  - `"THIS_MONTH"` - Current month to date
  - `"LAST_MONTH"` - Previous month

**Returns:**
```json
{
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
      "roas": 4.00
    }
  ],
  "total_campaigns": 1,
  "retrieved_at": "2024-02-16T18:30:00.000000"
}
```

### ads_list_campaigns

List all campaigns in an account with optional status filtering.

**Parameters:**
- `customer_id` (str, required): Google Ads customer ID
- `status` (str, optional): Filter by campaign status. Options:
  - `"ENABLED"` - Only active campaigns (default)
  - `"PAUSED"` - Only paused campaigns
  - `"REMOVED"` - Only removed campaigns
  - `"ALL"` - All campaigns

**Returns:**
```json
{
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
      "budget": 100.00
    }
  ],
  "total_campaigns": 1,
  "retrieved_at": "2024-02-16T18:30:00.000000"
}
```

### ads_pause_campaign

Pause an active campaign to stop spending.

**Parameters:**
- `customer_id` (str, required): Google Ads customer ID
- `campaign_id` (int, required): Campaign ID to pause

**Returns:**
```json
{
  "customer_id": "123-456-7890",
  "campaign_id": 12345678,
  "status": "PAUSED",
  "resource_name": "customers/1234567890/campaigns/12345678",
  "paused_at": "2024-02-16T18:30:00.000000"
}
```

## Error Handling

All tools return error dictionaries when operations fail:

```json
{
  "error": "Google Ads API error: AUTHENTICATION_ERROR: Invalid developer token"
}
```

Common errors:
- **Missing credentials**: Set all required environment variables
- **Invalid customer ID**: Ensure customer ID is correct (with or without hyphens)
- **Permission denied**: Check API access and OAuth scopes
- **Campaign not found**: Verify campaign ID exists in the account
- **Rate limit exceeded**: Implement exponential backoff

## Metrics Glossary

- **Impressions**: Number of times ads were shown
- **Clicks**: Number of times ads were clicked
- **Cost**: Total amount spent (in account currency)
- **CTR (Click-Through Rate)**: Percentage of impressions that resulted in clicks
- **Conversions**: Number of conversion actions completed
- **Conversions Value**: Total value of conversions
- **Average CPC**: Average cost per click
- **ROAS (Return on Ad Spend)**: Revenue generated per dollar spent

## Limitations

- Requires Google Ads API access (may need approval)
- Rate limits apply (see [Google Ads API quotas](https://developers.google.com/google-ads/api/docs/best-practices/quotas))
- Customer ID must have proper access permissions
- Some metrics may have data delays (up to 3 hours)

## References

- [Google Ads API Documentation](https://developers.google.com/google-ads/api/docs/start)
- [Google Ads API Python Client](https://github.com/googleads/google-ads-python)
- [Query Language Guide](https://developers.google.com/google-ads/api/docs/query/overview)
