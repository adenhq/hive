from __future__ import annotations

import sys
from pathlib import Path

from framework.cli import main as framework_main


def main() -> None:
    agent_dir = Path(__file__).resolve().parent
    args = sys.argv[1:]

    if not args:
        print("Usage: python -m support_ticket_agent <validate|info|run|test> [args]")
        raise SystemExit(2)

    cmd = args[0]
    if cmd in {"validate", "info", "run", "test"}:
        if len(args) == 1 or args[1].startswith("-"):
            args = [cmd, str(agent_dir), *args[1:]]

    sys.argv = ["hive", *args]
    framework_main()


if __name__ == "__main__":
    main()
