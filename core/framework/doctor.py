"""
Hive Doctor - Environment diagnostic command.

Validates the local development environment and provides actionable
fix suggestions for common setup issues. Inspired by flutter doctor.

Usage:
    hive doctor
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class CheckStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix_hint: Optional[str] = None
    details: Optional[str] = None


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)

    @property
    def failures(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)

    @property
    def is_healthy(self) -> bool:
        return self.failures == 0


def check_python_version() -> CheckResult:
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    python_path = sys.executable
    if version < (3, 11):
        return CheckResult(
            name="Python version",
            status=CheckStatus.FAIL,
            message=f"Python {version_str} ({python_path})",
            fix_hint="Hive requires Python 3.11+. Install via:\n   brew install python@3.12  (macOS)\n   sudo apt install python3.12  (Ubuntu)\n   Or use pyenv: pyenv install 3.12.1",
        )
    if version >= (3, 14):
        return CheckResult(
            name="Python version",
            status=CheckStatus.WARN,
            message=f"Python {version_str} ({python_path})",
            fix_hint="Python 3.14+ has not been tested with Hive. Consider using Python 3.11-3.13.",
        )
    details = None
    if version >= (3, 13):
        details = "Python 3.13+ requires --with-pip for venv creation. quickstart.sh handles this via uv."
    return CheckResult(
        name="Python version",
        status=CheckStatus.PASS,
        message=f"Python {version_str} ({python_path})",
        details=details,
    )


def check_uv_installed() -> CheckResult:
    uv_path = shutil.which("uv")
    if uv_path is None:
        return CheckResult(
            name="uv package manager",
            status=CheckStatus.WARN,
            message="uv not found",
            fix_hint="uv is recommended for faster setup. Install via:\n   curl -LsSf https://astral.sh/uv/install.sh | sh\n   Or: pip install uv",
        )
    try:
        result = subprocess.run([uv_path, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        version = "unknown version"
    return CheckResult(name="uv package manager", status=CheckStatus.PASS, message=f"{version} ({uv_path})")


def _check_venv(venv_path: Path, package_name: str, import_name: str, label: str) -> CheckResult:
    if not venv_path.exists():
        return CheckResult(name=label, status=CheckStatus.FAIL, message=f"{venv_path}/ not found", fix_hint="Run ./quickstart.sh to set up the environment.")
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_path / "Scripts" / "python.exe"
    if not venv_python.exists():
        return CheckResult(name=label, status=CheckStatus.FAIL, message=f"{venv_path}/ exists but Python binary not found", fix_hint=f"rm -rf {venv_path} && ./quickstart.sh")
    try:
        result = subprocess.run([str(venv_python), "-c", f"import {import_name}; print('ok')"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return CheckResult(name=label, status=CheckStatus.PASS, message=f"{package_name} package installed (editable)")
        else:
            return CheckResult(name=label, status=CheckStatus.FAIL, message=f"{venv_path}/ exists but {import_name} not importable", fix_hint=f"cd {venv_path.parent} && uv pip install -e .", details=result.stderr[:200] if result.stderr else None)
    except (subprocess.TimeoutExpired, OSError) as e:
        return CheckResult(name=label, status=CheckStatus.WARN, message=f"Could not verify {package_name} installation: {e}")


def check_core_venv() -> CheckResult:
    return _check_venv(Path("core/.venv"), "framework", "framework", "Core framework venv")


def check_tools_venv() -> CheckResult:
    return _check_venv(Path("tools/.venv"), "aden_tools", "aden_tools", "Tools package venv")


def check_api_keys() -> CheckResult:
    has_any_llm_key = False
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key and len(anthropic_key) > 8:
        has_any_llm_key = True
    for key in ("OPENAI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(key, "")
        if val and len(val) > 8:
            has_any_llm_key = True
    if not has_any_llm_key:
        return CheckResult(name="LLM API keys", status=CheckStatus.FAIL, message="No LLM API keys found", fix_hint='Set at least one LLM provider key:\n   export ANTHROPIC_API_KEY="sk-ant-..."  (recommended)\n   export OPENAI_API_KEY="sk-..."         (alternative)\nAdd to ~/.bashrc or ~/.zshrc to persist.')
    if not (anthropic_key and len(anthropic_key) > 8):
        return CheckResult(name="LLM API keys", status=CheckStatus.WARN, message="ANTHROPIC_API_KEY not set (other LLM key found)", fix_hint="Anthropic is the default provider. Set the key or update\n~/.hive/configuration.json to use a different provider.")
    return CheckResult(name="LLM API keys", status=CheckStatus.PASS, message="ANTHROPIC_API_KEY configured")


def check_mcp_config() -> CheckResult:
    mcp_path = Path(".mcp.json")
    if not mcp_path.exists():
        return CheckResult(name="MCP configuration", status=CheckStatus.WARN, message=".mcp.json not found in project root", fix_hint="Run ./quickstart.sh or copy from the repo template.")
    try:
        with open(mcp_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return CheckResult(name="MCP configuration", status=CheckStatus.FAIL, message=f".mcp.json has invalid JSON: {e}", fix_hint="Fix the syntax error or re-copy from the repo template.")
    servers = config.get("mcpServers", {})
    if not servers:
        return CheckResult(name="MCP configuration", status=CheckStatus.WARN, message=".mcp.json exists but no servers configured")
    server_names = list(servers.keys())
    return CheckResult(name="MCP configuration", status=CheckStatus.PASS, message=f"Servers configured: {', '.join(server_names)}")


def check_global_config() -> CheckResult:
    config_path = Path.home() / ".hive" / "configuration.json"
    if not config_path.exists():
        return CheckResult(name="Global config", status=CheckStatus.WARN, message="~/.hive/configuration.json not found", fix_hint="Created automatically by ./quickstart.sh.")
    try:
        with open(config_path) as f:
            config = json.load(f)
        model = config.get("llm", {}).get("model", "unknown")
        provider = config.get("llm", {}).get("provider", "unknown")
        return CheckResult(name="Global config", status=CheckStatus.PASS, message=f"Provider: {provider}, Model: {model}")
    except (json.JSONDecodeError, KeyError) as e:
        return CheckResult(name="Global config", status=CheckStatus.WARN, message=f"Config exists but could not parse: {e}")


def check_disk_space() -> CheckResult:
    try:
        usage = shutil.disk_usage(Path.home())
        free_gb = usage.free / (1024**3)
        if free_gb < 0.5:
            return CheckResult(name="Disk space", status=CheckStatus.FAIL, message=f"{free_gb:.1f} GB free", fix_hint="Hive needs at least 500 MB free.")
        elif free_gb < 2.0:
            return CheckResult(name="Disk space", status=CheckStatus.WARN, message=f"{free_gb:.1f} GB free (low)")
        else:
            return CheckResult(name="Disk space", status=CheckStatus.PASS, message=f"{free_gb:.1f} GB free")
    except OSError:
        return CheckResult(name="Disk space", status=CheckStatus.SKIP, message="Could not determine disk space")


def check_git_repo() -> CheckResult:
    if not Path("core").exists() or not Path("tools").exists():
        return CheckResult(name="Project root", status=CheckStatus.WARN, message="Not in the Hive project root", fix_hint="Run hive doctor from the hive/ project root directory.")
    return CheckResult(name="Project root", status=CheckStatus.PASS, message="Hive repository detected")


def check_os_compatibility() -> CheckResult:
    system = platform.system()
    machine = platform.machine()
    if system == "Windows":
        return CheckResult(name="Operating system", status=CheckStatus.WARN, message=f"Windows ({machine})", fix_hint="WSL or Git Bash is recommended for best compatibility.\nSee docs/environment-setup.md for Windows instructions.")
    return CheckResult(name="Operating system", status=CheckStatus.PASS, message=f"{system} {platform.release()} ({machine})")


STATUS_ICONS = {CheckStatus.PASS: "\033[32m✓\033[0m", CheckStatus.WARN: "\033[33m!\033[0m", CheckStatus.FAIL: "\033[31m✗\033[0m", CheckStatus.SKIP: "\033[90m-\033[0m"}
STATUS_ICONS_PLAIN = {CheckStatus.PASS: "[OK]", CheckStatus.WARN: "[!!]", CheckStatus.FAIL: "[FAIL]", CheckStatus.SKIP: "[--]"}


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def format_report(report: DoctorReport) -> str:
    icons = STATUS_ICONS if supports_color() else STATUS_ICONS_PLAIN
    lines = ["", "🐝 Hive Environment Check", "=" * 50, ""]
    for result in report.results:
        icon = icons[result.status]
        lines.append(f"  {icon}  {result.name}: {result.message}")
        if result.details:
            lines.append(f"      ℹ {result.details}")
        if result.fix_hint and result.status in (CheckStatus.FAIL, CheckStatus.WARN):
            for hint_line in result.fix_hint.split("\n"):
                lines.append(f"      → {hint_line}")
        lines.append("")
    lines.append("-" * 50)
    summary_parts = []
    if report.passed > 0:
        summary_parts.append(f"{report.passed} passed")
    if report.warnings > 0:
        summary_parts.append(f"{report.warnings} warning(s)")
    if report.failures > 0:
        summary_parts.append(f"{report.failures} issue(s)")
    lines.append(f"  {', '.join(summary_parts)}")
    if report.is_healthy:
        lines.extend(["", "  Your Hive environment looks good! 🎉"])
    else:
        lines.extend(["", "  Fix the issues above, then re-run: hive doctor"])
    lines.append("")
    return "\n".join(lines)


def register_doctor_command(subparsers) -> None:
    doctor_parser = subparsers.add_parser("doctor", help="Check your Hive development environment for issues")
    doctor_parser.set_defaults(func=_run_doctor_cmd)


def _run_doctor_cmd(args) -> int:
    report = run_doctor()
    print(format_report(report))
    return 0 if report.is_healthy else 1


def run_doctor() -> DoctorReport:
    report = DoctorReport()
    checks = [check_os_compatibility, check_python_version, check_uv_installed, check_git_repo, check_core_venv, check_tools_venv, check_api_keys, check_mcp_config, check_global_config, check_disk_space]
    for check_fn in checks:
        try:
            result = check_fn()
            report.results.append(result)
        except Exception as e:
            report.results.append(CheckResult(name=check_fn.__name__, status=CheckStatus.SKIP, message=f"Check failed unexpectedly: {e}"))
    return report
