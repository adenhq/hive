# Pipedrive CRM Tool

Manage persons, deals, and notes in Pipedrive.

## Credentials

The tool requires a Pipedrive Personal API Token.

- **Environment Variable**: `PIPEDRIVE_API_TOKEN`
- **Credential Name**: `pipedrive` (key: `api_token`)

To get a Pipedrive API token:
1. Log in to your Pipedrive account.
2. Go to Settings > Personal preferences > API.
3. Find your personal API token and copy it.

## Tools

### Persons
- `pipedrive_create_person`: Create a new person with name, email, and phone.
- `pipedrive_search_person`: Search for a person by email (exact match).
- `pipedrive_get_person_details`: Get full details of a person by ID.

### Deals
- `pipedrive_create_deal`: Create a new deal with title, person ID, value, and currency.
- `pipedrive_update_deal_stage`: Update the stage of an existing deal.
- `pipedrive_list_deals`: List deals with status filtering (default: 'open').

### Notes
- `pipedrive_add_note_to_deal`: Add a note (interaction summary, research) to a deal.

## API Reference
https://developers.pipedrive.com/docs/api/v1
