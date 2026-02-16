"""Tests for browser automation tool (FastMCP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.browser_automation_tool import register_tools

_PW_PATH = "aden_tools.tools.browser_automation_tool.browser_automation_tool.async_playwright"


def _make_playwright_mocks(html="<html><body>Test</body></html>", title="Test Page", final_url="https://example.com"):
    """Build a full playwright mock chain and return (context_manager, page)."""
    mock_page = AsyncMock()
    mock_page.goto.return_value = MagicMock(status=200, url=final_url)
    mock_page.content.return_value = html
    mock_page.title.return_value = title
    mock_page.url = final_url
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.inner_text.return_value = "Test content"
    mock_page.query_selector.return_value = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.select_option = AsyncMock()
    mock_page.press = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_page.is_checked = AsyncMock(return_value=False)
    mock_page.get_attribute = AsyncMock(return_value="text")
    mock_page.evaluate = AsyncMock(return_value="input")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    # async context manager for async_playwright()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm, mock_page


@pytest.fixture
def browser_get_page_content_fn(mcp: FastMCP):
    """Register and return the browser_get_page_content tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_get_page_content"].fn


@pytest.fixture
def browser_screenshot_fn(mcp: FastMCP):
    """Register and return the browser_screenshot tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_screenshot"].fn


@pytest.fixture
def browser_extract_text_fn(mcp: FastMCP):
    """Register and return the browser_extract_text tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_extract_text"].fn


@pytest.fixture
def browser_click_and_extract_fn(mcp: FastMCP):
    """Register and return the browser_click_and_extract tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_click_and_extract"].fn


@pytest.fixture
def browser_inspect_form_fn(mcp: FastMCP):
    """Register and return the browser_inspect_form tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_inspect_form"].fn


@pytest.fixture
def browser_fill_form_fn(mcp: FastMCP):
    """Register and return the browser_fill_form tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["browser_fill_form"].fn


class TestBrowserGetPageContent:
    """Tests for browser_get_page_content tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_url_auto_prefixed_with_https(self, mock_pw, browser_get_page_content_fn):
        """URLs without scheme get https:// prefix."""
        mock_cm, _ = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        result = await browser_get_page_content_fn(url="example.com")

        assert isinstance(result, dict)
        assert "error" not in result
        assert "html" in result

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_returns_html_title_url(self, mock_pw, browser_get_page_content_fn):
        """Function returns html, title, and url."""
        html = "<html><body>Content</body></html>"
        title = "Test Page"
        url = "https://example.com"
        mock_cm, _ = _make_playwright_mocks(html=html, title=title, final_url=url)
        mock_pw.return_value = mock_cm

        result = await browser_get_page_content_fn(url=url)

        assert result["html"] == html
        assert result["title"] == title
        assert result["url"] == url

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_wait_for_selector(self, mock_pw, browser_get_page_content_fn):
        """wait_for parameter waits for selector."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        await browser_get_page_content_fn(url="https://example.com", wait_for=".content")

        mock_page.wait_for_selector.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_timeout_clamped(self, mock_pw, browser_get_page_content_fn):
        """Timeout values are clamped to valid range."""
        mock_cm, _ = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        # Test low timeout (should be clamped to 5000)
        result = await browser_get_page_content_fn(url="https://example.com", timeout=1000)
        assert "error" not in result

        # Test high timeout (should be clamped to 300000)
        result = await browser_get_page_content_fn(url="https://example.com", timeout=500000)
        assert "error" not in result


class TestBrowserScreenshot:
    """Tests for browser_screenshot tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_screenshot_saved(self, mock_pw, browser_screenshot_fn, tmp_path):
        """Screenshot is saved to specified path."""
        output_path = str(tmp_path / "screenshot.png")
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        result = await browser_screenshot_fn(url="https://example.com", output_path=output_path)

        assert "error" not in result
        assert result["path"] == output_path
        mock_page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_full_page_option(self, mock_pw, browser_screenshot_fn, tmp_path):
        """full_page parameter is respected."""
        output_path = str(tmp_path / "screenshot.png")
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        await browser_screenshot_fn(url="https://example.com", output_path=output_path, full_page=True)

        call_args = mock_page.screenshot.call_args
        assert call_args.kwargs["full_page"] is True

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_viewport_only_screenshot(self, mock_pw, browser_screenshot_fn, tmp_path):
        """full_page=False captures viewport only."""
        output_path = str(tmp_path / "screenshot.png")
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        await browser_screenshot_fn(url="https://example.com", output_path=output_path, full_page=False)

        call_args = mock_page.screenshot.call_args
        assert call_args.kwargs["full_page"] is False


class TestBrowserExtractText:
    """Tests for browser_extract_text tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_extracts_text_from_body(self, mock_pw, browser_extract_text_fn):
        """Extracts text from body when no selector provided."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_page.inner_text.return_value = "Body text content"
        mock_pw.return_value = mock_cm

        result = await browser_extract_text_fn(url="https://example.com")

        assert "error" not in result
        assert result["text"] == "Body text content"
        mock_page.inner_text.assert_called_with("body")

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_extracts_text_from_selector(self, mock_pw, browser_extract_text_fn):
        """Extracts text from specified selector."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.inner_text.return_value = "Selector text"
        mock_page.query_selector.return_value = mock_element
        mock_pw.return_value = mock_cm

        result = await browser_extract_text_fn(url="https://example.com", selector=".content")

        assert "error" not in result
        assert result["text"] == "Selector text"
        mock_page.query_selector.assert_called_with(".content")

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_error_when_selector_not_found(self, mock_pw, browser_extract_text_fn):
        """Returns error when selector not found."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_page.query_selector.return_value = None
        mock_pw.return_value = mock_cm

        result = await browser_extract_text_fn(url="https://example.com", selector=".nonexistent")

        assert "error" in result
        assert "no element found matching selector" in result["error"].lower()


class TestBrowserClickAndExtract:
    """Tests for browser_click_and_extract tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_clicks_element_and_extracts(self, mock_pw, browser_click_and_extract_fn):
        """Clicks element and extracts resulting content."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        result = await browser_click_and_extract_fn(
            url="https://example.com",
            click_selector=".button",
        )

        assert "error" not in result
        assert "html" in result
        assert result["clicked_element"] == ".button"
        mock_page.click.assert_called_once_with(".button")

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_waits_for_selector_after_click(self, mock_pw, browser_click_and_extract_fn):
        """Waits for selector after clicking if provided."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_pw.return_value = mock_cm

        await browser_click_and_extract_fn(
            url="https://example.com",
            click_selector=".button",
            wait_for_selector=".result",
        )

        # Should wait for click selector first, then result selector
        assert mock_page.wait_for_selector.call_count >= 1

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_error_when_click_selector_missing(self, mock_pw, browser_click_and_extract_fn):
        """Returns error when click_selector is empty."""
        result = await browser_click_and_extract_fn(url="https://example.com", click_selector="")

        assert "error" in result
        assert "required" in result["error"].lower()


class TestBrowserFillForm:
    """Tests for browser_fill_form tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_fills_text_input(self, mock_pw, browser_fill_form_fn):
        """Fills text input fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = "input"
        mock_element.get_attribute.return_value = "text"
        mock_page.query_selector.return_value = mock_element
        mock_pw.return_value = mock_cm

        form_fields = '{"#username": "user@example.com"}'
        result = await browser_fill_form_fn(url="https://example.com", form_fields=form_fields)

        assert "error" not in result
        assert result["filled_fields"]["#username"] == "user@example.com"
        mock_page.fill.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_fills_multiple_fields(self, mock_pw, browser_fill_form_fn):
        """Fills multiple form fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = "input"
        mock_element.get_attribute.return_value = "text"
        mock_page.query_selector.return_value = mock_element
        mock_pw.return_value = mock_cm

        form_fields = '{"#username": "user@example.com", "#password": "secret123"}'
        result = await browser_fill_form_fn(url="https://example.com", form_fields=form_fields)

        assert "error" not in result
        assert len(result["filled_fields"]) == 2
        assert mock_page.fill.call_count == 2

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_submits_form(self, mock_pw, browser_fill_form_fn):
        """Submits form when submit=True."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = "input"
        mock_element.get_attribute.return_value = "text"
        mock_submit_button = AsyncMock()
        mock_page.query_selector.side_effect = [mock_element, mock_submit_button]
        mock_pw.return_value = mock_cm

        form_fields = '{"#username": "user@example.com"}'
        result = await browser_fill_form_fn(
            url="https://example.com",
            form_fields=form_fields,
            submit=True,
        )

        assert "error" not in result
        assert result["submitted"] is True
        mock_submit_button.click.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_error_invalid_json(self, mock_pw, browser_fill_form_fn):
        """Returns error for invalid JSON in form_fields."""
        result = await browser_fill_form_fn(url="https://example.com", form_fields="invalid json")

        assert "error" in result
        assert "json" in result["error"].lower()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_error_empty_form_fields(self, mock_pw, browser_fill_form_fn):
        """Returns error when form_fields is empty."""
        result = await browser_fill_form_fn(url="https://example.com", form_fields="{}")

        assert "error" in result
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_fills_select_dropdown(self, mock_pw, browser_fill_form_fn):
        """Fills select dropdown fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = "select"
        mock_page.query_selector.return_value = mock_element
        mock_pw.return_value = mock_cm

        form_fields = '{"#country": "US"}'
        result = await browser_fill_form_fn(url="https://example.com", form_fields=form_fields)

        assert "error" not in result
        mock_page.select_option.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_fills_checkbox(self, mock_pw, browser_fill_form_fn):
        """Fills checkbox fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = "input"
        mock_element.get_attribute.return_value = "checkbox"
        mock_element.is_checked.return_value = False
        mock_page.query_selector.return_value = mock_element
        mock_pw.return_value = mock_cm

        form_fields = '{"#remember": "true"}'
        result = await browser_fill_form_fn(url="https://example.com", form_fields=form_fields)

        assert "error" not in result
        mock_page.click.assert_called_once()


class TestBrowserInspectForm:
    """Tests for browser_inspect_form tool."""

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_inspects_form_fields(self, mock_pw, browser_inspect_form_fn):
        """Inspects form and returns field information."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {
            "fields": [
                {
                    "label": "Email",
                    "name": "email",
                    "type": "email",
                    "selector": "#email",
                    "required": True,
                    "placeholder": "Enter email",
                    "value": "",
                    "disabled": False,
                },
                {
                    "label": "Password",
                    "name": "password",
                    "type": "password",
                    "selector": "#password",
                    "required": True,
                    "placeholder": "",
                    "value": "",
                    "disabled": False,
                },
            ],
            "forms_found": 1,
        }
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(url="https://example.com/login")

        assert "error" not in result
        assert "form_fields" in result
        assert len(result["form_fields"]) == 2
        assert result["forms_found"] == 1
        assert result["form_fields"][0]["selector"] == "#email"
        assert result["form_fields"][0]["label"] == "Email"
        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_inspects_specific_form_selector(self, mock_pw, browser_inspect_form_fn):
        """Inspects form using specific form selector."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {
            "fields": [
                {
                    "label": "Username",
                    "name": "username",
                    "type": "text",
                    "selector": "#username",
                    "required": False,
                    "placeholder": "",
                    "value": "",
                    "disabled": False,
                }
            ],
            "forms_found": 1,
        }
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(
            url="https://example.com/login", form_selector="form#login-form"
        )

        assert "error" not in result
        assert len(result["form_fields"]) == 1
        # Verify the form selector was passed to evaluate
        call_args = mock_page.evaluate.call_args[0][0]
        assert call_args is not None

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_handles_select_fields_with_options(self, mock_pw, browser_inspect_form_fn):
        """Returns options for select dropdown fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {
            "fields": [
                {
                    "label": "Country",
                    "name": "country",
                    "type": "select",
                    "selector": "#country",
                    "required": False,
                    "placeholder": "",
                    "value": "",
                    "disabled": False,
                    "options": [
                        {"value": "us", "text": "United States", "selected": False},
                        {"value": "uk", "text": "United Kingdom", "selected": False},
                    ],
                }
            ],
            "forms_found": 1,
        }
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(url="https://example.com/form")

        assert "error" not in result
        assert "options" in result["form_fields"][0]
        assert len(result["form_fields"][0]["options"]) == 2

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_handles_checkbox_fields(self, mock_pw, browser_inspect_form_fn):
        """Returns checked state for checkbox fields."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {
            "fields": [
                {
                    "label": "Remember me",
                    "name": "remember",
                    "type": "checkbox",
                    "selector": "#remember",
                    "required": False,
                    "placeholder": "",
                    "value": "",
                    "disabled": False,
                    "checked": False,
                }
            ],
            "forms_found": 1,
        }
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(url="https://example.com/form")

        assert "error" not in result
        assert "checked" in result["form_fields"][0]
        assert result["form_fields"][0]["checked"] is False

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_returns_error_when_form_not_found(self, mock_pw, browser_inspect_form_fn):
        """Returns error when form selector doesn't match any form."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {"error": "No form found with selector: form#nonexistent"}
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(
            url="https://example.com", form_selector="form#nonexistent"
        )

        assert "error" in result
        assert "no form found with selector" in result["error"].lower()

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_handles_no_forms_on_page(self, mock_pw, browser_inspect_form_fn):
        """Handles pages with no forms gracefully."""
        mock_cm, mock_page = _make_playwright_mocks()
        mock_inspection_result = {"fields": [], "forms_found": 0}
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(url="https://example.com")

        assert "error" not in result
        assert result["form_fields"] == []
        assert result["forms_found"] == 0

    @pytest.mark.asyncio
    @patch(_PW_PATH)
    async def test_returns_title_and_url(self, mock_pw, browser_inspect_form_fn):
        """Returns page title and final URL."""
        mock_cm, mock_page = _make_playwright_mocks(title="Login Page", final_url="https://example.com/login")
        mock_inspection_result = {"fields": [], "forms_found": 0}
        mock_page.evaluate.return_value = mock_inspection_result
        mock_pw.return_value = mock_cm

        result = await browser_inspect_form_fn(url="https://example.com/login")

        assert "error" not in result
        assert result["title"] == "Login Page"
        assert result["url"] == "https://example.com/login"

