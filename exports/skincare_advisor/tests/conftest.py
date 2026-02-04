"""Shared test fixtures for Skincare Product Advisor tests."""

import json
import os
import re

import pytest


@pytest.fixture(scope="session")
def mock_mode():
    """Return True if running in mock mode (structure validation only)."""
    return bool(os.environ.get("MOCK_MODE", "1"))


@pytest.fixture(scope="session")
def agent():
    """Create a default agent instance for testing."""
    from exports.skincare_advisor import default_agent

    return default_agent


@pytest.fixture
def sample_input():
    """Standard test input for skincare evaluation."""
    return {
        "user_id": "test_user",
        "product_query": (
            "Evaluate: CeraVe Moisturizing Cream. "
            "Skin type: combination. "
            "Current routine: CeraVe Foaming Cleanser, The Ordinary Niacinamide 10%"
        ),
        "routine_update": "",
    }


@pytest.fixture
def sample_input_with_update():
    """Test input with routine update feedback."""
    return {
        "user_id": "test_user",
        "product_query": (
            "Evaluate: The Ordinary Hyaluronic Acid 2% + B5. "
            "Skin type: dry. "
            "Current routine: Cetaphil Gentle Cleanser, CeraVe PM Moisturizer"
        ),
        "routine_update": (
            "Added The Ordinary Hyaluronic Acid 2 weeks ago. "
            "Skin feels more hydrated, no breakouts or irritation."
        ),
    }


@pytest.fixture
def sensitive_skin_input():
    """Test input for sensitive skin with known irritants."""
    return {
        "user_id": "test_sensitive",
        "product_query": (
            "Evaluate: La Roche-Posay Toleriane Double Repair Moisturizer. "
            "Skin type: sensitive. "
            "Known sensitivities: fragrance, essential oils, alcohol denat. "
            "Current routine: Vanicream Gentle Cleanser, Vanicream Moisturizing Cream"
        ),
        "routine_update": "",
    }


def parse_json_from_output(result, key):
    """Parse JSON from agent output (framework may store full LLM response as string)."""
    if result.output is None:
        return None

    response_text = result.output.get(key, "")
    if isinstance(response_text, (dict, list)):
        return response_text

    if isinstance(response_text, str):
        json_text = re.sub(r"```json\s*|\s*```", "", response_text).strip()
        try:
            return json.loads(json_text)
        except (json.JSONDecodeError, TypeError):
            return response_text

    return None


def safe_get_nested(result, key_path, default=None):
    """Safely get nested value from result.output."""
    output = result.output or {}
    current = output

    for key in key_path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, str):
            try:
                json_text = re.sub(r"```json\s*|\s*```", "", current).strip()
                parsed = json.loads(json_text)
                if isinstance(parsed, dict):
                    current = parsed.get(key)
                else:
                    return default
            except json.JSONDecodeError:
                return default
        else:
            return default

    return current if current is not None else default


# Make helpers available via pytest namespace
pytest.parse_json_from_output = parse_json_from_output
pytest.safe_get_nested = safe_get_nested
