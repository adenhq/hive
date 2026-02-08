# PR Description: Zendesk Tickets & Search Integration

## 🎯 Objective
This PR implements the Zendesk integration for Hive agents, enabling automated support workflows. It allows agents to search for tickets, retrieve full details, and update ticket properties (status, assignee, comments) in real-time.

## ✨ Key Changes

### 🔐 1. Authentication & Credentials
- **`support.py`**: Created a new credential category for support-related services.
- **Spec Details**: Added `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, and `ZENDESK_API_TOKEN` specifications.
- **Auth Scheme**: Implemented the `{email}/token:{token}` Basic Auth pattern required by the Zendesk API.

### ⚙️ 2. Core Zendesk Toolkit
- **`zendesk_health_check`**: Proactive validation of API connectivity and authentication status.
- **`zendesk_ticket_search`**: Powerful search utilizing Zendesk's native query syntax (supports status and priority filtering).
- **`zendesk_ticket_get`**: Direct ticket retrieval by ID.
- **`zendesk_ticket_update`**: Comprehensive update tool supporting status transitions, assignments, and public/private commenting.

### 🏗️ 3. Industrial Structure
- **Package Refactoring**: Followed the Hive standard by encapsulating the integration into `tools/src/aden_tools/tools/zendesk_tool/` with its own `README.md` and `__init__.py`.
- **Docs**: Added `docs/ZENDESK_INTEGRATION.md` with setup instructions and reference agent configurations.

### 🧪 4. Testing & Reliability
- **Comprehensive Unit Tests**: Implemented 10 tests in `tools/tests/tools/test_zendesk_tool.py` covering success and failure paths.
- **Edge Case Coverage**:
    - **API Errors**: Verified 401 Unauthorized, 404 Not Found, and 429 Rate Limiting behavior.
    - **Validation**: Rejection of requests with missing credentials.
    - **Empty States**: Correct handling of zero search results.
    - **Payload Logic**: Verification of private vs public comments and minimal vs full ticket updates.
- **Integration Check**: Verified successful tool registration within the global Hive toolkit via `tools/tests/tools/test_zendesk_integration.py`.

---

## 🏗️ Future Roadmap
- Support for attachments in ticket comments.
- Integration with Zendesk Macros.
- Automated ticket categorization using LLM classification nodes.
