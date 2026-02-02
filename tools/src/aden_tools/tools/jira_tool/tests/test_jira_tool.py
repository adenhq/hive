"""
Tests for Jira Project Management tool.

Covers:
- _JiraClient methods (search, get, create, update, comment, transition, projects)
- Error handling (401, 403, 404, 429, 500, timeout)
- Credential retrieval (CredentialStoreAdapter vs env var)
- All 9 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.jira_tool.jira_tool import _JiraClient, register_tools

# --- _JiraClient tests ---


class TestJiraClient:
    def setup_method(self):
        self.client = _JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

    def test_initialization(self):
        assert self.client.base_url == "https://test.atlassian.net"
        assert self.client._email == "test@example.com"
        assert self.client._token == "test-token"

    def test_initialization_strips_trailing_slash(self):
        client = _JiraClient(
            base_url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="test-token",
        )
        assert client.base_url == "https://test.atlassian.net"

    def test_headers(self):
        headers = self.client._headers
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"issues": [], "total": 0}
        assert self.client._handle_response(response) == {"issues": [], "total": 0}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid Jira credentials"),
            (403, "Insufficient permissions"),
            (404, "Resource not found"),
            (429, "rate limit"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring in result["error"]

    def test_handle_response_generic_error_with_error_messages(self):
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"errorMessages": ["Field 'project' is required"]}
        result = self.client._handle_response(response)
        assert "error" in result
        assert "Field 'project' is required" in result["error"]

    def test_handle_response_generic_error_with_errors_dict(self):
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"errors": {"summary": "Required field"}}
        result = self.client._handle_response(response)
        assert "error" in result
        assert "summary" in result["error"]

    def test_handle_response_generic_error_fallback(self):
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = Exception()
        response.text = "Internal Server Error"
        result = self.client._handle_response(response)
        assert "error" in result
        assert "500" in result["error"]

    def test_handle_response_no_json(self):
        response = MagicMock()
        response.status_code = 204
        response.json.side_effect = Exception()
        result = self.client._handle_response(response)
        assert result["success"] is True
        assert result["status_code"] == 204

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_search_issues(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [{"id": "10001", "key": "PROJ-123"}],
            "total": 1,
        }
        mock_post.return_value = mock_response

        result = self.client.search_issues(
            jql="project = PROJ", fields=["summary"], max_results=10
        )

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args.kwargs["auth"] == ("test@example.com", "test-token")
        assert call_args.kwargs["json"]["jql"] == "project = PROJ"
        assert call_args.kwargs["json"]["fields"] == ["summary"]
        assert call_args.kwargs["json"]["maxResults"] == 10
        assert result["total"] == 1

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_search_issues_default_jql(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": [], "total": 0}
        mock_post.return_value = mock_response

        self.client.search_issues()

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["jql"] == "order by created DESC"
        assert "summary" in call_json["fields"]

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_search_issues_max_results_capped(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": [], "total": 0}
        mock_post.return_value = mock_response

        self.client.search_issues(max_results=200)

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["maxResults"] == 100

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_get_issue(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "10001",
            "key": "PROJ-123",
            "fields": {"summary": "Test issue"},
        }
        mock_get.return_value = mock_response

        result = self.client.get_issue("PROJ-123", fields=["summary", "status"])

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "PROJ-123" in call_args.args[0]
        assert call_args.kwargs["params"]["fields"] == "summary,status"
        assert result["key"] == "PROJ-123"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_get_issue_no_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "10001", "key": "PROJ-123"}
        mock_get.return_value = mock_response

        self.client.get_issue("PROJ-123")

        assert mock_get.call_args.kwargs["params"] == {}

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_create_issue(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "10002", "key": "PROJ-124"}
        mock_post.return_value = mock_response

        result = self.client.create_issue(
            project_key="PROJ",
            summary="New issue",
            issue_type="Bug",
            description="Test description",
        )

        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]["fields"]
        assert call_json["project"]["key"] == "PROJ"
        assert call_json["summary"] == "New issue"
        assert call_json["issuetype"]["name"] == "Bug"
        assert "description" in call_json
        assert result["key"] == "PROJ-124"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_create_issue_no_description(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "10002", "key": "PROJ-124"}
        mock_post.return_value = mock_response

        self.client.create_issue(project_key="PROJ", summary="New issue")

        call_json = mock_post.call_args.kwargs["json"]["fields"]
        assert "description" not in call_json

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_create_issue_with_additional_fields(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "10002", "key": "PROJ-124"}
        mock_post.return_value = mock_response

        self.client.create_issue(
            project_key="PROJ",
            summary="New issue",
            additional_fields={"priority": {"name": "High"}},
        )

        call_json = mock_post.call_args.kwargs["json"]["fields"]
        assert call_json["priority"]["name"] == "High"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.put")
    def test_update_issue(self, mock_put):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.side_effect = Exception()
        mock_put.return_value = mock_response

        result = self.client.update_issue("PROJ-123", {"summary": "Updated"})

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert "PROJ-123" in call_args.args[0]
        assert call_args.kwargs["json"]["fields"]["summary"] == "Updated"
        assert result["success"] is True

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_add_comment(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "10050",
            "body": {"type": "doc"},
            "author": {"displayName": "Test User"},
        }
        mock_post.return_value = mock_response

        result = self.client.add_comment("PROJ-123", "Test comment")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "PROJ-123/comment" in call_args.args[0]
        assert call_args.kwargs["json"]["body"]["type"] == "doc"
        assert result["id"] == "10050"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_transition_issue(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.side_effect = Exception()
        mock_post.return_value = mock_response

        result = self.client.transition_issue("PROJ-123", "31")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "PROJ-123/transitions" in call_args.args[0]
        assert call_args.kwargs["json"]["transition"]["id"] == "31"
        assert result["success"] is True

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_get_transitions(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transitions": [
                {"id": "11", "name": "To Do"},
                {"id": "21", "name": "In Progress"},
            ]
        }
        mock_get.return_value = mock_response

        result = self.client.get_transitions("PROJ-123")

        mock_get.assert_called_once()
        assert "PROJ-123/transitions" in mock_get.call_args.args[0]
        assert len(result["transitions"]) == 2

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_list_projects(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "10000", "key": "PROJ", "name": "My Project"}
        ]
        mock_get.return_value = mock_response

        result = self.client.list_projects()

        mock_get.assert_called_once()
        assert "/rest/api/3/project" in mock_get.call_args.args[0]
        assert "projects" in result
        assert len(result["projects"]) == 1
        assert result["projects"][0]["key"] == "PROJ"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_list_projects_error_passthrough(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.client.list_projects()

        assert "error" in result
        assert "Invalid Jira credentials" in result["error"]


# --- Credential management tests ---


class TestCredentialManagement:
    def test_get_credentials_from_credential_store(self):
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = {
            "base_url": "https://test.atlassian.net",
            "email": "test@example.com",
            "api_token": "store-token",
        }

        register_tools(mcp, credentials=cred)

        list_projects_fn = next(f for f in fns if f.__name__ == "jira_list_projects")

        with patch("aden_tools.tools.jira_tool.jira_tool.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=[{"key": "PROJ"}])
            )
            result = list_projects_fn()

            assert "projects" in result
            # Verify credentials were used
            call_auth = mock_get.call_args.kwargs["auth"]
            assert call_auth == ("test@example.com", "store-token")

    @patch.dict(
        "os.environ",
        {
            "JIRA_BASE_URL": "https://env.atlassian.net",
            "JIRA_EMAIL": "env@example.com",
            "JIRA_API_TOKEN": "env-token",
        },
    )
    def test_get_credentials_from_env(self):
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn

        register_tools(mcp, None)

        list_projects_fn = next(f for f in fns if f.__name__ == "jira_list_projects")

        with patch("aden_tools.tools.jira_tool.jira_tool.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=[{"key": "PROJ"}])
            )
            result = list_projects_fn()

            assert "projects" in result
            # Verify env credentials were used
            call_auth = mock_get.call_args.kwargs["auth"]
            assert call_auth == ("env@example.com", "env-token")

    @patch.dict("os.environ", {}, clear=True)
    def test_get_credentials_missing(self):
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = None

        register_tools(mcp, credentials=cred)

        list_projects_fn = next(f for f in fns if f.__name__ == "jira_list_projects")

        result = list_projects_fn()

        assert "error" in result
        assert "not configured" in result["error"]

    @patch.dict("os.environ", {}, clear=True)
    def test_credential_store_type_error(self):
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "invalid-string-not-dict"

        register_tools(mcp, credentials=cred)

        list_projects_fn = next(f for f in fns if f.__name__ == "jira_list_projects")

        with pytest.raises(TypeError, match="Expected dict"):
            list_projects_fn()


# --- MCP tool function tests ---


class TestMCPTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = {
            "base_url": "https://test.atlassian.net",
            "email": "test@example.com",
            "api_token": "test-token",
        }
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_search_issues_tool(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"issues": [], "total": 0})
        )
        result = self._fn("jira_search_issues")(jql="project = PROJ")
        assert result["total"] == 0

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_search_issues_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")
        result = self._fn("jira_search_issues")()
        assert "error" in result
        assert "timed out" in result["error"]

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_search_issues_network_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("connection error")
        result = self._fn("jira_search_issues")()
        assert "error" in result
        assert "Network error" in result["error"]

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_get_issue_tool(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"key": "PROJ-123"})
        )
        result = self._fn("jira_get_issue")(issue_key="PROJ-123")
        assert result["key"] == "PROJ-123"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_get_issue_timeout(self, mock_get):
        mock_get.side_effect = httpx.TimeoutException("timeout")
        result = self._fn("jira_get_issue")(issue_key="PROJ-123")
        assert "error" in result
        assert "timed out" in result["error"]

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_create_issue_tool(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201, json=MagicMock(return_value={"key": "PROJ-124"})
        )
        result = self._fn("jira_create_issue")(project_key="PROJ", summary="New issue")
        assert result["key"] == "PROJ-124"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_create_issue_network_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("network error")
        result = self._fn("jira_create_issue")(project_key="PROJ", summary="Test")
        assert "error" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.put")
    def test_jira_update_issue_tool(self, mock_put):
        mock_put.return_value = MagicMock(status_code=204, json=MagicMock(side_effect=Exception()))
        result = self._fn("jira_update_issue")(issue_key="PROJ-123", fields={"summary": "Updated"})
        assert result["success"] is True

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.put")
    def test_jira_update_issue_timeout(self, mock_put):
        mock_put.side_effect = httpx.TimeoutException("timeout")
        result = self._fn("jira_update_issue")(issue_key="PROJ-123", fields={})
        assert "error" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_add_comment_tool(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201, json=MagicMock(return_value={"id": "10050"})
        )
        result = self._fn("jira_add_comment")(issue_key="PROJ-123", comment="Test")
        assert result["id"] == "10050"

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_add_comment_network_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("error")
        result = self._fn("jira_add_comment")(issue_key="PROJ-123", comment="Test")
        assert "error" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_transition_issue_tool(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204, json=MagicMock(side_effect=Exception()))
        result = self._fn("jira_transition_issue")(issue_key="PROJ-123", transition_id="31")
        assert result["success"] is True

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.post")
    def test_jira_transition_issue_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")
        result = self._fn("jira_transition_issue")(issue_key="PROJ-123", transition_id="31")
        assert "error" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_get_transitions_tool(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"transitions": []})
        )
        result = self._fn("jira_get_transitions")(issue_key="PROJ-123")
        assert "transitions" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_get_transitions_network_error(self, mock_get):
        mock_get.side_effect = httpx.RequestError("error")
        result = self._fn("jira_get_transitions")(issue_key="PROJ-123")
        assert "error" in result

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_list_projects_tool(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value=[{"key": "PROJ"}])
        )
        result = self._fn("jira_list_projects")()
        assert "projects" in result
        assert len(result["projects"]) == 1

    @patch("aden_tools.tools.jira_tool.jira_tool.httpx.get")
    def test_jira_list_projects_timeout(self, mock_get):
        mock_get.side_effect = httpx.TimeoutException("timeout")
        result = self._fn("jira_list_projects")()
        assert "error" in result
        assert "timed out" in result["error"]
