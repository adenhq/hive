"""Tests for hive doctor diagnostic command."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.doctor import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    check_api_keys,
    check_disk_space,
    check_global_config,
    check_mcp_config,
    check_os_compatibility,
    check_python_version,
    check_uv_installed,
    format_report,
    run_doctor,
)


class TestDoctorReport:
    def test_empty_report_is_healthy(self):
        report = DoctorReport()
        assert report.is_healthy is True

    def test_report_counts(self):
        report = DoctorReport(results=[
            CheckResult("a", CheckStatus.PASS, "ok"),
            CheckResult("b", CheckStatus.PASS, "ok"),
            CheckResult("c", CheckStatus.WARN, "meh"),
            CheckResult("d", CheckStatus.FAIL, "bad"),
        ])
        assert report.passed == 2
        assert report.warnings == 1
        assert report.failures == 1
        assert report.is_healthy is False

    def test_warnings_only_is_healthy(self):
        report = DoctorReport(results=[
            CheckResult("a", CheckStatus.PASS, "ok"),
            CheckResult("b", CheckStatus.WARN, "meh"),
        ])
        assert report.is_healthy is True


class TestCheckPythonVersion:
    def test_current_python_passes(self):
        result = check_python_version()
        assert result.status in (CheckStatus.PASS, CheckStatus.WARN)


class TestCheckUvInstalled:
    @patch("shutil.which", return_value=None)
    def test_uv_not_found(self, _):
        result = check_uv_installed()
        assert result.status == CheckStatus.WARN

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/uv")
    def test_uv_found(self, _, mock_run):
        mock_run.return_value = MagicMock(stdout="uv 0.5.2\n", returncode=0)
        result = check_uv_installed()
        assert result.status == CheckStatus.PASS


class TestCheckApiKeys:
    def test_no_keys_fails(self):
        with patch.dict(os.environ, {}, clear=True):
            result = check_api_keys()
            assert result.status == CheckStatus.FAIL

    def test_anthropic_key_passes(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-api03-xxxxxxxxxxxx"}, clear=True):
            result = check_api_keys()
            assert result.status == CheckStatus.PASS

    def test_only_openai_key_warns(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-xxxxxxxxxxxxxxxxxxxx"}, clear=True):
            result = check_api_keys()
            assert result.status == CheckStatus.WARN


class TestCheckMcpConfig:
    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = check_mcp_config()
        assert result.status == CheckStatus.WARN

    def test_valid_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = {"mcpServers": {"agent-builder": {}, "tools": {}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))
        result = check_mcp_config()
        assert result.status == CheckStatus.PASS

    def test_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mcp.json").write_text("{bad json")
        result = check_mcp_config()
        assert result.status == CheckStatus.FAIL


class TestCheckOsCompatibility:
    @patch("platform.system", return_value="Linux")
    @patch("platform.release", return_value="6.1.0")
    @patch("platform.machine", return_value="x86_64")
    def test_linux_passes(self, *_):
        result = check_os_compatibility()
        assert result.status == CheckStatus.PASS

    @patch("platform.system", return_value="Windows")
    @patch("platform.machine", return_value="AMD64")
    def test_windows_warns(self, *_):
        result = check_os_compatibility()
        assert result.status == CheckStatus.WARN


class TestFormatReport:
    def test_healthy_report(self):
        report = DoctorReport(results=[CheckResult("Test", CheckStatus.PASS, "all good")])
        output = format_report(report)
        assert "Hive Environment Check" in output
        assert "1 passed" in output

    def test_unhealthy_report(self):
        report = DoctorReport(results=[CheckResult("Bad", CheckStatus.FAIL, "broken", fix_hint="fix it")])
        output = format_report(report)
        assert "fix it" in output


class TestRunDoctor:
    def test_returns_report(self):
        report = run_doctor()
        assert isinstance(report, DoctorReport)
        assert len(report.results) > 0
