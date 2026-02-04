"""
Google Maps Platform tool for Aden Tools.

Provides geocoding, routing, and places capabilities.
"""

import logging
from typing import Any, Optional, List, Dict, Union

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)


class _GoogleMapsClient:
    """Client for Google Maps Platform APIs."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_urls = {
            "geocode": "https://maps.googleapis.com/maps/api/geocode/json",
            "directions": "https://maps.googleapis.com/maps/api/directions/json",
            "distancematrix": "https://maps.googleapis.com/maps/api/distancematrix/json",
            "place_details": "https://maps.googleapis.com/maps/api/place/details/json",
            "place_search": "https://maps.googleapis.com/maps/api/place/textsearch/json",
            "nearby_search": "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
        }

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Google Maps API."""
        url = self.base_urls.get(endpoint)
        if not url:
            raise ValueError(f"Unknown endpoint: {endpoint}")

        params["key"] = self.api_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Google Maps HTTP error: {e}")
            raise RuntimeError(f"Google Maps HTTP error: {e}")
        except Exception as e:
            logger.error(f"Google Maps request failed: {e}")
            raise RuntimeError(f"Google Maps request failed: {e}")

        status = data.get("status")
        if status == "OK" or status == "ZERO_RESULTS":
            return data
        elif status == "OVER_QUERY_LIMIT":
            raise RuntimeError("Google Maps API limit exceeded")
        elif status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "Request denied")
            raise PermissionError(f"Google Maps API denied: {error_msg}")
        elif status == "INVALID_REQUEST":
            error_msg = data.get("error_message", "Invalid request")
            raise ValueError(f"Invalid Google Maps request: {error_msg}")
        else:
            error_msg = data.get("error_message", "Unknown error")
            raise RuntimeError(f"Google Maps API error ({status}): {error_msg}")

    def geocode(self, address: str, **kwargs) -> Dict[str, Any]:
        params = {"address": address, **kwargs}
        return self._request("geocode", params)

    def reverse_geocode(self, lat: float, lng: float, **kwargs) -> Dict[str, Any]:
        params = {"latlng": f"{lat},{lng}", **kwargs}
        return self._request("geocode", params)

    def directions(self, origin: str, destination: str, **kwargs) -> Dict[str, Any]:
        params = {"origin": origin, "destination": destination, **kwargs}
        return self._request("directions", params)

    def distance_matrix(self, origins: List[str], destinations: List[str], **kwargs) -> Dict[str, Any]:
        params = {
            "origins": "|".join(origins),
            "destinations": "|".join(destinations),
            **kwargs,
        }
        return self._request("distancematrix", params)

    def place_details(self, place_id: str, **kwargs) -> Dict[str, Any]:
        params = {"place_id": place_id, **kwargs}
        return self._request("place_details", params)

    def place_search(self, query: str, **kwargs) -> Dict[str, Any]:
        params = {"query": query, **kwargs}
        return self._request("place_search", params)
    
    def nearby_search(self, location: str, radius: int, **kwargs) -> Dict[str, Any]:
        params = {"location": location, "radius": radius, **kwargs}
        return self._request("nearby_search", params)


def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None) -> None:
    """Register Google Maps tools."""
    
    def get_client() -> _GoogleMapsClient:
        if credentials:
            api_key = credentials.get("google_maps")
        else:
            import os
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY must be set")
        return _GoogleMapsClient(api_key)

    @mcp.tool()
    def maps_geocode(
        address: str, 
        components: Optional[str] = None, 
        bounds: Optional[str] = None, 
        language: Optional[str] = None
    ) -> str:
        """
        Convert an address to coordinates (geocoding).

        Args:
            address: The address to geocode.
            components: Component filters (e.g., "country:US|postal_code:94043").
            bounds: Check documentation.
            language: Language code (e.g., "en").

        Returns:
            JSON string with geocoding results (lat/lng, place_id, etc.).
        """
        try:
            client = get_client()
            kwargs = {}
            if components: kwargs["components"] = components
            if bounds: kwargs["bounds"] = bounds
            if language: kwargs["language"] = language
            
            result = client.geocode(address, **kwargs)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error geocoding address: {str(e)}"

    @mcp.tool()
    def maps_reverse_geocode(
        lat: float, 
        lng: float, 
        result_type: Optional[str] = None, 
        language: Optional[str] = None
    ) -> str:
        """
        Convert coordinates to an address (reverse geocoding).

        Args:
            lat: Latitude.
            lng: Longitude.
            result_type: Filter by address type (e.g., "street_address").
            language: Language code.

        Returns:
            JSON string with reverse geocoding results.
        """
        try:
            client = get_client()
            kwargs = {}
            if result_type: kwargs["result_type"] = result_type
            if language: kwargs["language"] = language
            
            result = client.reverse_geocode(lat, lng, **kwargs)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error reverse geocoding: {str(e)}"

    @mcp.tool()
    def maps_directions(
        origin: str, 
        destination: str, 
        mode: Optional[str] = None,
        waypoints: Optional[str] = None,
        alternatives: Optional[bool] = None,
        avoid: Optional[str] = None,
        units: Optional[str] = None
    ) -> str:
        """
        Get directions between two points.

        Args:
            origin: Starting point (address or lat,lng or place_id).
            destination: End point.
            mode: travel mode (driving, walking, bicycling, transit).
            waypoints: | separated list of waypoints.
            alternatives: If True, provide alternative routes.
            avoid: features to avoid (tolls, highways, ferries).
            units: metric or imperial.

        Returns:
            JSON string with route details.
        """
        try:
            client = get_client()
            kwargs = {}
            if mode: kwargs["mode"] = mode
            if waypoints: kwargs["waypoints"] = waypoints
            if alternatives is not None: kwargs["alternatives"] = str(alternatives).lower()
            if avoid: kwargs["avoid"] = avoid
            if units: kwargs["units"] = units
            
            result = client.directions(origin, destination, **kwargs)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting directions: {str(e)}"

    @mcp.tool()
    def maps_distance_matrix(
        origins: List[str], 
        destinations: List[str], 
        mode: Optional[str] = None,
        avoid: Optional[str] = None,
        units: Optional[str] = None
    ) -> str:
        """
        Calculate travel distance and time for a matrix of origins and destinations.

        Args:
            origins: List of starting points.
            destinations: List of end points.
            mode: driving, walking, bicycling, transit.
            avoid: tolls, highways, ferries.
            units: metric or imperial.

        Returns:
            JSON string with distance matrix.
        """
        try:
            client = get_client()
            kwargs = {}
            if mode: kwargs["mode"] = mode
            if avoid: kwargs["avoid"] = avoid
            if units: kwargs["units"] = units
            
            result = client.distance_matrix(origins, destinations, **kwargs)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error calculating distance matrix: {str(e)}"

    @mcp.tool()
    def maps_place_details(place_id: str, fields: Optional[str] = None) -> str:
        """
        Get detailed information about a place.

        Args:
            place_id: The unique identifier for the place.
            fields: Comma-separated list of fields to return (e.g., name,formatted_address).

        Returns:
            JSON string with place details.
        """
        try:
            client = get_client()
            kwargs = {}
            if fields: kwargs["fields"] = fields
            
            result = client.place_details(place_id, **kwargs)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting place details: {str(e)}"

    @mcp.tool()
    def maps_place_search(
        query: str, 
        location: Optional[str] = None, 
        radius: Optional[int] = None,
        type: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        open_now: Optional[bool] = None
    ) -> str:
        """
        Search for places using a text query or nearby search.

        Args:
            query: Text search query (e.g., "restaurants in New York").
            location: lat,lng for specific location bias/nearby search.
            radius: Radius in meters (required if location is used without query for nearby search).
            type: Place type (e.g., restaurant).
            min_price: 0-4.
            max_price: 0-4.
            open_now: Only return open places.

        Returns:
            JSON string with search results.
        """
        try:
            client = get_client()
            kwargs = {}
            if type: kwargs["type"] = type
            if min_price is not None: kwargs["minprice"] = min_price
            if max_price is not None: kwargs["maxprice"] = max_price
            if open_now: kwargs["opennow"] = "true"
            
            if location and radius and not query:
                 # Nearby search usage
                result = client.nearby_search(location, radius, **kwargs)
            else:
                # Text search
                if location: kwargs["location"] = location
                if radius: kwargs["radius"] = radius
                result = client.place_search(query, **kwargs)
                
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error searching prices: {str(e)}"
