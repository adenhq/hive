"""
Email tool credentials.

Contains credentials for email providers like Resend, SendGrid, etc.
"""

from .base import CredentialSpec

EMAIL_CREDENTIALS = {
    "resend": CredentialSpec(
        env_var="RESEND_API_KEY",
        # send_email is multi-provider (auto-detects at runtime)
        tools=[],
        node_types=[],
        required=False,
        startup_required=False,
        help_url="https://resend.com/api-keys",
        description="API key for Resend email service",
        # Auth method support
        direct_api_key_supported=True,
        api_key_instructions="""To get a Resend API key:
1. Go to https://resend.com and create an account (or sign in)
2. Navigate to API Keys in the dashboard
3. Click "Create API Key"
4. Give it a name (e.g., "Hive Agent") and choose permissions:
   - "Sending access" is sufficient for most use cases
   - "Full access" if you also need to manage domains
5. Copy the API key (starts with re_)
6. Store it securely - you won't be able to see it again!
7. Note: You'll also need to verify a domain to send emails from custom addresses""",
        # Health check configuration
        health_check_endpoint="https://api.resend.com/domains",
        # Credential store mapping
        credential_id="resend",
        credential_key="api_key",
    ),
    "google": CredentialSpec(
        env_var="GOOGLE_ACCESS_TOKEN",
        tools=[
            # Multi-provider tools are excluded — they auto-detect provider
            # at runtime: send_email, email_list, email_read, email_search,
            # email_labels, email_mark_read, email_delete, email_reply,
            # email_forward, email_move, email_bulk_delete
            # Gmail-specific tools (from gmail_tool module)
            "gmail_reply_email",
            "gmail_list_messages",
            "gmail_get_message",
            "gmail_trash_message",
            "gmail_modify_message",
            "gmail_batch_modify_messages",
            "gmail_batch_get_messages",
            "gmail_create_draft",
            "gmail_list_labels",
            "gmail_create_label",
        ],
        node_types=[],
        required=True,
        startup_required=False,
        help_url="https://hive.adenhq.com",
        description="Google OAuth2 access token (via Aden) - used for Gmail",
        aden_supported=True,
        aden_provider_name="google",
        direct_api_key_supported=False,
        api_key_instructions="Google OAuth requires OAuth2. Connect via hive.adenhq.com",
        health_check_endpoint="https://gmail.googleapis.com/gmail/v1/users/me/profile",
        health_check_method="GET",
        credential_id="google",
        credential_key="access_token",
    ),
    "outlook": CredentialSpec(
        env_var="OUTLOOK_OAUTH_TOKEN",
        tools=[
            # Multi-provider tools are excluded — they auto-detect provider
            # at runtime: send_email, email_list, email_read, email_search,
            # email_labels, email_mark_read, email_delete, email_reply,
            # email_forward, email_move, email_bulk_delete
            # Outlook-specific tools (from outlook_tool module)
            "outlook_list_categories",
            "outlook_set_category",
            "outlook_create_category",
            "outlook_get_focused_inbox",
            "outlook_create_draft",
            "outlook_batch_get_messages",
        ],
        node_types=[],
        required=False,
        startup_required=False,
        help_url="https://hive.adenhq.com",
        description="Outlook OAuth2 access token (via Aden) - used for Outlook/Microsoft 365 email",
        aden_supported=True,
        aden_provider_name="outlook",
        direct_api_key_supported=False,
        api_key_instructions="Outlook OAuth requires OAuth2. Connect via hive.adenhq.com",
        health_check_endpoint="https://graph.microsoft.com/v1.0/me",
        health_check_method="GET",
        credential_id="outlook",
        credential_key="access_token",
    ),
}
