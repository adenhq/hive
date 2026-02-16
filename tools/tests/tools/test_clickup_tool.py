"""Tests for ClickUp tool with FastMCP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastmcp import FastMCP

from aden_tools.tools.clickup_tool import register_tools


class TestToolRegistration:
    """Tests for ClickUp tool registration."""

    def test_all_tools_registered(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-registration")

        register_tools(mcp)

        expected_tools = [
            "clickup_list_workspaces",
            "clickup_list_spaces",
            "clickup_list_lists",
            "clickup_list_tasks",
            "clickup_get_task",
            "clickup_create_task",
            "clickup_update_task",
            "clickup_add_task_comment",
        ]

        for tool_name in expected_tools:
            assert tool_name in mcp._tool_manager._tools


class TestCredentialHandling:
    """Tests for ClickUp credential handling."""

    def test_missing_credentials_returns_error_and_help(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
        mcp = FastMCP("test-clickup-no-creds")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_list_workspaces"].fn
        result = fn()

        assert "error" in result
        assert "not configured" in result["error"]
        assert "help" in result

    def test_non_string_credential_returns_error(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
        mcp = FastMCP("test-clickup-bad-creds")

        creds = MagicMock()
        creds.get.return_value = {"token": "bad-type"}
        register_tools(mcp, credentials=creds)

        fn = mcp._tool_manager._tools["clickup_list_workspaces"].fn
        result = fn()

        assert "error" in result
        assert "not configured" in result["error"]


class TestWorkspaceAndStructureReads:
    """Tests for workspace, space, and list reads."""

    def test_list_workspaces_success(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-list-workspaces")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_list_workspaces"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.get") as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "teams": [{"id": "team_1", "name": "Engineering"}],
            }
            mock_get.return_value = response

            result = fn()

            assert "teams" in result
            assert result["teams"][0]["id"] == "team_1"
            assert mock_get.call_args.kwargs["headers"]["Authorization"] == "test-token"

    def test_list_spaces_with_archived_filter(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-list-spaces")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_list_spaces"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.get") as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"spaces": []}
            mock_get.return_value = response

            fn(workspace_id="team_1", archived=True)

            params = mock_get.call_args.kwargs["params"]
            assert params["archived"] == "true"

    def test_list_tasks_with_filters(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-list-tasks")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_list_tasks"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.get") as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"tasks": []}
            mock_get.return_value = response

            fn(
                list_id="list_1",
                include_closed=True,
                archived=True,
                page=2,
                statuses=["in progress", "review"],
                assignees=["u1", "u2"],
            )

            params = mock_get.call_args.kwargs["params"]
            assert params["include_closed"] == "true"
            assert params["archived"] == "true"
            assert params["page"] == 2
            assert params["statuses[]"] == ["in progress", "review"]
            assert params["assignees[]"] == ["u1", "u2"]


class TestTaskOperations:
    """Tests for task create/read/update/comment operations."""

    def test_get_task_not_found(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-get-task-404")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_get_task"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.get") as mock_get:
            response = MagicMock()
            response.status_code = 404
            response.text = "Task not found"
            mock_get.return_value = response

            result = fn(task_id="missing")

            assert "error" in result
            assert "not found" in result["error"].lower()

    def test_create_task_validates_name(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-create-task-validation")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_create_task"].fn

        result = fn(list_id="list_1", name="   ")

        assert result == {"error": "Task name is required"}

    def test_create_task_success_payload(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-create-task")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_create_task"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.post") as mock_post:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": "task_1", "name": "Ship integration"}
            mock_post.return_value = response

            result = fn(
                list_id="list_1",
                name="Ship integration",
                description="Build ClickUp MCP integration",
                status="in progress",
                assignees=["u1"],
                due_date=1735689600000,
                priority=2,
            )

            assert result["id"] == "task_1"
            call = mock_post.call_args
            assert call.kwargs["json"]["name"] == "Ship integration"
            assert call.kwargs["json"]["status"] == "in progress"
            assert call.kwargs["json"]["assignees"] == ["u1"]

    def test_update_task_requires_at_least_one_field(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-update-task-validation")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_update_task"].fn

        result = fn(task_id="task_1")

        assert result == {"error": "At least one field must be provided for update"}

    def test_update_task_success(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-update-task")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_update_task"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.put") as mock_put:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": "task_1", "status": "done"}
            mock_put.return_value = response

            result = fn(task_id="task_1", status="done")

            assert result["status"] == "done"
            assert mock_put.call_args.kwargs["json"] == {"status": "done"}

    def test_add_comment_validates_text(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-comment-validation")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_add_task_comment"].fn

        result = fn(task_id="task_1", comment_text="  ")

        assert result == {"error": "Comment text is required"}

    def test_add_comment_success(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-comment")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_add_task_comment"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.post") as mock_post:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": "comment_1"}
            mock_post.return_value = response

            result = fn(task_id="task_1", comment_text="Looks good", notify_all=True)

            assert result["id"] == "comment_1"
            payload = mock_post.call_args.kwargs["json"]
            assert payload["comment_text"] == "Looks good"
            assert payload["notify_all"] is True


class TestErrorHandling:
    """Tests for network and API error handling."""

    def test_rate_limit_error(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_TOKEN", "test-token")
        mcp = FastMCP("test-clickup-rate-limit")
        register_tools(mcp)

        fn = mcp._tool_manager._tools["clickup_list_workspaces"].fn

        with patch("aden_tools.tools.clickup_tool.clickup_tool.httpx.get") as mock_get:
            response = MagicMock()
            response.status_code = 429
            response.text = "Too Many Requests"
            mock_get.return_value = response

            result = fn()

            assert "error" in result
            assert "rate limit" in result["error"].lower()
