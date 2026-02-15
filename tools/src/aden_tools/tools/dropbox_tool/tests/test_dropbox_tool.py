"""Tests for the Dropbox tool."""

import json
from unittest.mock import MagicMock, patch

import pytest
import httpx

from aden_tools.tools.dropbox_tool.dropbox_tool import register_tools


class TestDropboxTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        # Mocking the decorator behavior
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        self.cred = MagicMock()
        self.cred.get.return_value = "test_token"
        register_tools(self.mcp, credentials=self.cred)

    def _fn(self, name):
        """Retrieve a registered function by its name."""
        return next(f for f in self.fns if f.__name__ == name)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_dropbox_list_folder(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entries": [{"name": "test_dir", ".tag": "folder"}]}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tool = self._fn("dropbox_list_folder")
        result = await tool(path="/test")

        assert "entries" in result
        assert result["entries"][0]["name"] == "test_dir"
        
        # Verify call
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.dropboxapi.com/2/files/list_folder"
        assert kwargs["json"]["path"] == "/test"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_dropbox_upload_file(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test.txt", "id": "id:123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tool = self._fn("dropbox_upload_file")
        result = await tool(file_content="hello", dropbox_path="/test.txt")

        assert result["name"] == "test.txt"
        
        # Verify call
        args, kwargs = mock_post.call_args
        assert args[0] == "https://content.dropboxapi.com/2/files/upload"
        api_arg = json.loads(kwargs["headers"]["Dropbox-API-Arg"])
        assert api_arg["path"] == "/test.txt"
        assert kwargs["content"] == b"hello"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_dropbox_download_file(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "file content"
        mock_response.headers = {"dropbox-api-result": json.dumps({"name": "test.txt"})}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tool = self._fn("dropbox_download_file")
        result = await tool(dropbox_path="/test.txt")

        assert result["file_content"] == "file content"
        assert result["metadata"]["name"] == "test.txt"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_dropbox_create_shared_link(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "https://db.tt/123", "name": "test.txt"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tool = self._fn("dropbox_create_shared_link")
        result = await tool(path="/test.txt")

        assert result["url"] == "https://db.tt/123"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_no_token_error(self, mock_post):
        self.cred.get.return_value = None
        with patch.dict("os.environ", {}, clear=True):
            tool = self._fn("dropbox_list_folder")
            result = await tool(path="/test")
            assert "error" in result
            assert "token not configured" in result["error"]
