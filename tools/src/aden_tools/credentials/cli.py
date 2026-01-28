from __future__ import annotations

import argparse

from .base import CredentialError, CredentialManager


def _split_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aden-tools-credentials",
        description="Check and validate Aden Tools credentials.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="Check for missing credentials.")
    check.add_argument(
        "--node-types",
        default="",
        help="Comma-separated node types (e.g. llm_generate,llm_tool_use).",
    )
    check.add_argument(
        "--startup",
        action="store_true",
        help="Validate startup-required credentials.",
    )

    args = parser.parse_args(argv)
    creds = CredentialManager()

    if args.cmd != "check":
        return 2

    if args.startup:
        try:
            creds.validate_startup()
            print("✓ All startup-required credentials are present.")
            return 0
        except CredentialError as e:
            print(str(e))
            return 1

    node_types = _split_csv(args.node_types)
    if not node_types:
        parser.error("Provide --startup or --node-types")

    missing = creds.get_missing_for_node_types(node_types)

    if not missing:
        print("✓ All required credentials are present.")
        return 0

    print("✗ Missing required credentials:\n")
    for _cred_name, spec in missing:
        print(f"- {spec.env_var}: {spec.description}")
        if spec.help_url:
            print(f"  Help: {spec.help_url}")
    return 1
