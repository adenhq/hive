"""Agent Template Registry with Intent Matching.

This module provides a registry of reusable agent patterns that the compiler
can target. It uses semantic matching to map natural language intents to
existing Hive agent templates, enabling code reuse and standardization.

Example:
    >>> from core.compiler.registry import AgentTemplateRegistry, AgentTemplate
    >>> from core.compiler.transformer import AgentType
    >>>
    >>> registry = AgentTemplateRegistry()
    >>>
    >>> # Register a template
    >>> registry.register(AgentTemplate(
    ...     name="slack_notifier",
    ...     agent_type=AgentType.TOOL_USE,
    ...     description="Sends notifications to Slack channels",
    ...     required_tools=["send_slack_message"],
    ...     keywords=["slack", "notify", "message", "alert"]
    ... ))
    >>>
    >>> # Match intent to template
    >>> matches = registry.match("Send a Slack notification to the team")
    >>> print(matches[0].template.name)
    slack_notifier
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from framework.graph.plan import ActionType as AgentType

from core.compiler.transformer import AgentTemplate


@dataclass
class TemplateMatch:
    """Result of matching an intent to a template.

    Attributes:
        template: The matched AgentTemplate.
        score: Match confidence (0.0 to 1.0).
        matched_keywords: Keywords that triggered the match.
        explanation: Human-readable explanation of why this matched.
    """

    template: AgentTemplate
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class RegisteredTemplate:
    """A template with its matching configuration.

    Attributes:
        template: The agent template.
        keywords: Keywords for matching (e.g., ["email", "send", "mail"]).
        patterns: Regex patterns for advanced matching.
        weight: Importance weight (higher = preferred).
    """

    template: AgentTemplate
    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    weight: float = 1.0


class AgentTemplateRegistry:
    """Registry of agent templates with intent matching capabilities.

    This registry enables the compiler to map natural language intents
to reusable agent patterns, promoting standardization and code reuse.

    Example:
        >>> registry = AgentTemplateRegistry()
        >>>
        >>> # Register templates
        >>> registry.register_template(
        ...     name="email_sender",
        ...     agent_type=AgentType.TOOL_USE,
        ...     tool_name="send_email",
        ...     description="Sends emails to recipients",
        ...     keywords=["email", "send", "mail", "notify"],
        ...     required_tools=["send_email"]
        ... )
        >>>
        >>> # Match intent
        >>> matches = registry.match("Email the report to the team")
        >>> if matches:
        ...     best = matches[0]
        ...     print(f"Use template: {best.template.agent_type}")
    """

    def __init__(self):
        """Initialize empty registry."""
        self._templates: dict[str, RegisteredTemplate] = {}
        self._matchers: list[Callable[[str, RegisteredTemplate], TemplateMatch | None]] = []

        # Register default matchers
        self._register_default_matchers()

    def _register_default_matchers(self) -> None:
        """Register the built-in matching algorithms."""
        self._matchers.extend([
            self._keyword_matcher,
            self._pattern_matcher,
        ])

    def register(
        self,
        template: AgentTemplate,
        keywords: list[str] | None = None,
        patterns: list[str] | None = None,
        weight: float = 1.0,
    ) -> None:
        """Register an agent template with matching configuration.

        Args:
            template: The agent template to register.
            keywords: Keywords for matching this template.
            patterns: Regex patterns for advanced matching.
            weight: Importance weight (higher = preferred).
        """
        registered = RegisteredTemplate(
            template=template,
            keywords=[k.lower() for k in (keywords or [])],
            patterns=patterns or [],
            weight=weight,
        )
        self._templates[template.agent_type] = registered

    def register_template(
        self,
        name: str,
        agent_type: AgentType,
        description: str,
        tool_name: str | None = None,
        system_prompt: str | None = None,
        keywords: list[str] | None = None,
        patterns: list[str] | None = None,
        required_tools: list[str] | None = None,
        weight: float = 1.0,
    ) -> None:
        """Convenience method to create and register a template.

        Args:
            name: Unique identifier for this template.
            agent_type: The Hive ActionType.
            description: Human-readable description.
            tool_name: Tool name for TOOL_USE agents.
            system_prompt: System prompt for LLM_CALL agents.
            keywords: Keywords for matching.
            patterns: Regex patterns for matching.
            required_tools: Tools required by this agent.
            weight: Importance weight.
        """
        template = AgentTemplate(
            agent_type=name,
            action_type=agent_type,
            tool_name=tool_name,
            system_prompt=system_prompt,
            description=description,
            required_tools=required_tools or [],
        )
        self.register(template, keywords, patterns, weight)

    def match(self, intent: str, top_k: int = 3) -> list[TemplateMatch]:
        """Find templates matching the given intent.

        Args:
            intent: Natural language intent to match.
            top_k: Maximum number of matches to return.

        Returns:
            List of TemplateMatch objects, sorted by score (best first).
        """
        intent_lower = intent.lower()
        matches: list[TemplateMatch] = []

        for registered in self._templates.values():
            for matcher in self._matchers:
                match = matcher(intent_lower, registered)
                if match:
                    # Apply weight
                    match.score *= registered.weight
                    matches.append(match)
                    break  # Only count each template once

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches[:top_k]

    def get_best_match(self, intent: str) -> TemplateMatch | None:
        """Get the single best matching template.

        Args:
            intent: Natural language intent to match.

        Returns:
            Best TemplateMatch or None if no match.
        """
        matches = self.match(intent, top_k=1)
        return matches[0] if matches else None

    def _keyword_matcher(
        self, intent: str, registered: RegisteredTemplate
    ) -> TemplateMatch | None:
        """Match based on keyword presence."""
        if not registered.keywords:
            return None

        matched_keywords = []
        for keyword in registered.keywords:
            # Match whole words or substrings for flexibility
            if keyword in intent:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return None

        # Score based on fraction of keywords matched
        score = len(matched_keywords) / len(registered.keywords)

        # Boost score for multiple matches
        if len(matched_keywords) > 1:
            score = min(1.0, score * 1.2)

        return TemplateMatch(
            template=registered.template,
            score=score,
            matched_keywords=matched_keywords,
            explanation=f"Matched keywords: {', '.join(matched_keywords)}",
        )

    def _pattern_matcher(
        self, intent: str, registered: RegisteredTemplate
    ) -> TemplateMatch | None:
        """Match based on regex patterns."""
        if not registered.patterns:
            return None

        for pattern in registered.patterns:
            try:
                if re.search(pattern, intent, re.IGNORECASE):
                    return TemplateMatch(
                        template=registered.template,
                        score=0.9,  # High score for pattern match
                        matched_keywords=[],
                        explanation=f"Matched pattern: {pattern}",
                    )
            except re.error:
                continue

        return None

    def list_templates(self) -> list[str]:
        """Get list of registered template names."""
        return sorted(self._templates.keys())

    def get_template(self, name: str) -> AgentTemplate | None:
        """Get a template by name."""
        registered = self._templates.get(name)
        return registered.template if registered else None

    def unregister(self, name: str) -> bool:
        """Remove a template from the registry.

        Args:
            name: Template name to remove.

        Returns:
            True if removed, False if not found.
        """
        if name in self._templates:
            del self._templates[name]
            return True
        return False

    def clear(self) -> None:
        """Remove all templates."""
        self._templates.clear()


class DefaultTemplateRegistry(AgentTemplateRegistry):
    """Registry pre-populated with common agent templates."""

    def __init__(self):
        """Initialize with default templates."""
        super().__init__()
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register commonly used agent templates."""
        # Data operations
        self.register_template(
            name="data_fetcher",
            agent_type=AgentType.TOOL_USE,
            tool_name="http_request",
            description="Fetches data from APIs and web services",
            keywords=[
                "fetch", "get", "retrieve", "download", "pull",
                "data", "api", "web", "scrape", "extract"
            ],
            required_tools=["http_request"],
            weight=1.0,
        )

        self.register_template(
            name="data_transformer",
            agent_type=AgentType.FUNCTION,
            description="Transforms and processes data",
            keywords=[
                "transform", "process", "convert", "format",
                "parse", "clean", "filter", "aggregate"
            ],
            weight=0.9,
        )

        # Communication
        self.register_template(
            name="email_sender",
            agent_type=AgentType.TOOL_USE,
            tool_name="send_email",
            description="Sends emails to recipients",
            keywords=[
                "email", "send", "mail", "notify", "alert",
                "message", "smtp", "outlook", "gmail"
            ],
            patterns=[
                r"\bemail\s+(?:to|the)\b",
                r"\bsend\s+(?:an?\s+)?email\b",
            ],
            required_tools=["send_email"],
            weight=1.0,
        )

        self.register_template(
            name="slack_notifier",
            agent_type=AgentType.TOOL_USE,
            tool_name="send_slack_message",
            description="Sends notifications to Slack channels",
            keywords=[
                "slack", "notify", "notification", "message",
                "channel", "team", "alert", "post"
            ],
            patterns=[
                r"\bslack\b",
                r"\bpost\s+(?:to\s+)?slack\b",
            ],
            required_tools=["send_slack_message"],
            weight=1.0,
        )

        # Analysis and reporting
        self.register_template(
            name="report_generator",
            agent_type=AgentType.LLM_CALL,
            description="Generates structured reports from data",
            keywords=[
                "report", "generate", "create", "compile",
                "summary", "analysis", "insights", "metrics"
            ],
            weight=1.0,
        )

        self.register_template(
            name="data_analyzer",
            agent_type=AgentType.LLM_CALL,
            description="Analyzes data and provides insights",
            keywords=[
                "analyze", "analysis", "insight", "trend",
                "pattern", "correlation", "statistics", "metrics"
            ],
            weight=0.9,
        )

        # Storage operations
        self.register_template(
            name="database_writer",
            agent_type=AgentType.TOOL_USE,
            tool_name="execute_sql",
            description="Writes data to databases",
            keywords=[
                "database", "db", "sql", "store", "save",
                "insert", "write", "update", "postgres", "mysql"
            ],
            patterns=[
                r"\bsave\s+(?:to\s+)?(?:database|db)\b",
                r"\binsert\s+(?:into\s+)?",
            ],
            required_tools=["execute_sql"],
            weight=1.0,
        )

        self.register_template(
            name="file_writer",
            agent_type=AgentType.TOOL_USE,
            tool_name="write_file",
            description="Writes data to files",
            keywords=[
                "file", "write", "save", "export", "output",
                "csv", "json", "txt", "document", "spreadsheet"
            ],
            patterns=[
                r"\bsave\s+(?:to\s+)?file\b",
                r"\bexport\s+(?:to\s+)?",
            ],
            required_tools=["write_file"],
            weight=0.9,
        )

        # AI/LLM operations
        self.register_template(
            name="text_generator",
            agent_type=AgentType.LLM_CALL,
            description="Generates text content using LLM",
            keywords=[
                "generate", "create", "write", "draft", "compose",
                "text", "content", "article", "blog", "post"
            ],
            weight=0.8,
        )

        self.register_template(
            name="summarizer",
            agent_type=AgentType.LLM_CALL,
            description="Summarizes long content",
            keywords=[
                "summarize", "summary", "condense", "brief",
                "overview", "tl;dr", "digest", "abstract"
            ],
            weight=0.9,
        )

        # Search operations
        self.register_template(
            name="web_searcher",
            agent_type=AgentType.TOOL_USE,
            tool_name="web_search",
            description="Searches the web for information",
            keywords=[
                "search", "find", "lookup", "google", "bing",
                "web", "internet", "query", "research"
            ],
            required_tools=["web_search"],
            weight=1.0,
        )


def create_compiler_registry() -> DefaultTemplateRegistry:
    """Factory function to create a pre-configured registry for the compiler.

    Returns:
        DefaultTemplateRegistry with common agent templates.
    """
    return DefaultTemplateRegistry()
