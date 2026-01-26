# HTTP Request Tool

Make HTTP requests to any URL. Supports REST APIs, webhooks, and general HTTP endpoints.

## Description

A flexible HTTP client tool that supports all common HTTP methods, custom headers, JSON/form bodies, query parameters, and configurable timeouts. Includes built-in SSRF protection to prevent requests to internal/private networks.

## Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The full URL to request (must start with http:// or https://) |
| `method` | str | No | `GET` | HTTP method - GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS |
| `headers` | dict | No | `None` | HTTP headers dict (e.g., `{"Authorization": "Bearer token"}`) |
| `body` | str | No | `None` | Raw request body as string |
| `json_body` | dict | No | `None` | Request body as dict (auto JSON-encoded, sets Content-Type) |
| `params` | dict | No | `None` | Query parameters dict (appended to URL) |
| `timeout` | int | No | `30` | Request timeout in seconds (1-120) |
| `follow_redirects` | bool | No | `True` | Whether to follow HTTP redirects |
| `allow_private_ips` | bool | No | `False` | Allow requests to private/internal IPs (security override) |

## Usage Examples

### Basic GET Request

```python
result = http_request(url="https://api.example.com/users")
# Returns: {"status_code": 200, "body": [...], "is_json": True, ...}
```

### POST with JSON Body

```python
result = http_request(
    url="https://api.example.com/users",
    method="POST",
    json_body={"name": "Alice", "email": "alice@example.com"},
    headers={"Authorization": "Bearer my-token"}
)
```

### GET with Query Parameters

```python
result = http_request(
    url="https://api.example.com/search",
    params={"q": "python", "limit": 10}
)
# Requests: https://api.example.com/search?q=python&limit=10
```

### PUT with Custom Headers

```python
result = http_request(
    url="https://api.example.com/users/123",
    method="PUT",
    json_body={"name": "Updated Name"},
    headers={
        "Authorization": "Bearer token",
        "X-Custom-Header": "value"
    }
)
```

### POST with Raw Body

```python
result = http_request(
    url="https://api.example.com/webhook",
    method="POST",
    body="raw text content",
    headers={"Content-Type": "text/plain"}
)
```

## Response Format

### Success Response

```python
{
    "status_code": 200,
    "headers": {
        "content-type": "application/json",
        "x-request-id": "abc123",
        ...
    },
    "body": {"data": [...]},  # Parsed JSON if content-type is application/json
    "is_json": True,
    "elapsed_ms": 245
}
```

### Error Response

```python
{
    "error": "Request timed out after 30 seconds"
}
```

## Error Handling

Returns error dicts for common issues:

| Error | Cause |
|-------|-------|
| `URL is required` | Empty URL provided |
| `URL must start with http:// or https://` | Invalid URL scheme |
| `URL must include a hostname` | Malformed URL |
| `Requests to {host} are not allowed` | Blocked host (localhost, metadata endpoints) |
| `Requests to private/internal IP addresses are not allowed` | SSRF protection triggered |
| `Invalid HTTP method: {method}` | Unsupported HTTP method |
| `Cannot specify both 'body' and 'json_body'` | Conflicting body parameters |
| `Request timed out after {n} seconds` | Request exceeded timeout |
| `Too many redirects` | Redirect loop detected |
| `Connection failed: {error}` | Network/DNS error |
| `Request failed: {error}` | General HTTP error |

## Security Features

### SSRF Protection

By default, the tool blocks requests to:

- **Localhost**: `localhost`, `127.0.0.1`, `0.0.0.0`
- **Cloud metadata endpoints**: `169.254.169.254`, `metadata.google.internal`
- **Private IP ranges**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **IPv6 private/link-local addresses**

To allow internal requests (e.g., for testing), set `allow_private_ips=True`:

```python
result = http_request(
    url="http://192.168.1.100/api/internal",
    allow_private_ips=True  # Override SSRF protection
)
```

### Response Size Limit

Text responses are truncated at 1MB to prevent memory issues.

## Environment Variables

This tool does not require any environment variables. For APIs requiring authentication, pass tokens via the `headers` parameter.

## Notes

- Uses `httpx` library for HTTP requests
- Automatically parses JSON responses when `Content-Type: application/json`
- Timeout is clamped to 1-120 seconds
- Follows redirects by default (configurable)
