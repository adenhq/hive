"""
Integration credentials.

Contains credentials for third-party service integrations (HubSpot, etc.).
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "github": CredentialSpec(
        env_var="GITHUB_TOKEN",
        tools=[
            "github_list_repos",
            "github_get_repo",
            "github_search_repos",
            "github_list_issues",
            "github_get_issue",
            "github_create_issue",
            "github_update_issue",
            "github_list_pull_requests",
            "github_get_pull_request",
            "github_create_pull_request",
            "github_search_code",
            "github_list_branches",
            "github_get_branch",
        ],
        required=True,
        startup_required=False,
        help_url="https://github.com/settings/tokens",
        description="GitHub Personal Access Token (classic)",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a GitHub Personal Access Token:
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Click "Generate new token" > "Generate new token (classic)"
3. Give your token a descriptive name (e.g., "Hive Agent")
4. Select the following scopes:
   - repo (Full control of private repositories)
   - read:org (Read org and team membership - optional)
   - user (Read user profile data - optional)
5. Click "Generate token" and copy the token (starts with ghp_)
6. Store it securely - you won't be able to see it again!""",
        # Health check configuration
        health_check_endpoint="https://api.github.com/user",
        health_check_method="GET",
        # Credential store mapping
        credential_id="github",
        credential_key="access_token",
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
    "google_vision": CredentialSpec(
        env_var="GOOGLE_CLOUD_VISION_API_KEY",
        tools=[
            "vision_detect_labels",
            "vision_detect_text",
            "vision_detect_faces",
            "vision_localize_objects",
            "vision_detect_logos",
            "vision_detect_landmarks",
            "vision_image_properties",
            "vision_web_detection",
            "vision_safe_search",
        ],
        required=True,
        startup_required=False,
        help_url="https://console.cloud.google.com/apis/credentials",
        description="Google Cloud Vision API key for image analysis",
        # Auth method support
        aden_supported=False,
        aden_provider_name="",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Google Cloud Vision API key:
1. Go to Google Cloud Console (console.cloud.google.com)
2. Create a new project or select existing
3. Go to APIs & Services > Library
4. Search for "Cloud Vision API" and enable it
5. Go to APIs & Services > Credentials
6. Click "Create Credentials" > "API Key"
7. Copy the API key""",
        # Health check configuration
        health_check_endpoint="",
        health_check_method="GET",
        # Credential store mapping
        credential_id="google_vision",
        credential_key="api_key",
    ),
}
