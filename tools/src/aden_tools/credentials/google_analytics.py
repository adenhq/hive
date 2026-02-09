"""
Google Analytics tool credentials.

Contains credentials for Google Analytics Data API v1 integration.
"""

from .base import CredentialSpec

GOOGLE_ANALYTICS_CREDENTIALS = {
    "google_analytics": CredentialSpec(
        env_var="GOOGLE_APPLICATION_CREDENTIALS",
        tools=[
            "ga_run_report",
            "ga_get_realtime",
            "ga_get_top_pages",
            "ga_get_traffic_sources",
        ],
        required=True,
        startup_required=False,
        help_url="https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries",
        description="Path to Google Cloud service account JSON key with Analytics read access",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To set up Google Analytics credentials:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create or select a project
3. Enable the Google Analytics Data API
4. Go to IAM & Admin > Service Accounts
5. Create a service account with "Viewer" role
6. Generate a JSON key and download it
7. In Google Analytics, add the service account email as a Viewer
8. Set GOOGLE_APPLICATION_CREDENTIALS to the path of the JSON key file""",
        # Health check configuration
        health_check_endpoint=None,
        # Credential store mapping
        credential_id="google_analytics",
        credential_key="credentials_path",
    ),
}
