"""
DocuSign tool credentials.

Contains credentials for DocuSign eSignature REST API integration.
"""

from .base import CredentialSpec

DOCUSIGN_CREDENTIALS = {
    "docusign": CredentialSpec(
        env_var="DOCUSIGN_ACCESS_TOKEN",
        tools=[
            "docusign_create_envelope",
            "docusign_get_envelope_status",
            "docusign_list_envelopes",
            "docusign_download_document",
        ],
        required=True,
        startup_required=False,
        help_url="https://developers.docusign.com/platform/auth/",
        description="DocuSign OAuth 2.0 Access Token",
        # Auth method support
        aden_supported=True,
        aden_provider_name="docusign",
        direct_api_key_supported=True,
        api_key_instructions="""To get a DocuSign Access Token:
1. Log in to your DocuSign Developer Account (demo.docusign.net).
2. Go to Settings > Apps and Keys.
3. Add a new App and Integration Key.
4. Generate an OAuth Token using the Auth Code Grant or JWT Grant.
   (For testing, you can use the Token Generator in the dashboard)
5. Set the DOCUSIGN_ACCESS_TOKEN environment variable.
6. Also ensure DOCUSIGN_ACCOUNT_ID and DOCUSIGN_BASE_URI are set.
""",
        # Health check configuration
        health_check_endpoint="{base_uri}/restapi/v2.1/accounts/{account_id}",
        health_check_method="GET",
        # Credential store mapping
        credential_id="docusign",
        credential_key="access_token",
        # Additional required configuration
        additional_env_vars=["DOCUSIGN_ACCOUNT_ID", "DOCUSIGN_BASE_URI"],
    ),
}
