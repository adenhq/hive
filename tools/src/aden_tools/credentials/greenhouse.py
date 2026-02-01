"""Credentials for Greenhouse integration."""

from .base import CredentialSpec

GREENHOUSE_CREDENTIALS = {
    "greenhouse_api_key": CredentialSpec(
        env_var="GREENHOUSE_API_KEY",
        description="Greenhouse Harvest API Key for recruiting automation",
        required=False,  # Optional unless Greenhouse tools are used
    ),
}
