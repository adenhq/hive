"""
Integration credentials.

Contains credentials for third-party service integrations (HubSpot, etc.).
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "notion": CredentialSpec(
        env_var="NOTION_API_KEY",
        tools=[
            "notion_search",
            "notion_get_page",
            "notion_create_page",
            "notion_update_page",
            "notion_query_database",
            "notion_append_blocks",
        ],
        required=True,
        startup_required=False,
        help_url="https://developers.notion.com/docs/getting-started",
        description="Notion API integration token",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a Notion integration token:
1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name your integration (e.g., "Hive Agent")
4. Select the workspace to associate it with
5. Click "Submit" to create the integration
6. Copy the "Internal Integration Secret" (starts with "secret_")
7. Share your Notion pages/databases with the integration:
   - Open the page/database in Notion
   - Click "..." menu → "Add connections"
   - Select your integration""",
        # Health check configuration
        health_check_endpoint="https://api.notion.com/v1/users/me",
        health_check_method="GET",
        # Credential store mapping
        credential_id="notion",
        credential_key="api_key",
    ),
    "hubspot": CredentialSpec(
        env_var="HUBSPOT_ACCESS_TOKEN",
        tools=[
            "hubspot_search_contacts",
            "hubspot_get_contact",
            "hubspot_create_contact",
            "hubspot_update_contact",
            "hubspot_search_companies",
            "hubspot_get_company",
            "hubspot_create_company",
            "hubspot_update_company",
            "hubspot_search_deals",
            "hubspot_get_deal",
            "hubspot_create_deal",
            "hubspot_update_deal",
        ],
        required=True,
        startup_required=False,
        help_url="https://developers.hubspot.com/docs/api/private-apps",
        description="HubSpot access token (Private App or OAuth2)",
        # Auth method support
        aden_supported=True,
        aden_provider_name="hubspot",
        direct_api_key_supported=True,
        api_key_instructions="""To get a HubSpot Private App token:
1. Go to HubSpot Settings > Integrations > Private Apps
2. Click "Create a private app"
3. Name your app (e.g., "Hive Agent")
4. Go to the "Scopes" tab and enable:
   - crm.objects.contacts.read
   - crm.objects.contacts.write
   - crm.objects.companies.read
   - crm.objects.companies.write
   - crm.objects.deals.read
   - crm.objects.deals.write
5. Click "Create app" and copy the access token""",
        # Health check configuration
        health_check_endpoint="https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
        health_check_method="GET",
        # Credential store mapping
        credential_id="hubspot",
        credential_key="access_token",
    ),
}
