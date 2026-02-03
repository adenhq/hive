"""
BigQuery tool credentials.

Contains credentials for Google BigQuery data warehouse access.
"""

from .base import CredentialSpec

BIGQUERY_CREDENTIALS = {
    "bigquery_credentials": CredentialSpec(
        env_var="GOOGLE_APPLICATION_CREDENTIALS",
        tools=["run_bigquery_query", "describe_dataset"],
        node_types=[],
        required=False,  # Falls back to ADC if not set
        startup_required=False,
        help_url="https://cloud.google.com/bigquery/docs/authentication/service-account-file",
        description="Path to Google Cloud service account JSON file for BigQuery access",
    ),
    "bigquery_project": CredentialSpec(
        env_var="BIGQUERY_PROJECT_ID",
        tools=["run_bigquery_query", "describe_dataset"],
        node_types=[],
        required=False,  # Can be specified per-call or inferred from credentials
        startup_required=False,
        help_url="https://cloud.google.com/resource-manager/docs/creating-managing-projects",
        description="Default Google Cloud project ID for BigQuery queries",
    ),
}
