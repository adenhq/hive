"""Domain allowlist policy for network tool calls.

This policy evaluates network-related tool calls and checks
whether the target domain is allowed, providing defense-in-depth
against unintended external communications.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from framework.policies.base import BasePolicy
from framework.policies.decisions import PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType


class AllowlistMode(Enum):
    """Operating modes for the domain allowlist."""

    PERMISSIVE = "permissive"
    """Log unknown domains but allow (SUGGEST)."""

    BALANCED = "balanced"
    """Require confirmation for unknown domains (REQUIRE_CONFIRM)."""

    STRICT = "strict"
    """Block unknown domains entirely (BLOCK)."""


# Default patterns for network-related tools
DEFAULT_NETWORK_TOOL_PATTERNS = [
    r".*http.*",
    r".*fetch.*",
    r".*request.*",
    r".*api.*call.*",
    r".*url.*",
    r".*web.*",
    r".*download.*",
    r".*upload.*",
    r".*curl.*",
    r".*webhook.*",
]

# Default allowed domains (common safe destinations)
DEFAULT_ALLOWED_DOMAINS = [
    # Localhost
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    # Common APIs that are generally safe
    "api.openai.com",
    "api.anthropic.com",
    "api.github.com",
    "raw.githubusercontent.com",
]

# Default blocked domains (known risky destinations)
DEFAULT_BLOCKED_DOMAINS = [
    # Pastebin-like services (potential data exfil)
    "pastebin.com",
    "hastebin.com",
    "ghostbin.com",
    # File sharing (potential data exfil)
    "transfer.sh",
    "file.io",
    # Request catchers (potential data exfil)
    "requestbin.com",
    "webhook.site",
    "hookbin.com",
]


@dataclass
class DomainAllowlistPolicy(BasePolicy):
    """Policy that controls which domains agents can communicate with.

    This policy evaluates network-related tool calls and checks the
    target URL/domain against allowlists and blocklists.

    Operating modes:
    - permissive: Log unknown domains but allow (SUGGEST)
    - balanced: Require confirmation for unknown domains (REQUIRE_CONFIRM)
    - strict: Block unknown domains entirely (BLOCK)

    Attributes:
        mode: Operating mode (permissive, balanced, strict)
        allowed_domains: Domains that are always allowed
        blocked_domains: Domains that are always blocked
        network_tool_patterns: Regex patterns to identify network tools
        check_subdomains: Whether to check parent domains

    Example:
        policy = DomainAllowlistPolicy(
            mode=AllowlistMode.BALANCED,
            allowed_domains=["api.mycompany.com", "*.internal.net"],
        )
        engine.register_policy(policy)
    """

    mode: AllowlistMode = AllowlistMode.PERMISSIVE
    allowed_domains: list[str] = field(
        default_factory=lambda: DEFAULT_ALLOWED_DOMAINS.copy()
    )
    blocked_domains: list[str] = field(
        default_factory=lambda: DEFAULT_BLOCKED_DOMAINS.copy()
    )
    network_tool_patterns: list[str] = field(
        default_factory=lambda: DEFAULT_NETWORK_TOOL_PATTERNS.copy()
    )
    check_subdomains: bool = True

    # Policy metadata
    _id: str = "domain-allowlist"
    _name: str = "Domain Allowlist"
    _description: str = (
        "Controls which external domains agents can communicate with, "
        "providing defense against unintended data exfiltration."
    )

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def event_types(self) -> list[PolicyEventType]:
        return [PolicyEventType.TOOL_CALL]

    def _is_network_tool(self, tool_name: str) -> bool:
        """Check if a tool is network-related."""
        tool_lower = tool_name.lower()
        for pattern in self.network_tool_patterns:
            if re.match(pattern, tool_lower):
                return True
        return False

    def _extract_domain(self, payload: dict) -> Optional[str]:
        """Extract domain from tool call payload."""
        # Check common parameter names for URLs
        url_params = ["url", "endpoint", "uri", "href", "target", "destination"]

        args = payload.get("args", {})

        for param in url_params:
            if param in args:
                url = args[param]
                if isinstance(url, str):
                    try:
                        parsed = urlparse(url)
                        if parsed.netloc:
                            # Remove port if present
                            return parsed.netloc.split(":")[0].lower()
                    except Exception:
                        pass

        # Check if domain is passed directly
        if "domain" in args:
            return str(args["domain"]).lower()
        if "host" in args:
            return str(args["host"]).lower()

        return None

    def _matches_domain(self, domain: str, pattern: str) -> bool:
        """Check if a domain matches a pattern (supports wildcards)."""
        pattern = pattern.lower()
        domain = domain.lower()

        # Exact match
        if domain == pattern:
            return True

        # Wildcard match (*.example.com matches sub.example.com)
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if domain.endswith(suffix) or domain == suffix[1:]:
                return True

        # Subdomain check
        if self.check_subdomains:
            if domain.endswith("." + pattern):
                return True

        return False

    def _is_allowed(self, domain: str) -> bool:
        """Check if domain is in the allowlist."""
        for allowed in self.allowed_domains:
            if self._matches_domain(domain, allowed):
                return True
        return False

    def _is_blocked(self, domain: str) -> bool:
        """Check if domain is in the blocklist."""
        for blocked in self.blocked_domains:
            if self._matches_domain(domain, blocked):
                return True
        return False

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate a tool call for domain restrictions.

        Args:
            event: The TOOL_CALL event to evaluate

        Returns:
            PolicyDecision based on domain analysis
        """
        tool_name = event.payload.get("tool_name", "")

        # Skip non-network tools
        if not self._is_network_tool(tool_name):
            return PolicyDecision.allow(
                policy_id=self.id,
                reason=f"Tool '{tool_name}' is not a network tool",
            )

        # Extract domain from payload
        domain = self._extract_domain(event.payload)

        if not domain:
            # Can't determine domain - decide based on mode
            if self.mode == AllowlistMode.STRICT:
                return PolicyDecision.require_confirm(
                    policy_id=self.id,
                    reason=f"Cannot determine target domain for network tool '{tool_name}'",
                    severity=Severity.MEDIUM,
                    tags=["network", "unknown-domain"],
                    metadata={"tool_name": tool_name},
                )
            return PolicyDecision.allow(
                policy_id=self.id,
                reason=f"Network tool '{tool_name}' - domain not specified in args",
                metadata={"tool_name": tool_name},
            )

        # Check blocklist first (always enforced)
        if self._is_blocked(domain):
            return PolicyDecision.block(
                policy_id=self.id,
                reason=f"Domain '{domain}' is blocked (potential data exfiltration risk)",
                severity=Severity.CRITICAL,
                tags=["network", "blocked-domain", "security"],
                metadata={"tool_name": tool_name, "domain": domain},
            )

        # Check allowlist
        if self._is_allowed(domain):
            return PolicyDecision.allow(
                policy_id=self.id,
                reason=f"Domain '{domain}' is in the allowlist",
                metadata={"tool_name": tool_name, "domain": domain},
            )

        # Unknown domain - decide based on mode
        if self.mode == AllowlistMode.PERMISSIVE:
            return PolicyDecision.suggest(
                policy_id=self.id,
                reason=f"Domain '{domain}' is not in allowlist. Consider adding if trusted.",
                severity=Severity.LOW,
                tags=["network", "unknown-domain"],
                metadata={"tool_name": tool_name, "domain": domain},
            )
        elif self.mode == AllowlistMode.BALANCED:
            return PolicyDecision.require_confirm(
                policy_id=self.id,
                reason=f"Domain '{domain}' is not in allowlist. Confirm to proceed.",
                severity=Severity.MEDIUM,
                tags=["network", "unknown-domain", "requires-confirmation"],
                metadata={"tool_name": tool_name, "domain": domain},
            )
        else:  # STRICT
            return PolicyDecision.block(
                policy_id=self.id,
                reason=f"Domain '{domain}' is not in allowlist (strict mode)",
                severity=Severity.HIGH,
                tags=["network", "blocked-domain"],
                metadata={"tool_name": tool_name, "domain": domain},
            )

    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the allowlist."""
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)

    def add_blocked_domain(self, domain: str) -> None:
        """Add a domain to the blocklist."""
        if domain not in self.blocked_domains:
            self.blocked_domains.append(domain)

    def remove_allowed_domain(self, domain: str) -> None:
        """Remove a domain from the allowlist."""
        if domain in self.allowed_domains:
            self.allowed_domains.remove(domain)

    def remove_blocked_domain(self, domain: str) -> None:
        """Remove a domain from the blocklist."""
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
