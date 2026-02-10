# Generic API Connector Tool

Call any third-party or internal REST API without building a custom integration.

## Description

Provides a thin, validated HTTP interface that agents can safely call without
embedding raw HTTP logic in prompts. Users supply their own API credentials and
endpoint configurations. Supports multiple auth methods and automatic retries
with exponential backoff.

## Tools

| Tool | Description |
|------|-------------|
| `generic_api_get` | Convenience GET request wrapper |
| `generic_api_post` | Convenience POST request wrapper |
| `generic_api_request` | Full HTTP verb support (GET, POST, PUT, PATCH, DELETE) |

## Auth Methods

| Method | `auth_method` value | How it works |
|--------|---------------------|--------------|
| Bearer Token | `bearer` (default) | `Authorization: Bearer {token}` |
| API Key | `api_key` | `Authorization: ApiKey {key}` |
| Basic Auth | `basic` | `Authorization: Basic {base64(user:pass)}` |
| Custom Header | `custom_header` | `{custom_header_name}: {token}` |
| Query Parameter | `query_param` | `?{query_param_name}={token}` |
| No Auth | `none` | No authentication applied |

## Arguments

### `generic_api_get` / `generic_api_post` / `generic_api_request`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | — | Full URL to call (max 2048 chars) |
| `method` | str | No | `GET` | HTTP method (`generic_api_request` only) |
| `body` | dict | No | `None` | JSON body (POST/PUT/PATCH only) |
| `auth_method` | str | No | `bearer` | Auth method (see table above) |
| `custom_header_name` | str | No | `X-API-Key` | Header key for `custom_header` auth |
| `query_param_name` | str | No | `api_key` | Query key for `query_param` auth |
| `extra_headers` | dict | No | `None` | Additional request headers |
| `params` | dict | No | `None` | Additional query-string parameters |
| `timeout` | float | No | `30.0` | Request timeout in seconds |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GENERIC_API_TOKEN` | Yes (unless `auth_method=none`) | API token/key for the target API |

## Example Usage

```python
# GET from an internal inventory API
result = generic_api_get(
    url="https://internal.erp.company.com/api/v1/inventory",
    auth_method="bearer",
)

# POST to create a resource with Basic Auth
result = generic_api_post(
    url="https://legacy.billing.com/invoices",
    body={"customer_id": "C-1234", "amount": 99.99},
    auth_method="basic",  # GENERIC_API_TOKEN = "user:password"
)

# PUT with a custom header
result = generic_api_request(
    url="https://api.example.com/v2/records/42",
    method="PUT",
    body={"status": "approved"},
    auth_method="custom_header",
    custom_header_name="X-Service-Token",
)

# No auth required
result = generic_api_get(
    url="https://api.open-data.gov/datasets",
    auth_method="none",
)
```

## Error Handling

Returns structured error dicts:
- `GENERIC_API_TOKEN not configured` — credential not set
- `URL must be 1–2048 characters` — invalid URL length
- `Unsupported HTTP method` — method not in GET/POST/PUT/PATCH/DELETE
- `Request timed out` — exceeded timeout (default 30s)
- `Network error: ...` — connection / DNS error

Automatic retries (up to 3) with exponential backoff on:
- HTTP 429 (Rate Limited)
- HTTP 500, 502, 503, 504 (Server Error)
- Network timeouts

## Health Check

Configure a lightweight health-check endpoint in the credential spec.
The connector interprets:
- **200**: Credential valid
- **401**: Invalid or expired credential
- **403**: Insufficient permissions
- **429**: Rate limited (credential still valid)
