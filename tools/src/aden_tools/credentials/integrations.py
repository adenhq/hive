"""
Integration credentials.

Contains credentials for third-party service integrations (HubSpot, etc.).
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
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

    # Twilio credentials
    "twilio_account_sid": CredentialSpec(
        env_var="TWILIO_ACCOUNT_SID",
        tools=["send_sms", "send_whatsapp", "fetch_history", "validate_number"],
        required=True,
        startup_required=False,
        help_url="https://www.twilio.com/console",
        description="Twilio Account SID",
        credential_id="twilio",
        credential_key="account_sid",
    ),

    "twilio_auth_token": CredentialSpec(
        env_var="TWILIO_AUTH_TOKEN",
        tools=["send_sms", "send_whatsapp", "fetch_history", "validate_number"],
        required=True,
        startup_required=False,
        help_url="https://www.twilio.com/console",
        description="Twilio Auth Token",
        credential_id="twilio",
        credential_key="auth_token",
    ),

    "twilio_from_number": CredentialSpec(
        env_var="TWILIO_FROM_NUMBER",
        tools=["send_sms", "send_whatsapp"],
        required=True,
        startup_required=False,
        help_url="https://www.twilio.com/console",
        description="Default Twilio from number (E.164), e.g., +1234567890",
        credential_id="twilio",
        credential_key="from_number",
    ),
}
