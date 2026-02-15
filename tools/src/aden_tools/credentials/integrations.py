"""
Credential specifications for third-party integrations.

This module defines the expected credential keys for each integration.
Used by the CI conformance test (test_spec_conformance.py) to validate
that all required credentials are documented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialSpec:
    """Specification for credentials required by an integration."""
    
    name: str
    required_keys: list[str]
    optional_keys: list[str] | None = None
    description: str | None = None
    
    def __post_init__(self) -> None:
        if self.optional_keys is None:
            object.__setattr__(self, "optional_keys", [])


# Define credential specifications for all integrations
APOLLO_SPEC = CredentialSpec(
    name="apollo",
    required_keys=["APOLLO_API_KEY"],
    description="Apollo.io API key for prospecting and enrichment",
)

GITHUB_SPEC = CredentialSpec(
    name="github",
    required_keys=["GITHUB_TOKEN"],
    description="GitHub personal access token for repository operations",
)

HUBSPOT_SPEC = CredentialSpec(
    name="hubspot",
    required_keys=["HUBSPOT_ACCESS_TOKEN"],
    description="HubSpot private app access token for CRM operations",
)

SLACK_SPEC = CredentialSpec(
    name="slack",
    required_keys=["SLACK_BOT_TOKEN"],
    optional_keys=["SLACK_USER_TOKEN", "SLACK_SIGNING_SECRET"],
    description="Slack bot token for workspace interactions",
)

EMAIL_SPEC = CredentialSpec(
    name="email",
    required_keys=["RESEND_API_KEY"],
    description="Resend API key for sending emails",
)

WEB_SEARCH_SPEC = CredentialSpec(
    name="web_search",
    required_keys=[],
    optional_keys=["GOOGLE_API_KEY", "GOOGLE_CX", "BRAVE_API_KEY"],
    description="API keys for web search providers (Google, Brave)",
)

S3_SPEC = CredentialSpec(
    name="s3",
    required_keys=[],
    optional_keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_ENDPOINT_URL"],
    description="AWS credentials for S3 operations. If not provided, boto3 will use IAM roles or environment variables.",
)

# Registry of all integration specs
ALL_SPECS: list[CredentialSpec] = [
    APOLLO_SPEC,
    GITHUB_SPEC,
    HUBSPOT_SPEC,
    SLACK_SPEC,
    EMAIL_SPEC,
    WEB_SEARCH_SPEC,
    S3_SPEC,
]


def get_spec(name: str) -> CredentialSpec | None:
    """Get credential specification by integration name."""
    for spec in ALL_SPECS:
        if spec.name == name:
            return spec
    return None


def get_all_specs() -> list[CredentialSpec]:
    """Get all credential specifications."""
    return ALL_SPECS.copy()