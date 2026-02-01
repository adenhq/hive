# Airtable Tool

The Airtable tool provides comprehensive integration with the Airtable API, enabling agents to read and write data in Airtable bases.

## Use Cases

- **CRM Management**: Sync leads and contacts between systems
- **Project Tracking**: Update task statuses and assignments
- **Content Calendars**: Manage and schedule content
- **Data Collection**: Aggregate form responses and survey data

### Example Workflow

> "When a lead is qualified in Slack, create a row in our Airtable 'Leads' base and set status to 'Contacted'."

## Available Tools

### `airtable_list_bases`

Lists all Airtable bases accessible with the configured API key.

**Returns:**
- List of bases with `id`, `name`, and `permissionLevel`

**Example Response:**
```json
{
  "bases": [
    {
      "id": "appXXXXXXXXX",
      "name": "Sales CRM",
      "permissionLevel": "owner"
    }
  ]
}
```

### `airtable_list_tables`

Lists all tables in a specified base, including field schemas.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_id` | string | Yes | The base ID (e.g., `appXXXXXXX`) |

**Returns:**
- List of tables with `id`, `name`, `description`, and `fields`

### `airtable_list_records`

Lists records in a table with optional filtering and sorting.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_id` | string | Yes | The base ID |
| `table_id_or_name` | string | Yes | Table ID or name |
| `filter_by_formula` | string | No | Airtable formula filter (e.g., `{Status}='Active'`) |
| `sort_field` | string | No | Field name to sort by |
| `sort_direction` | string | No | Sort direction (`asc` or `desc`) |
| `max_records` | int | No | Maximum records to return |
| `fields` | string | No | Comma-separated list of fields to return |

**Example Usage:**
```python
# Filter for active leads, sorted by creation date
airtable_list_records(
    base_id="appXXXXXX",
    table_id_or_name="Leads",
    filter_by_formula="{Status}='Active'",
    sort_field="Created",
    sort_direction="desc",
    max_records=50
)
```

### `airtable_create_record`

Creates a new record in a table.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_id` | string | Yes | The base ID |
| `table_id_or_name` | string | Yes | Table ID or name |
| `fields_json` | string | Yes | JSON object of field values |
| `typecast` | bool | No | Enable automatic type conversion |

**Example:**
```python
airtable_create_record(
    base_id="appXXXXXX",
    table_id_or_name="Leads",
    fields_json='{"Name": "John Doe", "Email": "john@example.com", "Status": "Contacted"}'
)
```

### `airtable_update_record`

Updates an existing record by its ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_id` | string | Yes | The base ID |
| `table_id_or_name` | string | Yes | Table ID or name |
| `record_id` | string | Yes | Record ID (e.g., `recXXXXXX`) |
| `fields_json` | string | Yes | JSON object of fields to update |
| `typecast` | bool | No | Enable automatic type conversion |

## Authentication

### Personal Access Token (Recommended)

1. Go to [Airtable Token Creation](https://airtable.com/create/tokens)
2. Create a new token with the required scopes:
   - `data.records:read` - Read records
   - `data.records:write` - Create/update records
   - `schema.bases:read` - List bases and tables
3. Add the token to your `.env` file:

```bash
AIRTABLE_API_KEY=pat.XXXXXXXX.YYYYYYYYY
```

### Required Scopes

| Scope | Required For |
|-------|--------------|
| `data.records:read` | `airtable_list_records` |
| `data.records:write` | `airtable_create_record`, `airtable_update_record` |
| `schema.bases:read` | `airtable_list_bases`, `airtable_list_tables` |

## Credential Specification

The Airtable tool follows the project's credential management pattern:

```python
from aden_tools.credentials import AIRTABLE_CREDENTIALS

# Credential spec
AIRTABLE_CREDENTIALS = {
    "airtable_api_key": CredentialSpec(
        env_var="AIRTABLE_API_KEY",
        tools=[
            "airtable_list_bases",
            "airtable_list_tables",
            "airtable_list_records",
            "airtable_create_record",
            "airtable_update_record",
        ],
        required=True,
        description="Personal Access Token for Airtable API",
        help_url="https://airtable.com/create/tokens",
    ),
}
```

## Error Handling

All tools return JSON responses. Errors are returned in this format:

```json
{
  "error": "Airtable API error: 403",
  "details": "AUTHENTICATION_REQUIRED: The request requires valid authentication credentials."
}
```

Common error codes:
- `401` - Invalid or expired API key
- `403` - Insufficient permissions (check token scopes)
- `404` - Base, table, or record not found
- `422` - Invalid field values or formula syntax

## Rate Limits

Airtable enforces rate limits of 5 requests per second per base. The tool handles pagination automatically but does not implement rate limiting. For high-volume operations, consider adding delays between requests.

## Airtable Formula Reference

For `filter_by_formula`, use Airtable's formula syntax:

| Operation | Formula Example |
|-----------|-----------------|
| Equals | `{Status}='Active'` |
| Not equals | `{Status}!='Closed'` |
| Contains | `FIND('john', LOWER({Email}))` |
| Greater than | `{Amount}>1000` |
| AND | `AND({Status}='Active', {Priority}='High')` |
| OR | `OR({Status}='New', {Status}='Open')` |

See [Airtable Formula Reference](https://support.airtable.com/docs/formula-field-reference) for more.
