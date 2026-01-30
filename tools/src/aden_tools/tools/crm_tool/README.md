# CRM Tool

Manage customer relationship data with CRUD operations.

## Tools

| Tool | Description |
|------|-------------|
| `crm_create_contact` | Create a new contact |
| `crm_update_contact` | Update existing contact |
| `crm_get_contact` | Retrieve contact by ID or email |
| `crm_search_contacts` | Search contacts with filters |
| `crm_delete_contact` | Remove a contact |
| `crm_log_activity` | Log interaction for a contact |

## Storage Modes

1. **In-Memory (Default)**: Data persists only during session
2. **File-Based**: Set `CRM_STORAGE_PATH` environment variable

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| CRM_STORAGE_PATH | No | Path to JSON file for persistent storage |

## Examples

```python
# Create a contact
crm_create_contact(
    name="Jane Doe",
    email="jane@example.com",
    company="Acme Corp",
    tags=["lead", "enterprise"]
)

# Search contacts
crm_search_contacts(query="enterprise", limit=10)

# Log an activity
crm_log_activity(
    contact_id="contact_20260130...",
    activity_type="call",
    description="Discussed pricing options",
    outcome="Scheduled follow-up"
)
```
