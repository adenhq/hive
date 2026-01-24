"""
Email service credentials.

Contains credentials for email providers like Resend.
"""
from .base import CredentialSpec

EMAIL_CREDENTIALS = {
    "resend": CredentialSpec(
        env_var="RESEND_API_KEY",
        tools=["send_email", "send_templated_email"],
        node_types=[],
        required=True,
        startup_required=False,
        help_url="https://resend.com/api-keys",
        description="API key for Resend email service",
    ),
}
