"""
Integration credentials for Aden Tools.

Contains credentials for third-party integrations like Google Maps.
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "google_maps": CredentialSpec(
        env_var="GOOGLE_MAPS_API_KEY",
        tools=[
            "maps_geocode",
            "maps_reverse_geocode",
            "maps_directions",
            "maps_distance_matrix",
            "maps_place_details",
            "maps_place_search",
        ],
        required=True,
        startup_required=False,
        help_url="https://developers.google.com/maps/documentation/geocoding/get-api-key",
        description="Google Maps Platform API key",
    ),
}
