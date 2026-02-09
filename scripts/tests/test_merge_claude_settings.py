"""Tests for scripts/merge_claude_settings.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the merge script as a module (scripts/ is not a package).
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "merge_claude_settings.py"
_spec = importlib.util.spec_from_file_location("merge_claude_settings", _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
merge_settings = _mod.merge_settings
main = _mod.main

# Path to the real example file shipped in the repo.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REAL_EXAMPLE = REPO_ROOT / ".claude" / "settings.local.json.example"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EXAMPLE_CONTENT = {
    "permissions": {
        "allow": [
            "mcp__agent-builder__*",
            "mcp__tools__*",
            "Bash(uv run *)",
        ]
    },
    "enableAllProjectMcpServers": True,
    "enabledMcpjsonServers": ["agent-builder", "tools"],
}


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ===================================================================
# Unit tests – fresh install
# ===================================================================


class TestFreshInstall:
    """Verify behaviour when no target file exists yet."""

    def test_creates_target_from_example(self, tmp_path):
        """Target should be a copy of the example file."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)

        result = merge_settings(example, target)

        assert result["action"] == "created"
        assert target.exists()
        assert _read_json(target) == EXAMPLE_CONTENT

    def test_creates_parent_directories(self, tmp_path):
        """Missing parent directories should be created automatically."""
        example = tmp_path / "example.json"
        target = tmp_path / "deep" / "nested" / "target.json"
        _write_json(example, EXAMPLE_CONTENT)

        merge_settings(example, target)

        assert target.exists()


# ===================================================================
# Unit tests – merging existing
# ===================================================================


class TestMergeExisting:
    """Verify merge logic when the target file already exists."""

    def test_adds_new_entries(self, tmp_path):
        """New example entries must appear in the merged target."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(target, {"permissions": {"allow": ["Bash(uv run *)"]}})

        result = merge_settings(example, target)

        merged = _read_json(target)
        assert "mcp__agent-builder__*" in merged["permissions"]["allow"]
        assert "mcp__tools__*" in merged["permissions"]["allow"]
        assert result["action"] == "merged"
        assert len(result["new_entries"]) == 2

    def test_deduplicates(self, tmp_path):
        """Overlapping entries must not be duplicated."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {"permissions": {"allow": ["mcp__agent-builder__*", "Bash(uv run *)"]}},
        )

        merge_settings(example, target)

        merged = _read_json(target)
        allow = merged["permissions"]["allow"]
        assert allow.count("mcp__agent-builder__*") == 1
        assert allow.count("Bash(uv run *)") == 1

    def test_preserves_user_entries(self, tmp_path):
        """Personal entries already in the target must be kept."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {"permissions": {"allow": ["Bash(my-custom-script *)"]}},
        )

        merge_settings(example, target)

        merged = _read_json(target)
        assert "Bash(my-custom-script *)" in merged["permissions"]["allow"]

    def test_example_entries_ordered_first(self, tmp_path):
        """Project entries should appear before personal entries."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {"permissions": {"allow": ["Bash(my-custom-script *)"]}},
        )

        merge_settings(example, target)

        merged = _read_json(target)
        allow = merged["permissions"]["allow"]
        # All example entries come first, user entry is last.
        assert allow[-1] == "Bash(my-custom-script *)"
        assert (
            allow[: len(EXAMPLE_CONTENT["permissions"]["allow"])]
            == EXAMPLE_CONTENT["permissions"]["allow"]
        )


# ===================================================================
# Unit tests – top-level key merge
# ===================================================================


class TestTopLevelKeyMerge:
    """Verify that top-level keys are filled but never overwritten."""

    def test_fills_missing_keys(self, tmp_path):
        """Missing top-level keys should be filled from the example."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(target, {"permissions": {"allow": []}})

        merge_settings(example, target)

        merged = _read_json(target)
        assert merged["enableAllProjectMcpServers"] is True
        assert merged["enabledMcpjsonServers"] == ["agent-builder", "tools"]

    def test_does_not_overwrite_existing_keys(self, tmp_path):
        """Existing top-level keys must not be overwritten by example values."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {
                "permissions": {"allow": []},
                "enableAllProjectMcpServers": False,
                "enabledMcpjsonServers": ["custom-server"],
            },
        )

        merge_settings(example, target)

        merged = _read_json(target)
        assert merged["enableAllProjectMcpServers"] is False
        assert merged["enabledMcpjsonServers"] == ["custom-server"]


# ===================================================================
# Unit tests – error handling
# ===================================================================


class TestErrorHandling:
    """Verify correct exceptions for invalid inputs."""

    def test_missing_example_raises(self, tmp_path):
        """A missing example file must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            merge_settings(tmp_path / "missing.json", tmp_path / "target.json")

    def test_malformed_example_raises(self, tmp_path):
        """Invalid JSON in the example must raise JSONDecodeError."""
        example = tmp_path / "example.json"
        example.write_text("{bad json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            merge_settings(example, tmp_path / "target.json")

    def test_malformed_target_raises(self, tmp_path):
        """Invalid JSON in the target must raise JSONDecodeError."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        target.write_text("{bad json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            merge_settings(example, target)

    def test_missing_permissions_key_in_target(self, tmp_path):
        """A target with no 'permissions' key should get one created."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(target, {"someOtherKey": True})

        merge_settings(example, target)

        merged = _read_json(target)
        assert "permissions" in merged
        assert merged["permissions"]["allow"] == EXAMPLE_CONTENT["permissions"]["allow"]

    def test_missing_allow_key_in_target(self, tmp_path):
        """A target with 'permissions' but no 'allow' should get 'allow' created and keep 'deny'."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(target, {"permissions": {"deny": ["Bash(rm *)"]}})

        merge_settings(example, target)

        merged = _read_json(target)
        assert merged["permissions"]["allow"] == EXAMPLE_CONTENT["permissions"]["allow"]
        assert merged["permissions"]["deny"] == ["Bash(rm *)"]


# ===================================================================
# Idempotency
# ===================================================================


class TestIdempotency:
    """Verify that running merge twice produces identical output."""

    def test_idempotent(self, tmp_path):
        """Two consecutive merges must produce the same file content."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {"permissions": {"allow": ["Bash(my-custom-script *)"]}},
        )

        merge_settings(example, target)
        first_pass = target.read_text(encoding="utf-8")

        merge_settings(example, target)
        second_pass = target.read_text(encoding="utf-8")

        assert first_pass == second_pass


# ===================================================================
# CLI tests (subprocess)
# ===================================================================


class TestCLI:
    """Verify the command-line interface via subprocess."""

    def test_cli_fresh_install(self, tmp_path):
        """CLI should exit 0 and print 'Created' for a fresh install."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)

        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT_PATH),
                "--example",
                str(example),
                "--target",
                str(target),
            ],
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0
        assert "Created" in proc.stdout

    def test_cli_merge(self, tmp_path):
        """CLI should exit 0 and report new entries when merging."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(target, {"permissions": {"allow": ["Bash(uv run *)"]}})

        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT_PATH),
                "--example",
                str(example),
                "--target",
                str(target),
            ],
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0
        assert "Merged" in proc.stdout

    def test_cli_missing_example(self, tmp_path):
        """CLI should exit 1 and print 'Error' when example is missing."""
        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT_PATH),
                "--example",
                str(tmp_path / "missing.json"),
                "--target",
                str(tmp_path / "target.json"),
            ],
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 1
        assert "Error" in proc.stderr


# ===================================================================
# End-to-end integration
# ===================================================================


class TestEndToEnd:
    """Integration tests exercising realistic scenarios."""

    def test_full_onboarding_flow(self, tmp_path):
        """Simulate fresh onboarding: create → verify → re-merge → idempotent."""
        example = tmp_path / "example.json"
        target = tmp_path / ".claude" / "settings.local.json"
        _write_json(example, EXAMPLE_CONTENT)

        # First merge – creates target
        result = merge_settings(example, target)
        assert result["action"] == "created"

        merged = _read_json(target)
        assert merged["permissions"]["allow"] == EXAMPLE_CONTENT["permissions"]["allow"]
        assert merged["enableAllProjectMcpServers"] is True
        assert merged["enabledMcpjsonServers"] == ["agent-builder", "tools"]

        # Second merge – idempotent
        result2 = merge_settings(example, target)
        assert result2["action"] == "merged"
        assert len(result2["new_entries"]) == 0
        assert _read_json(target) == merged

    def test_existing_contributor_preserves_custom(self, tmp_path):
        """Contributor already has custom settings: merge adds project entries, keeps theirs."""
        example = tmp_path / "example.json"
        target = tmp_path / "target.json"
        _write_json(example, EXAMPLE_CONTENT)
        _write_json(
            target,
            {
                "permissions": {
                    "allow": ["Bash(my-custom *)", "Bash(npm test *)"],
                    "deny": ["Bash(rm -rf *)"],
                },
                "customUserKey": 42,
            },
        )

        merge_settings(example, target)

        merged = _read_json(target)
        # Personal entries preserved
        assert "Bash(my-custom *)" in merged["permissions"]["allow"]
        assert "Bash(npm test *)" in merged["permissions"]["allow"]
        assert merged["permissions"]["deny"] == ["Bash(rm -rf *)"]
        assert merged["customUserKey"] == 42
        # Project entries added
        for entry in EXAMPLE_CONTENT["permissions"]["allow"]:
            assert entry in merged["permissions"]["allow"]

    def test_example_file_is_valid(self):
        """The real .claude/settings.local.json.example in the repo must be valid."""
        assert REAL_EXAMPLE.exists(), f"Example file missing: {REAL_EXAMPLE}"
        data = json.loads(REAL_EXAMPLE.read_text(encoding="utf-8"))
        assert "permissions" in data
        assert "allow" in data["permissions"]
        allow = data["permissions"]["allow"]
        # Spot-check critical patterns — MCP wildcards
        assert any("mcp__agent-builder__" in e for e in allow)
        assert any("mcp__tools__" in e for e in allow)
        # Bash commands from agent generation flow
        assert any("Bash(PYTHONPATH=" in e for e in allow)
        assert any("Bash(MOCK_MODE=" in e for e in allow)
        assert any("Bash(cd " in e for e in allow)
        assert any("Bash(uv run" in e for e in allow)
        assert any("Bash(uv pip" in e for e in allow)
        assert any("Bash(python3" in e for e in allow)
        assert any("Bash(pytest" in e for e in allow)
        assert any("Bash(ruff" in e for e in allow)
        assert any("Bash(mkdir" in e for e in allow)
        assert any("Bash(ls" in e for e in allow)
        assert any("Bash(export" in e for e in allow)
        assert any("Bash(gh" in e for e in allow)
        # All skills used in the workflow
        assert any("Skill(agent-workflow)" in e for e in allow)
        assert any("Skill(building-agents-construction)" in e for e in allow)
        assert any("Skill(building-agents-core)" in e for e in allow)
        assert any("Skill(building-agents-patterns)" in e for e in allow)
        assert any("Skill(testing-agent)" in e for e in allow)
        assert any("Skill(setup-credentials)" in e for e in allow)
        assert any("Skill(triage-issue)" in e for e in allow)
        # Top-level config
        assert data.get("enableAllProjectMcpServers") is True
        assert "agent-builder" in data.get("enabledMcpjsonServers", [])
