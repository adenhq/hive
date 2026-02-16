"""
Browser Automation Tool for Hive Agents.

Provides browser-based web interaction capabilities for
scraping dynamic content, filling forms, taking screenshots,
and interacting with JavaScript-rendered pages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from playwright.async_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)

# Browser-like User-Agent for actual page requests
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def register_tools(mcp: FastMCP) -> None:
    """Register browser automation tools with the MCP server."""

    @mcp.tool()
    async def browser_get_page_content(
        url: str,
        wait_for: str | None = None,
        timeout: int = 30000,
    ) -> dict:
        """
        Navigate to a URL using a headless browser and return the fully rendered HTML content.

        Use this when you need to extract HTML from JavaScript-rendered pages,
        SPAs, or dynamic content that requires browser execution.

        Args:
            url: The URL to navigate to
            wait_for: Optional CSS selector to wait for before extracting content
            timeout: Maximum time in milliseconds to wait for page load (default: 30000)

        Returns:
            Dict with keys: html, title, url (final URL after redirects) or error dict
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Validate timeout
            timeout = max(5000, min(timeout, 300000))  # 5s to 5min

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="networkidle")

                    # Wait for specific selector if provided
                    if wait_for:
                        await page.wait_for_selector(wait_for, timeout=timeout)

                    content = await page.content()
                    title = await page.title()
                    final_url = page.url

                    return {
                        "html": content,
                        "title": title,
                        "url": final_url,
                    }
                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to get page content: {e!s}"}

    @mcp.tool()
    async def browser_screenshot(
        url: str,
        output_path: str = "screenshot.png",
        full_page: bool = True,
        timeout: int = 30000,
    ) -> dict:
        """
        Navigate to a URL and capture a screenshot.

        Use this when you need a visual snapshot of a webpage for reporting,
        monitoring, debugging, or documentation purposes.

        Args:
            url: The URL to screenshot
            output_path: File path to save the screenshot (default: "screenshot.png")
            full_page: If True, capture full scrollable page; if False, capture viewport only
            timeout: Maximum time in milliseconds to wait for page load (default: 30000)

        Returns:
            Dict with keys: path, width, height or error dict
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Validate timeout
            timeout = max(5000, min(timeout, 300000))  # 5s to 5min

            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="networkidle")

                    await page.screenshot(path=str(output_path), full_page=full_page)

                    viewport = page.viewport_size
                    await browser.close()

                    return {
                        "path": str(output_path),
                        "width": viewport["width"] if viewport else None,
                        "height": viewport["height"] if viewport else None,
                    }
                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to capture screenshot: {e!s}"}

    @mcp.tool()
    async def browser_extract_text(
        url: str,
        selector: str | None = None,
        timeout: int = 30000,
    ) -> dict:
        """
        Navigate to a URL and extract visible text content.

        Use this when you need clean text content from a page without HTML tags.
        Works with JavaScript-rendered content.

        Args:
            url: The URL to extract text from
            selector: Optional CSS selector to extract text from a specific element.
                     If None, extracts from body
            timeout: Maximum time in milliseconds to wait for page load (default: 30000)

        Returns:
            Dict with keys: text, title, url or error dict
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Validate timeout
            timeout = max(5000, min(timeout, 300000))  # 5s to 5min

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="networkidle")

                    if selector:
                        element = await page.query_selector(selector)
                        if not element:
                            return {"error": f"No element found matching selector: {selector}"}
                        text = await element.inner_text()
                    else:
                        text = await page.inner_text("body")

                    title = await page.title()
                    final_url = page.url

                    await browser.close()

                    return {
                        "text": text,
                        "title": title,
                        "url": final_url,
                    }
                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to extract text: {e!s}"}

    @mcp.tool()
    async def browser_click_and_extract(
        url: str,
        click_selector: str,
        wait_for_selector: str | None = None,
        timeout: int = 30000,
    ) -> dict:
        """
        Navigate to a URL, click an element, wait for result, and return updated page content.

        Use this when you need to interact with a page (e.g., click a button, link, or tab)
        and then extract the resulting content.

        Args:
            url: The URL to navigate to
            click_selector: CSS selector of the element to click
            wait_for_selector: Optional CSS selector to wait for after clicking
                              (defaults to waiting for network idle)
            timeout: Maximum time in milliseconds to wait for page load (default: 30000)

        Returns:
            Dict with keys: html, title, url, clicked_element or error dict
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Validate timeout
            timeout = max(5000, min(timeout, 300000))  # 5s to 5min

            if not click_selector:
                return {"error": "click_selector is required"}

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="networkidle")

                    # Wait for the element to be clickable
                    await page.wait_for_selector(click_selector, timeout=timeout, state="visible")

                    # Click the element
                    await page.click(click_selector)

                    # Wait for result
                    if wait_for_selector:
                        await page.wait_for_selector(wait_for_selector, timeout=timeout)
                    else:
                        # Wait for network to settle after click
                        await page.wait_for_load_state("networkidle", timeout=timeout)

                    content = await page.content()
                    title = await page.title()
                    final_url = page.url

                    await browser.close()

                    return {
                        "html": content,
                        "title": title,
                        "url": final_url,
                        "clicked_element": click_selector,
                    }
                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to click and extract: {e!s}"}

    @mcp.tool()
    async def browser_inspect_form(
        url: str,
        form_selector: str | None = None,
        timeout: int = 30000,
    ) -> dict:
        """
        Inspect a form on a webpage and return human-readable field information with CSS selectors.

        Use this before browser_fill_form to discover what fields are available on a form.
        The LLM can use this information to ask users for values, then convert those values
        to CSS selectors for browser_fill_form.

        Args:
            url: The URL to navigate to
            form_selector: Optional CSS selector for a specific form element.
                          If None, inspects all forms on the page
            timeout: Maximum time in milliseconds to wait for page load (default: 30000)

        Returns:
            Dict with keys: form_fields (list of field objects), forms_found (count), or error dict.
            Each field object contains: label, name, type, selector, required, placeholder, options (for selects)
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Validate timeout
            timeout = max(5000, min(timeout, 300000))  # 5s to 5min

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="networkidle")

                    # JavaScript to extract form field information
                    inspect_script = """
                    (formSelector) => {
                        const fields = [];
                        
                        // Find form(s) to inspect
                        const forms = formSelector 
                            ? document.querySelectorAll(formSelector)
                            : document.querySelectorAll('form');
                        
                        if (forms.length === 0 && formSelector) {
                            return { error: `No form found with selector: ${formSelector}` };
                        }
                        
                        // If no forms found, look for input fields outside forms
                        const allInputs = formSelector
                            ? document.querySelector(formSelector)?.querySelectorAll('input, textarea, select') || []
                            : document.querySelectorAll('input, textarea, select');
                        
                        const processed = new Set();
                        
                        allInputs.forEach((element, index) => {
                            // Skip hidden inputs (except hidden fields that might be important)
                            const type = element.type || element.tagName.toLowerCase();
                            if (type === 'hidden' && element.name === '') {
                                return;
                            }
                            
                            // Generate a unique selector
                            let selector = '';
                            if (element.id) {
                                selector = `#${element.id}`;
                            } else if (element.name) {
                                selector = `[name="${element.name}"]`;
                                // If multiple elements have same name, add index
                                const sameName = document.querySelectorAll(`[name="${element.name}"]`);
                                if (sameName.length > 1) {
                                    const idx = Array.from(sameName).indexOf(element);
                                    selector = `[name="${element.name}"]:nth-of-type(${idx + 1})`;
                                }
                            } else {
                                // Fallback: use tag + type + index
                                const tag = element.tagName.toLowerCase();
                                const typeAttr = element.type || '';
                                const siblings = Array.from(element.parentElement?.children || [])
                                    .filter(el => el.tagName.toLowerCase() === tag && (el.type || '') === typeAttr);
                                const idx = siblings.indexOf(element);
                                selector = `${tag}${typeAttr ? `[type="${typeAttr}"]` : ''}:nth-of-type(${idx + 1})`;
                            }
                            
                            // Avoid duplicates
                            if (processed.has(selector)) {
                                return;
                            }
                            processed.add(selector);
                            
                            // Find label
                            let label = '';
                            let labelText = '';
                            
                            // Try to find associated label
                            if (element.id) {
                                const labelEl = document.querySelector(`label[for="${element.id}"]`);
                                if (labelEl) {
                                    labelText = labelEl.textContent?.trim() || '';
                                }
                            }
                            
                            // If no label found, look for parent label or nearby text
                            if (!labelText) {
                                const parentLabel = element.closest('label');
                                if (parentLabel) {
                                    labelText = parentLabel.textContent?.trim() || '';
                                } else {
                                    // Look for preceding label or text node
                                    let prev = element.previousElementSibling;
                                    while (prev && !labelText) {
                                        if (prev.tagName.toLowerCase() === 'label') {
                                            labelText = prev.textContent?.trim() || '';
                                        } else if (prev.textContent?.trim()) {
                                            labelText = prev.textContent.trim();
                                        }
                                        prev = prev.previousElementSibling;
                                    }
                                }
                            }
                            
                            label = labelText || element.name || element.placeholder || selector;
                            
                            // Extract field properties
                            const fieldInfo = {
                                label: label,
                                name: element.name || '',
                                type: type,
                                selector: selector,
                                required: element.hasAttribute('required'),
                                placeholder: element.placeholder || '',
                                value: element.value || '',
                                disabled: element.disabled,
                            };
                            
                            // For select elements, get options
                            if (element.tagName.toLowerCase() === 'select') {
                                const options = Array.from(element.options).map(opt => ({
                                    value: opt.value,
                                    text: opt.text,
                                    selected: opt.selected
                                }));
                                fieldInfo.options = options;
                            }
                            
                            // For checkbox/radio, get checked state
                            if (type === 'checkbox' || type === 'radio') {
                                fieldInfo.checked = element.checked;
                            }
                            
                            fields.push(fieldInfo);
                        });
                        
                        return {
                            fields: fields,
                            forms_found: forms.length || (allInputs.length > 0 ? 1 : 0)
                        };
                    }
                    """

                    # Execute the inspection script
                    # Pass form_selector as argument (or None if not provided)
                    result = await page.evaluate(inspect_script, form_selector if form_selector else None)

                    if isinstance(result, dict) and "error" in result:
                        return result

                    title = await page.title()
                    final_url = page.url

                    await browser.close()

                    return {
                        "form_fields": result.get("fields", []),
                        "forms_found": result.get("forms_found", 0),
                        "title": title,
                        "url": final_url,
                    }
                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to inspect form: {e!s}"}
    
    @mcp.tool()
    async def browser_fill_form(
        url: str,
        form_fields: str,
        submit: bool = False,
        submit_selector: str | None = None,
        wait_for_selector: str | None = None,
        timeout: int = 30000,
    ) -> dict:
        """ 
        Navigate to a URL, fill form fields by CSS selector, optionally submit, and return result. 
        Use this when you need to automate form submissions, login flows, or data entry. 
        Form fields should be provided as a JSON string mapping CSS selectors to values. 
        
        Args: 
            url: The URL to navigate to 
            form_fields: JSON string mapping CSS selectors to values. Use browser_inspect_form tool to get the correct selectors.
                Example: '{"#username": "user@example.com", "#password": "secret123"}' 
            submit: Whether to submit the form after filling (default: False) 
            submit_selector: CSS selector of submit button (if different from form submit) 
            wait_for_selector: Optional CSS selector to wait for after submission (defaults to waiting for network idle) 
            timeout: Maximum time in milliseconds to wait for page load (default: 30000) 
        
        Returns: Dict with keys: html, title, url, filled_fields, submitted or error dict 
        
        """

        try:
            # Normalize URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            timeout = max(5000, min(timeout, 300000))

            # Parse JSON
            try:
                fields_dict: dict[str, str] = json.loads(form_fields)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON in form_fields: {e!s}"}

            if not fields_dict:
                return {"error": "form_fields cannot be empty"}

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

                try:
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=BROWSER_USER_AGENT,
                        locale="en-US",
                    )
                    page = await context.new_page()

                    await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

                    filled_fields: dict[str, str] = {}

                    # Fill Fields
                    for selector, value in fields_dict.items():
                        try:
                            await page.wait_for_selector(
                                selector, timeout=timeout, state="visible"
                            )

                            element = await page.query_selector(selector)
                            if not element:
                                return {"error": f"Element not found: {selector}"}

                            tag_name = await element.evaluate(
                                "el => el.tagName.toLowerCase()"
                            )
                            input_type = (await element.get_attribute("type") or "").lower()

                            # SELECT
                            if tag_name == "select":
                                await page.select_option(selector, str(value))

                            # CHECKBOX / RADIO
                            elif input_type in ("checkbox", "radio"):
                                should_check = str(value).lower() in (
                                    "true",
                                    "1",
                                    "yes",
                                    "on",
                                )
                                is_checked = await element.is_checked()
                                if should_check != is_checked:
                                    await page.click(selector)

                            # TEXT / TEXTAREA / OTHER
                            else:
                                try:
                                    await page.fill(selector, str(value))
                                except Exception:
                                    # Fallback for React-controlled inputs
                                    await page.click(selector)
                                    await page.type(selector, str(value), delay=20)

                            filled_fields[selector] = str(value)

                        except PlaywrightTimeout:
                            return {"error": f"Timeout waiting for field: {selector}"}
                        except Exception as e:
                            return {"error": f"Failed to fill field {selector}: {e!s}"}

                    submitted = False

                    # Submit Handling (Robust)
                    if submit:
                        try:
                            old_content = await page.content()

                            if submit_selector:
                                await page.wait_for_selector(
                                    submit_selector, timeout=timeout, state="visible"
                                )
                                await page.click(submit_selector)
                            else:
                                submit_button = await page.query_selector(
                                    'button[type="submit"], input[type="submit"]'
                                )
                                if not submit_button:
                                    submit_button = await page.query_selector(
                                        "button:has-text('Submit'), button:has-text('submit')"
                                    )

                                if submit_button:
                                    await submit_button.click()
                                else:
                                    last_selector = list(fields_dict.keys())[-1]
                                    await page.press(last_selector, "Enter")

                            submitted = True

                            if wait_for_selector:
                                await page.wait_for_selector(wait_for_selector, timeout=timeout)
                            else:
                                # Wait for any DOM change (short window)
                                try:
                                    await page.wait_for_function(
                                        "(oldHtml) => document.documentElement.outerHTML !== oldHtml",
                                        arg=old_content,
                                        timeout=5000,
                                    )
                                except PlaywrightTimeout:
                                    pass

                                # Small stabilization delay
                                await page.wait_for_timeout(1500)

                        except Exception as e:
                            return {"error": f"Failed to submit form: {e!s}"}


                    # Capture Final State
                    content = await page.content()
                    title = await page.title()
                    final_url = page.url

                    return {
                        "html": content,
                        "title": title,
                        "url": final_url,
                        "filled_fields": filled_fields,
                        "submitted": submitted,
                    }

                finally:
                    await browser.close()

        except PlaywrightTimeout:
            return {"error": f"Request timed out after {timeout}ms"}
        except PlaywrightError as e:
            return {"error": f"Browser error: {e!s}"}
        except Exception as e:
            return {"error": f"Failed to fill form: {e!s}"}