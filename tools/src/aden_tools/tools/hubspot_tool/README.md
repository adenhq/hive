# HubSpot Tool

Manage contacts, companies, and deals via HubSpot CRM API v3.

## Setup

```bash
# Option 1: Private App token (recommended for testing)
export HUBSPOT_ACCESS_TOKEN=pat-na1-your-private-app-token-here

# Option 2: OAuth2 via credential store
# Configure through Hive credential management
```

To get a Private App token:
1. Go to HubSpot → Settings → Integrations → Private Apps
2. Create new app with scopes:
   - `crm.objects.contacts.read`, `crm.objects.contacts.write`
   - `crm.objects.companies.read`, `crm.objects.companies.write`
   - `crm.objects.deals.read`, `crm.objects.deals.write`
3. Copy the access token

## All Tools (12 Total)

### Contacts (4)
| Tool | Description |
|------|-------------|
| `hubspot_search_contacts` | Search contacts by name, email, phone, etc. |
| `hubspot_get_contact` | Get a single contact by ID |
| `hubspot_create_contact` | Create a new contact |
| `hubspot_update_contact` | Update existing contact |

### Companies (4)
| Tool | Description |
|------|-------------|
| `hubspot_search_companies` | Search companies by name, domain, etc. |
| `hubspot_get_company` | Get a single company by ID |
| `hubspot_create_company` | Create a new company |
| `hubspot_update_company` | Update existing company |

### Deals (4)
| Tool | Description |
|------|-------------|
| `hubspot_search_deals` | Search deals by name, amount, stage, etc. |
| `hubspot_get_deal` | Get a single deal by ID |
| `hubspot_create_deal` | Create a new deal |
| `hubspot_update_deal` | Update existing deal |

## Example Usage

```python
# Search contacts
hubspot_search_contacts(query="john@example.com", properties=["email", "firstname", "lastname"])

# Get contact details
hubspot_get_contact(contact_id="12345", properties=["email", "phone", "company"])

# Create new contact
hubspot_create_contact(properties={
    "email": "new@example.com",
    "firstname": "John",
    "lastname": "Doe",
    "phone": "+1234567890"
})

# Update contact
hubspot_update_contact(contact_id="12345", properties={"phone": "+9876543210"})

# Search companies
hubspot_search_companies(query="Acme Corp", properties=["name", "domain", "website"])

# Create deal
hubspot_create_deal(properties={
    "dealname": "New Opportunity",
    "amount": "50000",
    "dealstage": "appointmentscheduled",
    "pipeline": "default"
})
```

## Common Properties

### Contact Properties
- `email`, `firstname`, `lastname`, `phone`
- `company`, `website`, `jobtitle`, `address`
- `lifecyclestage`, `leadsource`

### Company Properties
- `name`, `domain`, `website`, `phone`
- `industry`, `numberofemployees`, `annualrevenue`
- `country`, `state`, `city`

### Deal Properties
- `dealname`, `amount`, `closedate`, `dealstage`
- `pipeline`, `probability`, `description`
- `hubspot_owner_id`, `dealtype`

## Error Codes

| Error | Meaning |
|-------|---------|
| `Invalid or expired HubSpot access token` | Token is invalid or has expired |
| `Insufficient permissions` | Token lacks required scope for this operation |
| `Resource not found` | Object ID doesn't exist or no access |
| `HubSpot rate limit exceeded` | API rate limit hit, retry later |
| `Request timed out` | Network request timed out |
| `Network error` | Failed to connect to HubSpot API |

## API Reference

Full HubSpot CRM API documentation: https://developers.hubspot.com/docs/api/crm

## Tips

- Use `limit` parameter to control results (max 100)
- Specify only the properties you need to improve performance
- Search is case-insensitive and searches across all text properties
- For OAuth2, configure credentials through Hive's credential management system
