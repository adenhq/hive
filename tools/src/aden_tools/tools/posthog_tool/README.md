# PostHog Tool

Analytics-driven agent automation. Allows agents to query product data, analyze funnels, and react to user behavior patterns.

## Features
- **HogQL Queries**: Execute powerful SQL-like queries directly against your PostHog data.
- **Event Retrieval**: List recent events to monitor specific user actions.
- **Funnel Analysis**: Retrieve metrics for existing funnel insights.
- **Cohort Management**: Access user cohorts for targeted automation.
- **Self-Hostable**: Supports both app.posthog.com and self-hosted instances.

## Configuration

Set the following environment variables or configure via the Hive Credential Store:

- `POSTHOG_API_KEY`: Your Personal API Key (requires `query:read` and `project:read` scopes).
- `POSTHOG_PROJECT_ID`: The ID of your PostHog project.
- `POSTHOG_URL` (Optional): Custom base URL (e.g., `https://posthog.example.com`). Defaults to `https://app.posthog.com`.

### Getting a Personal API Key
1. Log in to PostHog.
2. Go to **Settings** > **Personal API Keys**.
3. Create a new key with appropriate permissions.

## Available Tools

### `posthog_query`
Execute a HogQL query for advanced analytics.
- `hogql` (str): The HogQL query string.
- **Example**: `SELECT event, count() FROM events GROUP BY event`

### `posthog_list_events`
List recent raw events.
- `limit` (int, default=100): Max events to return.
- `event_name` (str, optional): Filter by event type (e.g., `$pageview`).

### `posthog_get_funnel_metrics`
Retrieve conversion metrics for a saved funnel insight.
- `insight_id` (str): The ID of the saved insight.

### `posthog_list_cohorts`
List all user cohorts defined in the project.

## Example Workflow

### Funnel Drop-off Alert
An agent monitors a conversion funnel and alerts Slack if the drop-off exceeds a threshold.
```python
funnel = posthog_get_funnel_metrics(insight_id="12345")
conversion_rate = funnel['results'][0]['count'] / funnel['results'][1]['count']
if conversion_rate < 0.2:
    slack_send_message(channel="#growth", message="Conversion drop-off detected!")
```

### Behavioral Trigger
Trigger a follow-up for users who signed up but didn't complete onboarding.
```python
query = "SELECT distinct_id FROM events WHERE event = 'signup' AND distinct_id NOT IN (SELECT distinct_id FROM events WHERE event = 'onboarding_complete')"
users = posthog_query(hogql=query)
# ... trigger outreach for users
```
