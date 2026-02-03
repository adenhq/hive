from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Cmd:
    args: list[str]
    cwd: Path


def _repo_root() -> Path:
    # scripts/check.py -> scripts/ -> repo root
    return Path(__file__).resolve().parent.parent


def _run(cmd: Cmd) -> None:
    subprocess.run(cmd.args, cwd=str(cmd.cwd), check=True)


def _python_exe() -> str:
    return sys.executable


def _env() -> None:
    # Ensure predictable output in CI/dev shells.
    os.environ.setdefault("PYTHONUTF8", "1")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cross-platform checks for this repo (replacement for `make check` + `make test`). "
            "Runs ruff lint + format checks for core/ and tools/, then core tests."
        )
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix lint issues and apply formatting (equivalent to `make lint` + `make format`).",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest (only run lint/format checks).",
    )
    args = parser.parse_args()

    _env()
    root = _repo_root()

    ruff_check = ["-m", "ruff", "check"]
    ruff_format = ["-m", "ruff", "format"]

    check_flags = ["--fix"] if args.fix else []
    format_flags = [] if args.fix else ["--check"]

    cmds: list[Cmd] = [
        Cmd(args=[_python_exe(), *ruff_check, *check_flags, "."], cwd=root / "core"),
        Cmd(args=[_python_exe(), *ruff_check, *check_flags, "."], cwd=root / "tools"),
        Cmd(args=[_python_exe(), *ruff_format, *format_flags, "."], cwd=root / "core"),
        Cmd(args=[_python_exe(), *ruff_format, *format_flags, "."], cwd=root / "tools"),
    ]

    if not args.skip_tests:
        cmds.append(Cmd(args=[_python_exe(), "-m", "pytest", "tests/", "-v"], cwd=root / "core"))

    for cmd in cmds:
        _run(cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


