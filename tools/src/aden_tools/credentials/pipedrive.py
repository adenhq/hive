"""
Pipedrive CRM tool credentials.

Contains credentials for Pipedrive CRM integration.
"""

from .base import CredentialSpec

PIPEDRIVE_CREDENTIALS = {
    "pipedrive": CredentialSpec(
        env_var="PIPEDRIVE_API_TOKEN",
        tools=[
            "pipedrive_create_person",
            "pipedrive_search_person",
            "pipedrive_get_person_details",
            "pipedrive_create_deal",
            "pipedrive_update_deal_stage",
            "pipedrive_list_deals",
            "pipedrive_add_note_to_deal",
        ],
        required=True,
        startup_required=False,
        help_url="https://pipedrive.readme.io/docs/how-to-find-the-api-token",
        description="Pipedrive Personal API Token",
        # Auth method support
        aden_supported=True,
        aden_provider_name="pipedrive",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Pipedrive API token:
1. Log in to your Pipedrive account.
2. Go to Settings > Personal preferences > API.
3. Find your personal API token and copy it.""",
        # Health check configuration
        health_check_endpoint="https://api.pipedrive.com/v1/users/me",
        health_check_method="GET",
        # Credential store mapping
        credential_id="pipedrive",
        credential_key="api_token",
    ),
}
