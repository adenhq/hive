---
description: Set up and install credentials for an agent. Detects missing credentials from agent config, collects them from the user, and stores them securely in the encrypted credential store at ~/.hive/credentials.
name: Setup Credentials
tools: ['agent-builder/*', 'tools/*']
target: vscode
---

# Setup Credentials

Interactive credential setup for agents with multiple authentication options. Detects what's missing, offers auth method choices, validates with health checks, and stores credentials securely.

## When to Use

- Before running or testing an agent for the first time
- When `AgentRunner.run()` fails with "missing required credentials"
- When a user asks to configure credentials for an agent
- After building a new agent that uses tools requiring API keys

## Workflow

### Step 1: Identify the Agent

Determine which agent needs credentials. The user will either:

- Name the agent directly (e.g., "set up credentials for hubspot-agent")
- Have an agent directory open (check `exports/` for agent dirs)
- Be working on an agent in the current session

Locate the agent's directory under `exports/{agent_name}/`.

### Step 2: Detect Required Credentials

Read the agent's configuration to determine which tools and node types it uses:

```python
from core.framework.runner import AgentRunner

runner = AgentRunner.load("exports/{agent_name}")
validation = runner.validate()

# validation.missing_credentials contains env var names
# validation.warnings contains detailed messages with help URLs
```

Alternatively, check the credential store directly:

```python
from core.framework.credentials import CredentialStore

# Use encrypted storage (default: ~/.hive/credentials)
store = CredentialStore.with_encrypted_storage()

# Check what's available
available = store.list_credentials()
print(f"Available credentials: {available}")

# Check if specific credential exists
if store.is_available("hubspot"):
    print("HubSpot credential found")
else:
    print("HubSpot credential missing")
```

To see all known credential specs (for help URLs and setup instructions):

```python
from aden_tools.credentials import CREDENTIAL_SPECS

for name, spec in CREDENTIAL_SPECS.items():
    print(f"{name}: env_var={spec.env_var}, aden={spec.aden_supported}")
```

### Step 3: Present Auth Options

For each missing credential, check available authentication methods:

```python
from aden_tools.credentials import CREDENTIAL_SPECS

spec = CREDENTIAL_SPECS.get("hubspot")
if spec:
    auth_options = []
    if spec.aden_supported:
        auth_options.append("aden")
    if spec.direct_api_key_supported:
        auth_options.append("direct")
    auth_options.append("custom")

    # Get setup info
    setup_info = {
        "env_var": spec.env_var,
        "description": spec.description,
        "help_url": spec.help_url,
        "api_key_instructions": spec.api_key_instructions,
    }
```

Present options:

```
Choose how to configure HUBSPOT_ACCESS_TOKEN:

  1) Aden Authorization Server (Recommended)
     Secure OAuth2 flow via integration.adenhq.com
     - Quick setup with automatic token refresh
     - No need to manage API keys manually

  2) Direct API Key
     Enter your own API key manually
     - Requires creating a HubSpot Private App
     - Full control over scopes and permissions

  3) Custom Credential Store (Advanced)
     Programmatic configuration for CI/CD
     - For automated deployments
     - Requires manual API calls
```

### Step 4: Execute Auth Flow

#### Option 1: Aden Authorization Server

This is the recommended flow for supported integrations (HubSpot, etc.).

**How Aden OAuth Works:**

The ADEN_API_KEY represents a user who has already completed OAuth authorization on Aden's platform. When users sign up and connect integrations on Aden, those OAuth tokens are stored server-side. Having an ADEN_API_KEY means:

1. User has an Aden account
2. User has already authorized integrations (HubSpot, etc.) via OAuth on Aden
3. We just need to sync those credentials down to the local credential store

**4.1a. Check for ADEN_API_KEY**

```python
import os
aden_key = os.environ.get("ADEN_API_KEY")
```

If not set, guide user to Aden:

```python
from aden_tools.credentials import open_browser, get_aden_setup_url

url = get_aden_setup_url()
success, msg = open_browser(url)

print("Sign in to Aden and connect your integrations.")
print("Copy your API key and return here.")
```

Ask user to provide the ADEN_API_KEY they received.

**4.1b. Save ADEN_API_KEY to Shell Config**

With user approval, persist ADEN_API_KEY to their shell config:

```python
from aden_tools.credentials import (
    detect_shell,
    add_env_var_to_shell_config,
    get_shell_source_command,
)

shell_type = detect_shell()  # 'bash', 'zsh', or 'unknown'

# Ask user for approval first
success, config_path = add_env_var_to_shell_config(
    "ADEN_API_KEY",
    user_provided_key,
    comment="Aden authorization server API key"
)

if success:
    source_cmd = get_shell_source_command()
    print(f"Saved to {config_path}")
    print(f"Run: {source_cmd}")
```

Also save to `~/.hive/configuration.json` for the framework:

```python
import json
from pathlib import Path

config_path = Path.home() / ".hive" / "configuration.json"
config = json.loads(config_path.read_text()) if config_path.exists() else {}

config["aden"] = {
    "api_key_configured": True,
    "api_url": "https://api.adenhq.com"
}

config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config, indent=2))
```

**4.1c. Sync Credentials from Aden Server**

Since the user has already authorized integrations on Aden, use the one-liner factory method:

```python
from core.framework.credentials import CredentialStore

# Single call handles everything
# This single call handles everything:
# - Creates encrypted local storage at ~/.hive/credentials
# - Configures Aden client from ADEN_API_KEY env var
# - Syncs all credentials from Aden server automatically
store = CredentialStore.with_aden_sync(
    base_url="https://api.adenhq.com",
    auto_sync=True,
)

# Check what was synced
synced = store.list_credentials()
print(f"Synced credentials: {synced}")

# If the required credential wasn't synced, the user hasn't authorized it on Aden yet
if "hubspot" not in synced:
    print("HubSpot not found in your Aden account.")
    print("Please visit https://integration.adenhq.com to connect HubSpot, then try again.")
```

For more control over the sync process:

```python
from core.framework.credentials import CredentialStore
from core.framework.credentials.aden import (
    AdenCredentialClient,
    AdenClientConfig,
    AdenSyncProvider,
)

# Create client (API key loaded from ADEN_API_KEY env var)
client = AdenCredentialClient(AdenClientConfig(
    base_url="https://api.adenhq.com",
))

# Create provider and store
provider = AdenSyncProvider(client=client)
store = CredentialStore.with_encrypted_storage()

# Manual sync
synced_count = provider.sync_all(store)
print(f"Synced {synced_count} credentials from Aden")
```

**4.1d. Run Health Check**

```python
from aden_tools.credentials import check_credential_health

cred = store.get_credential("hubspot")
token = cred.keys["access_token"].value.get_secret_value()

result = check_credential_health("hubspot", token)
if result.valid:
    print("HubSpot credentials validated!")
else:
    print(f"Validation failed: {result.message}")
    # Offer to retry the OAuth flow
```

#### Option 2: Direct API Key

For users who prefer manual API key management.

**4.2a. Show Setup Instructions**

```python
from aden_tools.credentials import CREDENTIAL_SPECS

spec = CREDENTIAL_SPECS.get("hubspot")
if spec and spec.api_key_instructions:
    print(spec.api_key_instructions)
# Output:
# To get a HubSpot Private App token:
# 1. Go to HubSpot Settings > Integrations > Private Apps
# 2. Click "Create a private app"
# 3. Name your app (e.g., "Hive Agent")
# ...

if spec and spec.help_url:
    print(f"More info: {spec.help_url}")
```

**4.2b. Collect API Key from User**

Use AskUserQuestion to securely collect the API key:

```
Please provide your HubSpot access token:
(This will be stored securely in ~/.hive/credentials)
```

**4.2c. Run Health Check Before Storing**

```python
from aden_tools.credentials import check_credential_health

result = check_credential_health("hubspot", user_provided_token)
if not result.valid:
    print(f"Warning: {result.message}")
    # Ask user if they want to:
    # 1. Try a different token
    # 2. Continue anyway (not recommended)
```

**4.2d. Store in Encrypted Credential Store**

```python
from core.framework.credentials import CredentialStore, CredentialObject, CredentialKey
from pydantic import SecretStr

store = CredentialStore.with_encrypted_storage()

cred = CredentialObject(
    id="hubspot",
    name="HubSpot Access Token",
    keys={
        "access_token": CredentialKey(
            name="access_token",
            value=SecretStr(user_provided_token),
        )
    },
)
store.save_credential(cred)
```

**4.2e. Export to Current Session**

```bash
export HUBSPOT_ACCESS_TOKEN="the-value"
```

#### Option 3: Custom Credential Store (Advanced)

For programmatic/CI/CD setups.

**4.3a. Show Documentation**

```
For advanced credential management, you can use the CredentialStore API directly:

  from core.framework.credentials import CredentialStore, CredentialObject, CredentialKey
  from pydantic import SecretStr

  store = CredentialStore.with_encrypted_storage()

  cred = CredentialObject(
      id="hubspot",
      name="HubSpot Access Token",
      keys={"access_token": CredentialKey(name="access_token", value=SecretStr("..."))}
  )
  store.save_credential(cred)

For CI/CD environments:
  - Set HIVE_CREDENTIAL_KEY for encryption
  - Pre-populate ~/.hive/credentials programmatically
  - Or use environment variables directly (HUBSPOT_ACCESS_TOKEN)

Documentation: See core/framework/credentials/README.md
```

### Step 5: Record Configuration Method

```python
import json
from pathlib import Path
from datetime import datetime

config_path = Path.home() / ".hive" / "configuration.json"
config = json.loads(config_path.read_text()) if config_path.exists() else {}

if "credential_methods" not in config:
    config["credential_methods"] = {}

config["credential_methods"]["hubspot"] = {
    "method": "aden",
    "configured_at": datetime.now().isoformat(),
}

config_path.write_text(json.dumps(config, indent=2))
```

### Step 6: Verify All Credentials

```python
runner = AgentRunner.load("exports/{agent_name}")
validation = runner.validate()
assert not validation.missing_credentials
```

## Health Check Reference

Health checks validate credentials by making lightweight API calls:

| Credential     | Endpoint                                | What It Checks                    |
| -------------- | --------------------------------------- | --------------------------------- |
| `hubspot`      | `GET /crm/v3/objects/contacts?limit=1`  | Bearer token validity, CRM scopes |
| `brave_search` | `GET /res/v1/web/search?q=test&count=1` | API key validity                  |

```python
from aden_tools.credentials import check_credential_health

result = check_credential_health("hubspot", token_value)
# result.valid: bool
# result.message: str
# result.details: dict (status_code, rate_limited, etc.)
```

## Encryption Key (HIVE_CREDENTIAL_KEY)

The encrypted credential store requires `HIVE_CREDENTIAL_KEY`:

- If not set, `EncryptedFileStorage` auto-generates one
- User MUST persist this key (in `~/.bashrc` or secrets manager)
- Without this key, credentials cannot be decrypted
- This is the ONLY secret that should live in `~/.bashrc` or environment config

If `HIVE_CREDENTIAL_KEY` is not set:

1. Let the store generate one
2. Tell the user to save it: `export HIVE_CREDENTIAL_KEY="{generated_key}"`
3. Recommend adding it to `~/.bashrc` or their shell profile

## Security Rules

- **NEVER** log, print, or echo credential values
- **NEVER** store credentials in plaintext files
- **NEVER** hardcode credentials in source code
- **ALWAYS** use `SecretStr` from Pydantic
- **ALWAYS** use encrypted credential store
- **ALWAYS** run health checks before storing
- **ALWAYS** verify with re-validation, not by reading back
- **ALWAYS** confirm before modifying shell config

## Credential Sources Reference

All credential specs are defined in `tools/src/aden_tools/credentials/`:

| File              | Category      | Credentials                                   | Aden Supported |
| ----------------- | ------------- | --------------------------------------------- | -------------- |
| `llm.py`          | LLM Providers | `anthropic`                                   | No             |
| `search.py`       | Search Tools  | `brave_search`, `google_search`, `google_cse` | No             |
| `integrations.py` | Integrations  | `hubspot`                                     | Yes            |

**Note:** Additional LLM providers (Cerebras, Groq, OpenAI) are handled by LiteLLM via environment
variables (`CEREBRAS_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`) but are not yet in CREDENTIAL_SPECS.
Add them to `llm.py` as needed.

To check what's registered:

```python
from aden_tools.credentials import CREDENTIAL_SPECS
for name, spec in CREDENTIAL_SPECS.items():
    print(f"{name}: aden={spec.aden_supported}, direct={spec.direct_api_key_supported}")
```

## Migration: CredentialManager → CredentialStore

**CredentialManager is deprecated.** Use CredentialStore.

| Old (Deprecated)                          | New (Recommended)                                                    |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `CredentialManager()`                     | `CredentialStore.with_encrypted_storage()`                           |
| `creds.get("hubspot")`                    | `store.get("hubspot")` or `store.get_key("hubspot", "access_token")` |
| `creds.validate_for_tools(tools)`         | Use `store.is_available(cred_id)` per credential                     |
| `creds.get_auth_options("hubspot")`       | Check `CREDENTIAL_SPECS["hubspot"].aden_supported`                   |
| `creds.get_setup_instructions("hubspot")` | Access `CREDENTIAL_SPECS["hubspot"]` directly                        |

**Why migrate?**

- **CredentialStore** supports encrypted storage, multi-key credentials, template resolution, and automatic token refresh
- **CredentialManager** only reads from environment variables and .env files (no encryption, no refresh)
- **CredentialStoreAdapter** exists for backward compatibility during migration

```python
# Old way (deprecated)
from aden_tools.credentials import CredentialManager
creds = CredentialManager()
token = creds.get("hubspot")

# New way (recommended)
from core.framework.credentials import CredentialStore
store = CredentialStore.with_encrypted_storage()
token = store.get("hubspot")

# With Aden sync (recommended for OAuth integrations)
store = CredentialStore.with_aden_sync()
token = store.get_key("hubspot", "access_token")
```

## Example Session

```
User: /setup-credentials for my hubspot-agent

Agent: Let me check what credentials your hubspot-agent needs.

[Runs validation, finds ANTHROPIC_API_KEY and HUBSPOT_ACCESS_TOKEN missing]

Agent: Your hubspot-agent requires 2 credentials:

  1. ANTHROPIC_API_KEY - Anthropic API key for LLM calls
  2. HUBSPOT_ACCESS_TOKEN - HubSpot access token

Let's set these up one at a time.

--- Setting up ANTHROPIC_API_KEY ---

This credential only supports direct API key entry.

[Shows instructions for getting Anthropic API key]
[AskUserQuestion: "Please provide your Anthropic API key:"]
[User provides key]
[Stores in credential store, exports to env]

--- Setting up HUBSPOT_ACCESS_TOKEN ---

[AskUserQuestion with 3 options]

Choose how to configure HUBSPOT_ACCESS_TOKEN:
  1) Aden Authorization Server (Recommended)
  2) Direct API Key
  3) Custom Credential Store (Advanced)

User: 1 (Aden)

Agent: Great! Let me check if you have an Aden API key configured...

[Checks for ADEN_API_KEY, not found]
[Opens browser to integration.adenhq.com/setup]

Agent: I've opened Aden's setup page. Please:
  1. Sign in or create an account
  2. Connect your HubSpot account (OAuth happens on Aden's site)
  3. Copy the API key shown after setup

[AskUserQuestion: "Please provide your Aden API key:"]
[User provides key]

Agent: Would you like me to save this to your shell config (~/.zshrc) for future sessions?

[User approves]
[Saves to ~/.zshrc and ~/.hive/configuration.json]

Agent: Let me sync your credentials from Aden...

[Syncs credentials from Aden server - OAuth already done on Aden's side]
[Runs health check]

Agent: HubSpot credentials validated successfully!

All credentials are now configured:
  - ANTHROPIC_API_KEY: Stored in encrypted credential store
  - HUBSPOT_ACCESS_TOKEN: Synced from Aden (OAuth completed on Aden)
  - Validation passed - your agent is ready to run!
```
