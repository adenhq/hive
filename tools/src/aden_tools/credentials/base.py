"""
Base classes for credential management.

Contains the core infrastructure: CredentialSpec, CredentialManager, and CredentialError.
Credential specs are defined in separate category files (llm.py, search.py, etc.).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Set

from dotenv import dotenv_values

if TYPE_CHECKING:
    pass


@dataclass
class CredentialSpec:
    """Specification for a single credential."""

    env_var: str
    """Environment variable name (e.g., 'BRAVE_SEARCH_API_KEY')"""

    tools: List[str] = field(default_factory=list)
    """Tool names that require this credential (e.g., ['web_search'])"""

    node_types: List[str] = field(default_factory=list)
    """Node types that require this credential (e.g., ['llm_generate', 'llm_tool_use'])"""

    required: bool = True
    """Whether this credential is required (vs optional)"""

    startup_required: bool = False
    """Whether this credential must be present at server startup (Tier 1)"""

    help_url: str = ""
    """URL where user can obtain this credential"""

    description: str = ""
    """Human-readable description of what this credential is for"""


class CredentialError(Exception):
    """Raised when required credentials are missing."""
    pass


class CredentialManager:
    """
    Centralized credential management with agent-aware validation.

    Key features:
    - validate_for_tools(): Validates only credentials needed by specific tools
    - get(): Retrieves credential value by logical name
    - for_testing(): Factory for creating test instances with mock values
    """

    _specs: Dict[str, CredentialSpec]
    _overrides: Dict[str, str]
    _tool_to_cred: Dict[str, str]
    _node_type_to_cred: Dict[str, str]
    _dotenv_path: Optional[Path]

    def __init__(
        self,
        specs: Optional[Dict[str, CredentialSpec]] = None,
        _overrides: Optional[Dict[str, str]] = None,
        dotenv_path: Optional[Path] = None,
    ):
        """
        Initialize the credential manager.

        Args:
            specs: Credential specifications (defaults to CREDENTIAL_SPECS)
            _overrides: Internal - used by for_testing() to inject test values
            dotenv_path: Optional path to .env file (defaults to cwd/.env)
        """
        if specs is None:
            from . import CREDENTIAL_SPECS

            specs = CREDENTIAL_SPECS

        self._specs = specs
        self._overrides = _overrides or {}
        self._dotenv_path = dotenv_path

        # Build reverse mapping: tool_name -> credential_name
        self._tool_to_cred = {}
        for cred_name, spec in self._specs.items():
            for tool_name in spec.tools:
                self._tool_to_cred[tool_name] = cred_name

        # Build reverse mapping: node_type -> credential_name
        self._node_type_to_cred = {}
        for cred_name, spec in self._specs.items():
            for node_type in spec.node_types:
                self._node_type_to_cred[node_type] = cred_name

    @classmethod
    def for_testing(
        cls,
        overrides: Dict[str, str],
        specs: Optional[Dict[str, CredentialSpec]] = None,
        dotenv_path: Optional[Path] = None,
    ) -> "CredentialManager":
        """Create a CredentialManager with test values."""
        return cls(specs=specs, _overrides=overrides, dotenv_path=dotenv_path)

    def _get_raw(self, name: str) -> Optional[str]:
        """
        Get credential from overrides, os.environ, or .env file.

        Returns None if the credential is undefined or not set.

        Priority order:
        1. Test overrides
        2. os.environ
        3. .env file (hot-reload)
        """
        if name in self._overrides:
            return self._overrides[name]

        spec = self._specs.get(name)
        if spec is None:
            return None

        env_value = os.environ.get(spec.env_var)
        if env_value:
            return env_value

        return self._read_from_dotenv(spec.env_var)

    def _read_from_dotenv(self, env_var: str) -> Optional[str]:
        """Read a single env var from .env file without mutating os.environ."""
        dotenv_path = self._dotenv_path or Path.cwd() / ".env"
        if not dotenv_path.exists():
            return None

        values = dotenv_values(dotenv_path)
        return values.get(env_var)

    def get(self, name: str) -> Optional[str]:
        """Get a credential value by logical name."""
        if name not in self._specs:
            raise KeyError(
                f"Unknown credential '{name}'. Available: {list(self._specs.keys())}"
            )

        return self._get_raw(name)

    def get_spec(self, name: str) -> CredentialSpec:
        """Get the spec for a credential."""
        if name not in self._specs:
            raise KeyError(f"Unknown credential '{name}'")
        return self._specs[name]

    def is_available(self, name: str) -> bool:
        """Check if a credential is available (set and non-empty)."""
        value = self.get(name)
        return value is not None and value != ""

    def get_credential_for_tool(self, tool_name: str) -> Optional[str]:
        """
        Get the credential name required by a tool.

        Note:
            Returns the logical credential name (e.g. "brave_search"),
            not the environment variable name.
        """
        return self._tool_to_cred.get(tool_name)

    def get_missing_for_tools(
        self, tool_names: List[str]
    ) -> List[Tuple[str, CredentialSpec]]:
        """Get list of missing credentials for the given tools."""
        missing: List[Tuple[str, CredentialSpec]] = []
        checked: Set[str] = set()

        for tool_name in tool_names:
            cred_name = self._tool_to_cred.get(tool_name)
            if cred_name is None or cred_name in checked:
                continue

            checked.add(cred_name)
            spec = self._specs[cred_name]

            if spec.required and not self.is_available(cred_name):
                missing.append((cred_name, spec))

        return missing

    def validate_for_tools(self, tool_names: List[str]) -> None:
        """Validate that all credentials required by the given tools are available."""
        missing = self.get_missing_for_tools(tool_names)

        if missing:
            raise CredentialError(self._format_missing_error(missing, tool_names))

    def _format_missing_error(
        self,
        missing: List[Tuple[str, CredentialSpec]],
        tool_names: List[str],
    ) -> str:
        """Format a clear, actionable error message for missing credentials."""
        lines = ["Cannot run agent: Missing credentials"]
        lines.append("The following tools require credentials that are not set:\n")

        for cred_name, spec in missing:
            affected_tools = [t for t in tool_names if t in spec.tools]
            tools_str = ", ".join(affected_tools)

            lines.append(f"  {tools_str} requires {spec.env_var}")
            if spec.description:
                lines.append(f"    {spec.description}")
            if spec.help_url:
                lines.append(f"    Get an API key at: {spec.help_url}")
            lines.append(f"    Set via: export {spec.env_var}=your_key\n")

        lines.append("Set these environment variables and re-run the agent.")
        return "\n".join(lines)

    def validate_startup(self) -> None:
        """Validate that all startup-required credentials are present."""
        missing: List[Tuple[str, CredentialSpec]] = []

        for cred_name, spec in self._specs.items():
            if spec.startup_required and not self.is_available(cred_name):
                missing.append((cred_name, spec))

        if missing:
            raise CredentialError(self._format_startup_error(missing))

    def _format_startup_error(
        self,
        missing: List[Tuple[str, CredentialSpec]],
    ) -> str:
        """Format a clear, actionable error message for missing startup credentials."""
        lines = ["Server startup failed: Missing required credentials"]

        for _, spec in missing:
            lines.append(f"  {spec.env_var}")
            if spec.description:
                lines.append(f"    {spec.description}")
            if spec.help_url:
                lines.append(f"    Get an API key at: {spec.help_url}")
            lines.append(f"    Set via: export {spec.env_var}=your_key\n")

        lines.append("Set these environment variables and restart the server.")
        return "\n".join(lines)
