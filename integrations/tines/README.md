# Tines Security Automation Integration

## Supported Operations
- Trigger security workflows (stories)
- Monitor story execution status
- List available automation stories
- Pass incident data to Tines

## Configuration
```bash
export TINES_API_TOKEN="your_api_token"
export TINES_TENANT="your_tenant"


## Usage
from integrations.tines import TinesConnector, TinesCredentials

# Initialize
credentials = TinesCredentials.from_env()
connector = TinesConnector(credentials)

# Trigger security workflow
result = connector.trigger_story(
    story_id="12345",
    payload={
        "alert_type": "suspicious_login",
        "user": "admin@company.com",
        "ip": "192.168.1.1"
    }
)

# Check status
status = connector.get_story_status("12345")


##Security Use Cases
- Suspicious login detection
- Automated incident response
- Threat enrichment
- Compliance auditing


## Links
Tines Documentation [ https://www.tines.com/docs/]
Tines API Reference [ https://www.tines.com/docs/api/]