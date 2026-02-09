#!/usr/bin/env python3
"""Merge Claude Code settings from an example template into a user's local settings.

Ensures every contributor has the project-required MCP tool approvals while
preserving any personal entries they have already added.

Usage:
    python scripts/merge_claude_settings.py --example <path> --target <path>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def merge_settings(example_path: Path, target_path: Path) -> dict:
    """Merge example settings into the target settings file.

    Args:
        example_path: Path to the ``.example`` template (must exist).
        target_path: Path to the user's ``settings.local.json``.  Created from
            the example when absent.

    Returns:
        A dict with ``"action"`` (``"created"`` or ``"merged"``),
        ``"new_entries"`` (list of permission strings that were added), and
        ``"target"`` (the final resolved path).

    Raises:
        FileNotFoundError: If *example_path* does not exist.
        json.JSONDecodeError: If either file contains invalid JSON.
    """
    if not example_path.exists():
        raise FileNotFoundError(f"Example file not found: {example_path}")

    example_text = example_path.read_text(encoding="utf-8")
    example = json.loads(example_text)

    if not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example_path, target_path)
        return {
            "action": "created",
            "new_entries": example.get("permissions", {}).get("allow", []),
            "target": str(target_path),
        }

    target_text = target_path.read_text(encoding="utf-8")
    target = json.loads(target_text)

    # --- permissions.allow merge ---
    if "permissions" not in target:
        target["permissions"] = {}
    if "allow" not in target["permissions"]:
        target["permissions"]["allow"] = []

    example_allow: list[str] = example.get("permissions", {}).get("allow", [])
    target_allow: list[str] = target["permissions"]["allow"]

    existing_set = set(target_allow)
    new_entries = [e for e in example_allow if e not in existing_set]

    # Example entries first, then user-only entries (preserving relative order).
    example_set = set(example_allow)
    user_only = [e for e in target_allow if e not in example_set]
    target["permissions"]["allow"] = example_allow + user_only

    # --- top-level keys: fill missing, never overwrite ---
    for key, value in example.items():
        if key == "permissions":
            continue
        if key not in target:
            target[key] = value

    target_path.write_text(json.dumps(target, indent=2) + "\n", encoding="utf-8")

    return {
        "action": "merged",
        "new_entries": new_entries,
        "target": str(target_path),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Merge Claude Code settings from example into local target."
    )
    parser.add_argument(
        "--example",
        required=True,
        type=Path,
        help="Path to the .example settings template.",
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Path to the user's settings.local.json.",
    )
    args = parser.parse_args(argv)

    try:
        result = merge_settings(args.example, args.target)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result["action"] == "created":
        print(f"Created {result['target']} from example template.")
    else:
        n = len(result["new_entries"])
        if n:
            print(f"Merged {n} new permission(s) into {result['target']}.")
            for entry in result["new_entries"]:
                print(f"  + {entry}")
        else:
            print(f"{result['target']} is already up to date.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
