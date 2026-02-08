# Work Plan: Zendesk Tickets & Search Integration ([Issue #2912](https://github.com/Samir-atra/hive_fork/issues/2912))

## Overview
Enable Hive agents to interact with Zendesk to search, retrieve, and update support tickets. This integration follows the "Apple UX" philosophy of Hive by providing a streamlined toolset for support automation workflows (e.g., Slack summaries, PagerDuty incident linking).

---

## 🛠 Phase 1: Authentication & Specification
**Goal**: Securely handle Zendesk API Token authentication.

1.  **Environment Configuration**:
    *   Add `ZENDESK_SUBDOMAIN` (e.g., `adenhq`) to `.env`.
    *   Add `ZENDESK_EMAIL` (the user email) to `.env`.
    *   Add `ZENDESK_API_TOKEN` to `.env`.
2.  **Credential Management**:
    *   Add `ZENDESK_CREDENTIALS` to `tools/src/aden_tools/credentials/crm.py` (or a new `support.py`).
    *   Spec required keys: `subdomain`, `email`, `api_token`.
3.  **Discovery/Research**:
    *   Verify Zendesk API documentation for Ticket Search and Update endpoints.
    *   Endpoint pattern: `https://{subdomain}.zendesk.com/api/v2/...`

## ⚙️ Phase 2: Core Tooling Implementation (MVP)
**Goal**: Implement the four primary tools requested in the scope.

1.  **`zendesk_ticket_search`**:
    *   Search tickets by advanced queries (status, priority, requester).
    *   Parameters: `query`, `status`, `priority`.
2.  **`zendesk_ticket_get`**:
    *   Retrieve full details for a specific ticket.
    *   Parameters: `ticket_id`.
3.  **`zendesk_ticket_update`**:
    *   Modify ticket status, assignee, or add internal/public comments.
    *   Parameters: `ticket_id`, `status`, `assignee_id`, `comment`, `is_public`.
4.  **`zendesk_health_check`**:
    *   Lightweight validation tool to verify connectivity to the Zendesk instance.

## 🚀 Phase 3: Agent Integration & Documentation
**Goal**: Provide reference implementations and guides for support teams.

1.  **Documentation**:
    *   Create `docs/ZENDESK_INTEGRATION.md` covering API token generation and scope requirements.
    *   Include a "Search Query Guide" for agent prompt engineering.
2.  **Reference Workflow Agent**:
    *   Create `exports/zendesk_summary_agent`: A sample agent that lists high-priority tickets and generates a natural language summary.

## 🧪 Phase 4: Testing & Verification
**Goal**: Ensure reliability and security within the Hive framework.

1.  **Unit Tests**:
    *   Mock API responses for all endpoints.
    *   Verify correct header formation (`Authorization: Basic base64({email}/token:{api_token})`).
2.  **Credential Validation**:
    *   Verify the `CredentialManager` correctly enforces Zendesk requirements.

---

## 📅 Timeline Estimate
*   **Infrastructure & Authentication**: 0.5 days
*   **Ticket Tools (Search/Get/Update)**: 1.5 days
*   **Documentation & Reference Agent**: 0.5 days
*   **Testing**: 0.5 days

## 📝 Notes
*   **Auth Strategy**: Using "zopim" style `/token` suffix for the email is standard for Zendesk API tokens.
*   **Safety**: Update operations will be clearly marked as destructive in tool descriptions.
