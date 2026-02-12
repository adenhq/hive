"""Tests for the 5 targeted improvements to Hive core."""

import os
import tempfile
from datetime import UTC, datetime

import pytest

from framework.config import RuntimeConfig
from framework.graph.safe_eval import safe_eval
from framework.graph.validator import OutputValidator
from framework.runtime.event_bus import AgentEvent, EventType

# === 1. safe_eval: BoolOp short-circuit + expanded methods ===


class TestSafeEvalBoolOpShortCircuit:
    """BoolOp must match Python's lazy evaluation semantics."""

    def test_and_short_circuits_on_falsy(self):
        result = safe_eval("False and missing_var", {"x": 1})
        assert result is False

    def test_and_returns_last_truthy(self):
        result = safe_eval("1 and 2 and 3")
        assert result == 3

    def test_or_short_circuits_on_truthy(self):
        result = safe_eval("True or missing_var", {"x": 1})
        assert result is True

    def test_or_returns_last_falsy(self):
        result = safe_eval("0 or '' or None")
        assert result is None

    def test_guard_pattern(self):
        ctx = {"output": {"status": "ready", "data": [1, 2, 3]}}
        result = safe_eval('output.get("status") == "ready" and output.get("data")', ctx)
        assert result == [1, 2, 3]

    def test_guard_pattern_short_circuits(self):
        ctx = {"output": {}}
        result = safe_eval('output.get("status") == "ready" and output["data"]', ctx)
        assert result is False

    def test_or_fallback_pattern(self):
        ctx = {"output": {}}
        result = safe_eval('output.get("name") or "default"', ctx)
        assert result == "default"


class TestSafeEvalExpandedMethods:
    """Expanded method allowlist covers common read-only operations."""

    def test_startswith(self):
        assert safe_eval('"hello".startswith("hel")') is True

    def test_endswith(self):
        assert safe_eval('"hello.py".endswith(".py")') is True

    def test_replace(self):
        assert safe_eval('"hello world".replace("world", "earth")') == "hello earth"

    def test_join(self):
        ctx = {"items": ["a", "b", "c"]}
        assert safe_eval('", ".join(items)', ctx) == "a, b, c"

    def test_find(self):
        assert safe_eval('"abcdef".find("cd")') == 2

    def test_count(self):
        assert safe_eval('"banana".count("a")') == 3

    def test_strip_variants(self):
        assert safe_eval('"  hi  ".lstrip()') == "hi  "
        assert safe_eval('"  hi  ".rstrip()') == "  hi"

    def test_capitalize_title(self):
        assert safe_eval('"hello world".title()') == "Hello World"
        assert safe_eval('"hello".capitalize()') == "Hello"

    def test_isdigit(self):
        assert safe_eval('"123".isdigit()') is True
        assert safe_eval('"12a".isdigit()') is False

    def test_dict_copy(self):
        ctx = {"d": {"a": 1}}
        result = safe_eval("d.copy()", ctx)
        assert result == {"a": 1}

    def test_format_is_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            safe_eval('"{0}".format("test")')

    def test_setdefault_is_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            safe_eval('d.setdefault("b", 2)', {"d": {"a": 1}})

    def test_unsafe_methods_still_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            safe_eval('"test".__class__')

        with pytest.raises((NameError, ValueError)):
            safe_eval('open("file.txt")')


# === 2. security.py: symlink protection ===

try:
    from aden_tools.tools.file_system_toolkits import security as security_mod

    _has_security = True
except ImportError:
    _has_security = False


@pytest.mark.skipif(not _has_security, reason="aden_tools not installed")
class TestSecuritySymlinkProtection:
    """realpath resolves symlinks before containment check."""

    def test_normal_path_still_works(self):
        result = security_mod.get_secure_path("test.txt", "ws1", "agent1", "session1")
        assert result.endswith("test.txt")
        assert "ws1" in result

    def test_traversal_blocked(self):
        with pytest.raises(ValueError, match="outside the session sandbox"):
            security_mod.get_secure_path("../../etc/passwd", "ws1", "agent1", "session1")

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks need privileges on Windows")
    def test_symlink_outside_sandbox_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            secret = os.path.join(tmpdir, "secret.txt")
            with open(secret, "w") as f:
                f.write("sensitive")

            sandbox = os.path.join(tmpdir, "sandbox")
            os.makedirs(sandbox)
            link = os.path.join(sandbox, "innocent.txt")
            os.symlink(secret, link)

            resolved = os.path.realpath(link)
            sandbox_real = os.path.realpath(sandbox)
            assert not resolved.startswith(sandbox_real)


# === 3. event_bus.py: timezone-aware timestamps ===


class TestEventBusTimezone:
    """AgentEvent timestamps must be timezone-aware."""

    def test_timestamp_has_tzinfo(self):
        event = AgentEvent(type=EventType.CUSTOM, stream_id="test")
        assert event.timestamp.tzinfo is not None

    def test_timestamp_is_utc(self):
        event = AgentEvent(type=EventType.CUSTOM, stream_id="test")
        assert event.timestamp.tzinfo == UTC

    def test_to_dict_includes_timezone(self):
        event = AgentEvent(type=EventType.CUSTOM, stream_id="test")
        iso = event.to_dict()["timestamp"]
        assert "+" in iso or "Z" in iso

    def test_timestamp_close_to_now(self):
        before = datetime.now(UTC)
        event = AgentEvent(type=EventType.CUSTOM, stream_id="test")
        after = datetime.now(UTC)
        assert before <= event.timestamp <= after


# === 4. validator.py: reduced false positives ===


class TestValidatorFalsePositives:
    """Single contextual keywords should not trigger detection."""

    def test_natural_text_with_from(self):
        validator = OutputValidator()
        text = "The data from the customer API was processed successfully."
        assert validator._contains_code_indicators(text) is False

    def test_natural_text_with_class(self):
        validator = OutputValidator()
        text = "The middle class economy is growing rapidly."
        assert validator._contains_code_indicators(text) is False

    def test_natural_text_with_import(self):
        validator = OutputValidator()
        text = "This is an important decision for the company."
        assert validator._contains_code_indicators(text) is False

    def test_natural_text_with_let(self):
        validator = OutputValidator()
        text = "Let me help you with that request."
        assert validator._contains_code_indicators(text) is False

    def test_natural_text_with_two_keywords(self):
        validator = OutputValidator()
        text = "Let me explain the import process from the warehouse."
        assert validator._contains_code_indicators(text) is False

    def test_three_keywords_triggers(self):
        validator = OutputValidator()
        text = "def foo():\n    import os\n    from sys import argv"
        assert validator._contains_code_indicators(text) is True

    def test_strict_sql_single_match(self):
        validator = OutputValidator()
        assert validator._contains_code_indicators("DROP TABLE users") is True

    def test_strict_script_single_match(self):
        validator = OutputValidator()
        assert validator._contains_code_indicators("<script>alert('xss')</script>") is True

    def test_strict_async_def_single_match(self):
        validator = OutputValidator()
        assert validator._contains_code_indicators("async def handler(): pass") is True


# === 5. config.py: API key masking ===


class TestRuntimeConfigRepr:
    """RuntimeConfig repr must mask API keys."""

    def test_long_key_masked(self):
        cfg = RuntimeConfig(api_key="sk-1234567890abcdef")
        r = repr(cfg)
        assert "sk-1234567890abcdef" not in r
        assert "****cdef" in r

    def test_short_key_fully_masked(self):
        cfg = RuntimeConfig(api_key="abc")
        r = repr(cfg)
        assert "abc" not in r
        assert "****" in r

    def test_none_key(self):
        cfg = RuntimeConfig(api_key=None)
        r = repr(cfg)
        assert "****" in r
        assert "None" not in r.split("api_key=")[1].split(",")[0]

    def test_model_visible(self):
        cfg = RuntimeConfig(model="test/model", api_key="sk-secret")
        r = repr(cfg)
        assert "test/model" in r
