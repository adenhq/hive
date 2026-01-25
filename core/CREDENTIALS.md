# Enterprise Credential Manager

Aden Framework includes a robust, pluggable credential management system designed for enterprise environments. It supports multiple secret sources, priority chaining, rotation, and audit logging.

## Key Features

- **Multi-Source**: Load secrets from Environment Variables, Config Files, HashiCorp Vault, and AWS Secrets Manager.
- **Priority Chain**: Define a hierarchy of sources (e.g., *Vault* > *Native Env Vars* > *Config File*).
- **Auto-Rotation**: Automatically refresh secrets from remote providers (Vault/AWS) based on TTL.
- **Audit Logging**: Logs access to credentials (without logging details) for compliance.
- **Lazy Loading**: Connections to remote providers are only established when a specific credential is requested.

## Usage

### Basic Logic (Environment Variables)

By default, the manager looks at `os.environ`.

```python
from framework.credentials import CredentialManager

creds = CredentialManager() # Defaults to [EnvVarSource]
api_key = creds.get_or_error("OPENAI_API_KEY")
```

### Local Development (Config File)

Load credentials from a local YAML file (git-ignored, hopefully!).

```python
from framework.credentials import CredentialManager

creds = CredentialManager.from_environment("local")
# Looks for credentials.local.yaml
```

**credentials.local.yaml**:
```yaml
OPENAI_API_KEY: sk-...
DATABASE_URL: postgres://...
```

### Advanced: Enterprise Stack (Vault + AWS)

```python
from framework.credentials import (
    CredentialManager, 
    EnvVarSource, 
    ConfigFileSource, 
    VaultSource, 
    AWSSecretsSource
)

creds = CredentialManager(sources=[
    # 1. Check HashiCorp Vault first (auto-refresh every 5 mins)
    VaultSource(
        url="https://vault.corp.com", 
        token=os.environ["VAULT_TOKEN"],
        ttl_seconds=300
    ),
    
    # 2. Check AWS Secrets Manager
    AWSSecretsSource(
        secret_id="prod/myapp/secrets", 
        region_name="us-east-1"
    ),

    # 3. Fallback to Environment Variables
    EnvVarSource(),
])

# This call triggers the lookup chain
db_pass = creds.get("DB_PASSWORD")
```

## Credential Resolution Logic

When you call `get(key)`:
1. Manager iterates through the list of `sources`.
2. Accesses the credential from the source.
3. If found:
   - Logs an `[AUDIT]` entry (debug level).
   - Returns the value immediately.
4. If not found in any source, returns `None` (or raises error if `get_or_error` was used).

## Dependencies

The core system requires `pyyaml`.
Enterprise sources require optional extras:

```bash
pip install framework[secrets]
# Installs hvac, boto3
```
