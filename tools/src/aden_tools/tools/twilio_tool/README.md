# Twilio Tool

SMS and WhatsApp messaging integration for Aden agents via the Twilio API.

## Description

This tool enables AI agents to send SMS and WhatsApp messages, retrieve message history, and validate phone numbers using Twilio's communication APIs. It supports both SMS and WhatsApp messaging with optional media attachments.

## Features

- Send SMS messages to any phone number
- Send WhatsApp messages with automatic prefix handling
- Fetch message history with filtering options
- Validate and format phone numbers via Twilio Lookup API
- Support for media attachments (MMS/WhatsApp media)

## Available Tools

### 1. `send_sms`

Send an SMS message to a phone number.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `to` | str | Yes | - | Recipient phone number (E.164 format, e.g., `+15551234567`) |
| `body` | str | Yes | - | Message content (up to 1600 characters) |
| `media_url` | str | No | `None` | URL of media to attach (MMS) |

**Returns:**
```json
{
  "sid": "SM...",
  "status": "queued",
  "to": "+155512xxxxx"
}
```

**Error Response:**

```json
{
  "error": "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN",
  "help": "Set env vars or configure credential store"
}
```

### 2. `send_whatsapp`
Send a WhatsApp message via Twilio's WhatsApp Business API.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `to` | str | Yes | - | Recipient WhatsApp number (can include or omit whatsapp: prefix) |
| `body` | str | Yes | - | Message content (up to 1600 characters) |
| `media_url` | str | No | `None` | URL of media to attach |

**Returns:**

```json
{
  "sid": "SM...",
  "to": "whatsapp:+15551xxxxx"
}
```

### 3. `fetch_history`
Retrieve recent message logs from Twilio.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `to` | str | No | `None` | 	Filter by recipient number |
| `limit` | int | No | 5 | Number of messages to retrieve (1-1000) |

**Returns:**

```json
{
  "messages": [
    {
      "date": "2026-02-09T14:30:00",
      "direction": "OUT",
      "from": "+155598xxxxx",
      "to": "+15551234567",
      "body": "Hello from Twilio!"
    }
  ]
}
```
### 4. `validate_number`
Validate a phone number and get formatting information.

**Arguments:**
| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `phone_number` | str | Yes | - | 	Phone number to validate (any format) |


**Returns:**

```json
{
  "valid": true,
  "formatted": "+1555123xxxx",
  "country": "US"
}
```
## Installation
1. Install Dependencies
```bash
# Install the Twilio Python SDK if not installed
pip install twilio

# Run ./quickstart.sh
./quickstart.sh

# [Optional] Install in development mode (from repository root)
cd /path/to/hive
pip install -e ./core
pip install -e ./tools
```

2. Get Twilio Credentials
- Sign up at twilio.com
- Navigate to Twilio Console
- Copy your Account SID and Auth Token
- Get a Twilio phone number or set up WhatsApp Business

## Credential Management
### Method 1: Environment Variables (Recommended for Development/Testing)
The simplest method for testing and development:

```bash
# Set credentials
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_FROM_NUMBER="+1555123xxxx"
```

## Method 2: Credential Store (Recommended for Production)
Use the Aden credential manager for encrypted storage:

## Known Issue: Non-OAuth Credential Support
**Issue:** The credential store is currently optimized for OAuth flows and has limited support for API key-based credentials like Twilio.

**Tracking:** See GitHub issue #3455 - Update credentials store to work with non-oauth keys

Temporary Workaround: Use `CredentialStoreAdapter` in `mcp_server.py` 

```Python

# Go to hive/tools/mcp_server.py and replace this 
try:
    from framework.credentials import CredentialStore

    store = CredentialStore.with_encrypted_storage()  # ~/.hive/credentials
    credentials = CredentialStoreAdapter(store)
    logger.info("Using CredentialStoreAdapter with encrypted storage")
except Exception as e:
    # Fall back to env-only adapter if encrypted storage fails
    credentials = CredentialStoreAdapter.with_env_storage()
    logger.warning(f"Falling back to env-only CredentialStoreAdapter: {e}")

# With this
from aden_tools.credentials import CredentialStoreAdapter
credentials = CredentialStoreAdapter.with_env_storage()

```

## Testing
Quick Test with MCP Inspector
The easiest way to test your Twilio integration:

Terminal 1: Start MCP Server (HTTP Transport)
```bash
# Navigate to repository root
cd /path/to/hive

# Set environment variables
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="your_token"
export TWILIO_FROM_NUMBER="+1555123xxxx"

# Set Python path
export PYTHONPATH="/path/to/hive:$PYTHONPATH"
fastmcp run tools/mcp_server.py --transport http --port 8000
```

Terminal 2: Launch MCP Inspector
```bash
# Install MCP Inspector (if not already installed)
npm install -g @modelcontextprotocol/inspector

# Connect to your MCP server
npx @modelcontextprotocol/inspector http://127.0.0.1:8000/mcp

```

The inspector will open in your browser at http://localhost:5173, allowing you to:
- View all available tools
- Test tool calls with a visual interface
- Inspect request/response payloads
- Debug credential issues

## Troubleshooting
### Credentials Not Found
**Symptom:** 
```bash
ValueError: Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN
```

**Solutions:**

- Verify environment variables are set:
```bash
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
```
- Check if .env file is being loaded:
```bash
# Create .env file in project root
cat > .env << EOF
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1555123xxxx
EOF
```
- Use the storage workaround (see "Known Issue" section above)

### Import Errors
**Symptom:** 
```bash
ModuleNotFoundError: No module named 'core' or 'aden_tools'
```
**Solution:**

```bash
# Ensure packages are installed in development mode
cd /path/to/hive
pip install -e ./core
pip install -e ./tools

# Or set PYTHONPATH
export PYTHONPATH="/path/to/hive:$PYTHONPATH"
```
### MCP Server Won't Start
**Symptom:** 
Server fails to start or returns 500 errors

Solutions:
- Check logs for specific error messages
- Verify Twilio SDK is installed: pip list | grep twilio
- Test credentials manually:

```bash
python3 << EOF
from twilio.rest import Client
client = Client("AC...", "your_token")
print(client.messages.list(limit=1))
EOF
```

## Development

### File Structure
```text
tools/src/aden_tools/tools/twilio_tool/
├── __init__.py              # Package initialization
├── twilio_tool.py          # Tool implementation
└── README.md               # This file

tools/tests/tools/
└── test_twilio_tool.py     # Unit tests
```

### Running Tests
``` bash
cd tools
pytest tests/tools/test_twilio_tool.py -v
```

## Adding New Features
- Add new tool function in twilio_tool.py
- Register with @mcp.tool() decorator
- Add docstring with argument descriptions
- Update this README with new tool documentation
- Add tests in test_twilio_tool.py

### Resources
- [Twilio SMS Quickstart](https://www.twilio.com/docs/sms/quickstart/python)
- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp/quickstart/python)
- [Fastmcp Documentation](https://github.com/jlowin/fastmcp)

### Contributing
See GitHub Issue #3455 for ongoing work on credential management improvements.