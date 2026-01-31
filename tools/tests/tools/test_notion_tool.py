"""
Tests for Notion tool.

Covers:
- _NotionClient methods (search, get_page, create_page, update_page, query_database, append_blocks)
- Error handling (401, 403, 404, 429, 500, timeout)
- Credential retrieval (CredentialStoreAdapter vs env var)
- All 6 MCP tool functions
- Input validation
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.notion_tool.notion_tool import (
    NOTION_API_BASE,
    NOTION_API_VERSION,
    _NotionClient,
    register_tools,
)

# --- _NotionClient tests ---


class TestNotionClient:
    def setup_method(self):
        self.client = _NotionClient("secret_test-token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Bearer secret_test-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Notion-Version"] == NOTION_API_VERSION

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"results": []}
        assert self.client._handle_response(response) == {"results": []}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid Notion API key"),
            (403, "Access denied"),
            (404, "not found"),
            (429, "rate limit"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring in result["error"]

    def test_handle_response_generic_error(self):
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = {"message": "Internal Server Error"}
        result = self.client._handle_response(response)
        assert "error" in result
        assert "500" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_search(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "page-1", "object": "page"}],
            "has_more": False,
        }
        mock_post.return_value = mock_response

        result = self.client.search(query="test", filter_type="page", page_size=5)

        mock_post.assert_called_once_with(
            f"{NOTION_API_BASE}/search",
            headers=self.client._headers,
            json={
                "page_size": 5,
                "query": "test",
                "filter": {"property": "object", "value": "page"},
            },
            timeout=30.0,
        )
        assert len(result["results"]) == 1

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_search_no_query(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "has_more": False}
        mock_post.return_value = mock_response

        self.client.search(page_size=10)

        call_json = mock_post.call_args.kwargs["json"]
        assert "query" not in call_json
        assert "filter" not in call_json
        assert call_json["page_size"] == 10

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_search_page_size_capped(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "has_more": False}
        mock_post.return_value = mock_response

        self.client.search(page_size=200)

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["page_size"] == 100

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_get_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "page-123",
            "object": "page",
            "properties": {"title": {"title": [{"text": {"content": "Test Page"}}]}},
        }
        mock_get.return_value = mock_response

        result = self.client.get_page("page-123")

        mock_get.assert_called_once_with(
            f"{NOTION_API_BASE}/pages/page-123",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert result["id"] == "page-123"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_get_page_content(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"type": "paragraph", "paragraph": {"rich_text": []}}],
            "has_more": False,
        }
        mock_get.return_value = mock_response

        result = self.client.get_page_content("page-123")

        mock_get.assert_called_once_with(
            f"{NOTION_API_BASE}/blocks/page-123/children",
            headers=self.client._headers,
            params={"page_size": 100},
            timeout=30.0,
        )
        assert len(result["results"]) == 1

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_create_page_under_page(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "new-page", "object": "page"}
        mock_post.return_value = mock_response

        result = self.client.create_page(
            parent_id="parent-page",
            parent_type="page",
            title="New Page",
        )

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["parent"] == {"page_id": "parent-page"}
        assert "title" in str(call_json["properties"])
        assert result["id"] == "new-page"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_create_page_in_database(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "db-page", "object": "page"}
        mock_post.return_value = mock_response

        result = self.client.create_page(
            parent_id="database-id",
            parent_type="database",
            title="DB Entry",
            properties={"Name": {"title": [{"text": {"content": "DB Entry"}}]}},
        )

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["parent"] == {"database_id": "database-id"}
        assert result["id"] == "db-page"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_create_page_with_content(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "page-with-content"}
        mock_post.return_value = mock_response

        content = [
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}
        ]
        self.client.create_page(
            parent_id="parent",
            parent_type="page",
            title="Test",
            content=content,
        )

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["children"] == content

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_update_page(self, mock_patch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "page-123", "archived": False}
        mock_patch.return_value = mock_response

        result = self.client.update_page(
            page_id="page-123",
            properties={"title": {"title": [{"text": {"content": "Updated"}}]}},
        )

        mock_patch.assert_called_once()
        assert result["id"] == "page-123"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_update_page_archive(self, mock_patch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "page-123", "archived": True}
        mock_patch.return_value = mock_response

        result = self.client.update_page(page_id="page-123", archived=True)

        call_json = mock_patch.call_args.kwargs["json"]
        assert call_json["archived"] is True
        assert result["archived"] is True

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_query_database(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "row-1"}, {"id": "row-2"}],
            "has_more": False,
        }
        mock_post.return_value = mock_response

        result = self.client.query_database(
            database_id="db-123",
            filter_conditions={"property": "Status", "select": {"equals": "Done"}},
            sorts=[{"property": "Created", "direction": "descending"}],
            page_size=20,
        )

        mock_post.assert_called_once_with(
            f"{NOTION_API_BASE}/databases/db-123/query",
            headers=self.client._headers,
            json={
                "page_size": 20,
                "filter": {"property": "Status", "select": {"equals": "Done"}},
                "sorts": [{"property": "Created", "direction": "descending"}],
            },
            timeout=30.0,
        )
        assert len(result["results"]) == 2

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_append_blocks(self, mock_patch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "block-1", "type": "paragraph"}],
        }
        mock_patch.return_value = mock_response

        children = [
            {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}
        ]
        result = self.client.append_blocks(block_id="page-123", children=children)

        mock_patch.assert_called_once_with(
            f"{NOTION_API_BASE}/blocks/page-123/children",
            headers=self.client._headers,
            json={"children": children},
            timeout=30.0,
        )
        assert len(result["results"]) == 1


# --- MCP tool registration and credential tests ---


class TestToolRegistration:
    def test_register_tools_registers_all_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 6

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)

        search_fn = next(fn for fn in registered_fns if fn.__name__ == "notion_search")
        result = search_fn()
        assert "error" in result
        assert "not configured" in result["error"]

    def test_credentials_from_credential_manager(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.return_value = "secret_test-token"

        register_tools(mcp, credentials=cred_manager)

        search_fn = next(fn for fn in registered_fns if fn.__name__ == "notion_search")

        with patch("aden_tools.tools.notion_tool.notion_tool.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [], "has_more": False}
            mock_post.return_value = mock_response

            result = search_fn(query="test")

        cred_manager.get.assert_called_with("notion")
        assert "results" in result

    def test_credentials_from_env_var(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        register_tools(mcp, credentials=None)

        search_fn = next(fn for fn in registered_fns if fn.__name__ == "notion_search")

        with (
            patch.dict("os.environ", {"NOTION_API_KEY": "secret_env-token"}),
            patch("aden_tools.tools.notion_tool.notion_tool.httpx.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [], "has_more": False}
            mock_post.return_value = mock_response

            result = search_fn(query="test")

        assert "results" in result
        call_headers = mock_post.call_args.kwargs["headers"]
        assert call_headers["Authorization"] == "Bearer secret_env-token"


# --- Individual tool function tests ---


class TestNotionTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "secret_tok"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_notion_search(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"results": [{"id": "1"}], "has_more": False}),
        )
        result = self._fn("notion_search")(query="test", filter_type="page")
        assert len(result["results"]) == 1

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_notion_get_page(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"id": "page-1"})
        )
        result = self._fn("notion_get_page")(page_id="page-1")
        assert result["id"] == "page-1"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_notion_get_page_with_content(self, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value={"id": "page-1"})),
            MagicMock(
                status_code=200,
                json=MagicMock(return_value={"results": [{"type": "paragraph"}]}),
            ),
        ]
        result = self._fn("notion_get_page")(page_id="page-1", include_content=True)
        assert result["id"] == "page-1"
        assert "content" in result

    def test_notion_get_page_missing_id(self):
        result = self._fn("notion_get_page")(page_id="")
        assert "error" in result
        assert "required" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_notion_create_page(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"id": "new-page"})
        )
        result = self._fn("notion_create_page")(
            parent_id="parent", title="New Page", parent_type="page"
        )
        assert result["id"] == "new-page"

    def test_notion_create_page_missing_parent_id(self):
        result = self._fn("notion_create_page")(parent_id="", title="Test")
        assert "error" in result
        assert "parent_id" in result["error"]

    def test_notion_create_page_missing_title(self):
        result = self._fn("notion_create_page")(parent_id="parent", title="")
        assert "error" in result
        assert "title" in result["error"]

    def test_notion_create_page_invalid_parent_type(self):
        result = self._fn("notion_create_page")(
            parent_id="parent", title="Test", parent_type="invalid"
        )
        assert "error" in result
        assert "parent_type" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_notion_update_page(self, mock_patch):
        mock_patch.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"id": "page-1"})
        )
        result = self._fn("notion_update_page")(
            page_id="page-1",
            properties={"title": {"title": [{"text": {"content": "Updated"}}]}},
        )
        assert result["id"] == "page-1"

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_notion_update_page_archive(self, mock_patch):
        mock_patch.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"id": "page-1", "archived": True})
        )
        result = self._fn("notion_update_page")(page_id="page-1", archived=True)
        assert result["archived"] is True

    def test_notion_update_page_missing_id(self):
        result = self._fn("notion_update_page")(page_id="")
        assert "error" in result
        assert "page_id" in result["error"]

    def test_notion_update_page_no_updates(self):
        result = self._fn("notion_update_page")(page_id="page-1")
        assert "error" in result
        assert "At least one" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_notion_query_database(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"results": [{"id": "row-1"}], "has_more": False}),
        )
        result = self._fn("notion_query_database")(database_id="db-1")
        assert len(result["results"]) == 1

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_notion_query_database_with_filter(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"results": [], "has_more": False}),
        )
        result = self._fn("notion_query_database")(
            database_id="db-1",
            filter_conditions={"property": "Status", "select": {"equals": "Done"}},
            sorts=[{"property": "Name", "direction": "ascending"}],
        )
        assert "results" in result

    def test_notion_query_database_missing_id(self):
        result = self._fn("notion_query_database")(database_id="")
        assert "error" in result
        assert "database_id" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.post")
    def test_notion_search_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timed out")
        result = self._fn("notion_search")(query="test")
        assert "error" in result
        assert "timed out" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.get")
    def test_notion_get_page_network_error(self, mock_get):
        mock_get.side_effect = httpx.RequestError("connection failed")
        result = self._fn("notion_get_page")(page_id="page-1")
        assert "error" in result
        assert "Network error" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_notion_append_blocks(self, mock_patch):
        mock_patch.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"results": [{"id": "block-1"}]}),
        )
        children = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        result = self._fn("notion_append_blocks")(block_id="page-1", children=children)
        assert "results" in result

    def test_notion_append_blocks_missing_block_id(self):
        result = self._fn("notion_append_blocks")(block_id="", children=[{"type": "paragraph"}])
        assert "error" in result
        assert "block_id" in result["error"]

    def test_notion_append_blocks_empty_children(self):
        result = self._fn("notion_append_blocks")(block_id="page-1", children=[])
        assert "error" in result
        assert "children" in result["error"]

    @patch("aden_tools.tools.notion_tool.notion_tool.httpx.patch")
    def test_notion_append_blocks_timeout(self, mock_patch):
        mock_patch.side_effect = httpx.TimeoutException("timed out")
        children = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        result = self._fn("notion_append_blocks")(block_id="page-1", children=children)
        assert "error" in result
        assert "timed out" in result["error"]


# --- Credential spec tests ---


class TestCredentialSpec:
    def test_notion_credential_spec_exists(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        assert "notion" in CREDENTIAL_SPECS

    def test_notion_spec_env_var(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["notion"]
        assert spec.env_var == "NOTION_API_KEY"

    def test_notion_spec_tools(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["notion"]
        assert "notion_search" in spec.tools
        assert "notion_get_page" in spec.tools
        assert "notion_create_page" in spec.tools
        assert "notion_update_page" in spec.tools
        assert "notion_query_database" in spec.tools
        assert "notion_append_blocks" in spec.tools
        assert len(spec.tools) == 6

    def test_notion_spec_help_url(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["notion"]
        assert "developers.notion.com" in spec.help_url
