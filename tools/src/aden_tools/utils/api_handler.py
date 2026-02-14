from typing import Any
import httpx


def handle_api_response(
    response: httpx.Response,
    service_name: str = "API",
    error_map: dict[int, str | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Handle API response and map HTTP errors to human-readable messages.

    Args:
        response: The HTTP response object.
        service_name: Name of the service (e.g., "Apollo").
        error_map: Optional dictionary mapping status codes to error messages or dicts.
            - If value is str: returns {"error": value}
            - If value is dict: returns the dict as-is (useful for keys like "help")

    Returns:
        Dict returning either the JSON response (success) or an error dict.
    """
    if response.is_success:
        return response.json()

    status_code = response.status_code

    # 1. Check custom error map specifically passed for this tool
    if error_map and status_code in error_map:
        mapping = error_map[status_code]
        if isinstance(mapping, str):
            return {"error": mapping}
        return mapping

    # 2. Extract error details from response body if possible
    try:
        data = response.json()
        # Apollo specifically uses "error" key often, but sometimes just text
        detail = data.get("error", data.get("message", response.text))
    except Exception:
        detail = response.text

    # 3. Handle common status codes with generic messages if not overridden
    if status_code == 401:
        return {"error": f"Invalid {service_name} API key or unauthorized access."}
    if status_code == 403:
        return {"error": f"Access denied by {service_name} (Forbidden)."}
    if status_code == 404:
        return {"error": f"Resource not found in {service_name}."}
    if status_code == 422:
        return {"error": f"Invalid parameters sent to {service_name}: {detail}"}
    if status_code == 429:
        return {"error": f"{service_name} rate limit exceeded. Please retry later."}

    # 4. Generic catch-all
    return {"error": f"{service_name} error (HTTP {status_code}): {detail}"}
