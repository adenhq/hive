# Salesforce CRM Tool

A FastMCP-compatible tool for integrating Salesforce CRM capabilities into the Hive framework. This tool allows identifying and managing leads, contacts, and opportunities, as well as executing custom SOQL queries.

## Features

- **SOQL Queries**: Execute any Salesforce Object Query Language (SOQL) query.
- **CRUD Operations**: Create, Read, and Update any Salesforce object (Leads, Contacts, Opportunities, etc.).
- **Object Metadata**: Describe Salesforce objects to understand fields and picklist values.
- **Convenience Search**: Simple tools to search for Leads, Contacts, and Opportunities.

## Available Tools

- `salesforce_query`: Execute a SOQL query.
- `salesforce_create_record`: Create a new record in Salesforce.
- `salesforce_update_record`: Update an existing record.
- `salesforce_get_record`: Get a record by ID.
- `salesforce_describe_object`: Get object metadata.
- `salesforce_search_leads`: Search leads by name or email.
- `salesforce_search_contacts`: Search contacts by name or email.
- `salesforce_search_opportunities`: Search opportunities by name.

## Configuration

The tool requires a Salesforce instance URL and an OAuth2 access token.

### Environment Variables

- `SALESFORCE_INSTANCE_URL`: Your Salesforce instance URL (e.g., `https://na1.salesforce.com`).
- `SALESFORCE_ACCESS_TOKEN`: A valid Salesforce API access token.

### Setup Instructions

1.  Log in to your Salesforce account.
2.  If you haven't already, create a Connected App to obtain OAuth2 credentials.
3.  Ensure your Connected App has the `api` scope.
4.  Obtain an access token using your preferred OAuth2 flow (e.g., Web Server Flow, JWT Bearer Flow).

## Usage Examples

### Search for a Lead

```python
results = salesforce_search_leads(query="John Doe")
# Returns a list of matching leads with their IDs and emails.
```

### Create a New Lead

```python
new_lead = salesforce_create_record(
    object_name="Lead",
    fields={
        "FirstName": "Jane",
        "LastName": "Smith",
        "Company": "Innovate LLC",
        "Email": "jane.smith@innovate.com",
        "Status": "Open - Not Contacted"
    }
)
```

### Run a Custom Query

```python
high_value_opps = salesforce_query(
    soql_query="SELECT Id, Name, Amount FROM Opportunity WHERE Amount > 100000"
)
```

## API Version

By default, the tool uses Salesforce REST API `v60.0`.
