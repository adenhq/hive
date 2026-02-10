# Salesforce Tool

Interact with Salesforce data via the REST API. This tool allows the Aden agent framework to query, create, update, and manage Salesforce records.

## Installation

The Salesforce tool uses `httpx` which is already included in the base dependencies. No additional installation required.

## Setup

You need a Salesforce Connected App and an OAuth Access Token to use this tool.

### Getting Credentials

1.  **Log in to Salesforce Setup.**
2.  Go to **Apps > App Manager**.
3.  Click **New Connected App**.
4.  Enable OAuth Settings and select the `api` and `refresh_token` scopes.
5.  Save and note your **Consumer Key** and **Consumer Secret**.
6.  Use these credentials to generate an Access Token via the Salesforce OAuth flow (e.g., Device Flow or Web Server Flow).

### Configuration

Set the following environment variables:

```bash
export SALESFORCE_ACCESS_TOKEN=your_access_token_here
export SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com
```

Or configure via the credential store (recommended for production).

## Available Functions

### `salesforce_soql_query`

Execute a SOQL query to search or retrieve data from Salesforce.

**Parameters:**
- `query` (str): The SOQL query string (e.g., `SELECT Id, Name, Email FROM Contact WHERE Email LIKE '%@example.com%'`)
- `access_token` (str, optional): Override access token.
- `instance_url` (str, optional): Override instance URL.

**Returns:**
A string summary of the query results, including the total number of records found and a list of the top records.

**Example:**
```python
salesforce_soql_query("SELECT Id, Name, StageName FROM Opportunity WHERE IsClosed = false")
```

### `salesforce_get_record`

Retrieve a single record from Salesforce by ID.

**Parameters:**
- `sobject` (str): The API name of the object (e.g., "Account", "Contact").
- `record_id` (str): The 15 or 18 character Salesforce ID.
- `fields` (list[str], optional): specific fields to retrieve.

**Returns:**
A string representation of the record data.

**Example:**
```python
salesforce_get_record("Account", "001xxxxxxxxxxxx", fields=["Name", "BillingCity"])
```

### `salesforce_create_record`

Create a new record in Salesforce.

**Parameters:**
- `sobject` (str): The API name of the object.
- `data` (dict): A dictionary of field API names and values.

**Returns:**
Success message with the new record ID, or an error message.

**Example:**
```python
salesforce_create_record("Lead", {"FirstName": "John", "LastName": "Doe", "Company": "Acme Corp"})
```

### `salesforce_update_record`

Update an existing record in Salesforce.

**Parameters:**
- `sobject` (str): The API name of the object.
- `record_id` (str): The ID of the record to update.
- `data` (dict): A dictionary of fields to update.

**Returns:**
Success message or error message.

**Example:**
```python
salesforce_update_record("Contact", "003xxxxxxxxxxxx", {"Title": "VP of Sales"})
```

### `salesforce_get_limits`

Check API usage limits for the Salesforce organization.

**Returns:**
A string summary of API usage (e.g., `API Usage: {'Max': 15000, 'Remaining': 14500}`).

**Example:**
```python
salesforce_get_limits()
```

## Error Handling

All functions return a descriptive string starting with "Error: ..." or containing specific error details if the API call fails (e.g., invalid query, record not found, permission denied).
