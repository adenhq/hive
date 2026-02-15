"""Tests for the Docker Hub tool."""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from aden_tools.tools.dockerhub_tool.dockerhub_tool import register_tools


class TestDockerHubTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        # Mocking the decorator behavior
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        self.cred = MagicMock()
        self.cred.get.return_value = "dckr_pat_test"
        register_tools(self.mcp, credentials=self.cred)

    def _fn(self, name):
        """Retrieve a registered function by its name."""
        return next(f for f in self.fns if f.__name__ == name)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_dockerhub_list_repositories(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"name": "hive"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        tool = self._fn("dockerhub_list_repositories")
        result = await tool(username="adenhq")

        assert "results" in result
        assert result["results"][0]["name"] == "hive"
        
        # Verify call
        args, kwargs = mock_get.call_args
        assert "/repositories/adenhq/" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer dckr_pat_test"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_dockerhub_list_tags(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"name": "latest"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        tool = self._fn("dockerhub_list_tags")
        result = await tool(namespace="adenhq", repository="hive")

        assert result["results"][0]["name"] == "latest"
        
        args, kwargs = mock_get.call_args
        assert "/repositories/adenhq/hive/tags/" in args[0]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_dockerhub_get_tag_metadata(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "latest", "full_size": 100}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        tool = self._fn("dockerhub_get_tag_metadata")
        result = await tool(namespace="adenhq", repository="hive", tag="latest")

        assert result["name"] == "latest"
        assert result["full_size"] == 100

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        # httpx.HTTPStatusError requires a response
        error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = error

        tool = self._fn("dockerhub_list_repositories")
        result = await tool(username="unknown")
        
        assert "error" in result
        assert "404" in result["error"]
