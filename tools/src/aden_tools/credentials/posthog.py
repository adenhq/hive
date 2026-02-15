"""PostHog credential specification."""

from __future__ import annotations

from .base import CredentialSpec

POSTHOG_CREDENTIALS = {
    "posthog": CredentialSpec(
        env_var="POSTHOG_API_KEY",
        tools=[
            "posthog_query",
            "posthog_list_events",
            "posthog_get_funnel_metrics",
            "posthog_list_cohorts",
        ],
        required=True,
        direct_api_key_supported=True,
        api_key_instructions="Create a Personal API Key in your PostHog User Settings.",
    ),
    "posthog_project_id": CredentialSpec(
        env_var="POSTHOG_PROJECT_ID",
        required=True,
        direct_api_key_supported=True,
        api_key_instructions="The ID of your PostHog project (found in Project Settings).",
    ),
    "posthog_url": CredentialSpec(
        env_var="POSTHOG_URL",
        required=False,
        direct_api_key_supported=True,
        api_key_instructions="Optional: Custom PostHog API URL (defaults to https://app.posthog.com).",
    ),
}
