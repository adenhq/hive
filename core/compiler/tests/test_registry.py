"""Tests for the Agent Template Registry with Intent Matching.

These tests validate template registration, intent matching algorithms,
and the default template registry.
"""

from __future__ import annotations

import pytest

from core.compiler.registry import (
    AgentTemplateRegistry,
    AgentType,
    DefaultTemplateRegistry,
    RegisteredTemplate,
    TemplateMatch,
    create_compiler_registry,
)
from core.compiler.transformer import AgentTemplate


class TestAgentTemplateRegistry:
    """Tests for the base AgentTemplateRegistry."""

    def test_register_template(self):
        """Should register a template successfully."""
        registry = AgentTemplateRegistry()
        template = AgentTemplate(
            agent_type="test_agent",
            action_type=AgentType.LLM_CALL,
            description="Test agent",
        )

        registry.register(template, keywords=["test", "example"])

        assert "test_agent" in registry.list_templates()

    def test_register_template_with_keywords(self):
        """Should register with matching keywords."""
        registry = AgentTemplateRegistry()

        registry.register_template(
            name="email_sender",
            agent_type=AgentType.TOOL_USE,
            tool_name="send_email",
            description="Sends emails",
            keywords=["email", "send", "mail"],
        )

        matches = registry.match("Send an email to the team")
        assert len(matches) > 0
        assert matches[0].template.agent_type == "email_sender"

    def test_match_multiple_keywords(self):
        """Should match better with multiple keywords."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="data_fetcher",
            agent_type=AgentType.TOOL_USE,
            tool_name="http_request",
            description="Fetches data",
            keywords=["fetch", "data", "api"],
        )

        # Match with multiple keywords
        matches = registry.match("Fetch data from the API")
        assert len(matches) == 1
        assert matches[0].score > 0.5  # Multiple keyword match boosts score
        assert set(matches[0].matched_keywords) == {"fetch", "data", "api"}

    def test_match_no_keywords(self):
        """Should return empty list when no keywords match."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="specific_agent",
            agent_type=AgentType.LLM_CALL,
            description="Very specific",
            keywords=["quantum", "physics"],
        )

        matches = registry.match("Send a simple email")
        assert len(matches) == 0

    def test_match_top_k_limit(self):
        """Should respect top_k parameter."""
        registry = AgentTemplateRegistry()

        # Register multiple templates
        for i in range(5):
            registry.register_template(
                name=f"agent_{i}",
                agent_type=AgentType.LLM_CALL,
                description=f"Agent {i}",
                keywords=["common"],  # All match same keyword
            )

        matches = registry.match("common task", top_k=3)
        assert len(matches) <= 3

    def test_get_best_match(self):
        """Should return single best match."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="high_match",
            agent_type=AgentType.LLM_CALL,
            description="High match",
            keywords=["email", "send", "mail", "notify"],
            weight=1.0,
        )
        registry.register_template(
            name="low_match",
            agent_type=AgentType.LLM_CALL,
            description="Low match",
            keywords=["email"],
            weight=0.5,
        )

        best = registry.get_best_match("Send email notification")
        assert best is not None
        assert best.template.agent_type == "high_match"

    def test_get_best_match_no_match(self):
        """Should return None when no match found."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="specific",
            agent_type=AgentType.LLM_CALL,
            description="Specific",
            keywords=["xyz123"],
        )

        best = registry.get_best_match("Completely unrelated intent")
        assert best is None

    def test_get_template_by_name(self):
        """Should retrieve template by name."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="retrievable",
            agent_type=AgentType.TOOL_USE,
            tool_name="test_tool",
            description="Retrievable agent",
        )

        template = registry.get_template("retrievable")
        assert template is not None
        assert template.agent_type == "retrievable"
        assert template.tool_name == "test_tool"

    def test_get_template_not_found(self):
        """Should return None for unknown template."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("nonexistent")
        assert template is None

    def test_unregister_template(self):
        """Should unregister a template."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="removable",
            agent_type=AgentType.LLM_CALL,
            description="Removable",
        )

        result = registry.unregister("removable")

        assert result is True
        assert "removable" not in registry.list_templates()

    def test_unregister_not_found(self):
        """Should return False when unregistering unknown template."""
        registry = AgentTemplateRegistry()

        result = registry.unregister("never_registered")
        assert result is False

    def test_clear_registry(self):
        """Should clear all templates."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="agent1", agent_type=AgentType.LLM_CALL, description="Agent 1"
        )
        registry.register_template(
            name="agent2", agent_type=AgentType.LLM_CALL, description="Agent 2"
        )

        registry.clear()

        assert len(registry.list_templates()) == 0

    def test_list_templates_sorted(self):
        """Should return sorted list of template names."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="zebra", agent_type=AgentType.LLM_CALL, description="Zebra"
        )
        registry.register_template(
            name="alpha", agent_type=AgentType.LLM_CALL, description="Alpha"
        )
        registry.register_template(
            name="beta", agent_type=AgentType.LLM_CALL, description="Beta"
        )

        templates = registry.list_templates()
        assert templates == ["alpha", "beta", "zebra"]


class TestPatternMatching:
    """Tests for regex pattern matching."""

    def test_pattern_match(self):
        """Should match using regex patterns."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="email_sender",
            agent_type=AgentType.TOOL_USE,
            tool_name="send_email",
            description="Sends emails",
            keywords=[],  # No keywords
            patterns=[r"\bsend\s+(?:an?\s+)?email\b"],
        )

        matches = registry.match("Please send an email to the team")
        assert len(matches) == 1
        assert matches[0].score == 0.9  # Pattern match score

    def test_pattern_no_match(self):
        """Should not match when pattern doesn't fit."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="specific_pattern",
            agent_type=AgentType.LLM_CALL,
            description="Specific",
            patterns=[r"^specific:\s+"],
        )

        matches = registry.match("This doesn't start with specific:")
        assert len(matches) == 0

    def test_keyword_over_pattern(self):
        """Keywords should be checked before patterns."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="test_agent",
            agent_type=AgentType.LLM_CALL,
            description="Test",
            keywords=["email"],
            patterns=[r"\bmail\b"],
        )

        # Should match via keyword, not pattern
        matches = registry.match("Email the report")
        assert len(matches) == 1
        assert "email" in matches[0].matched_keywords


class TestTemplateWeights:
    """Tests for template weight/scoring."""

    def test_weight_affects_score(self):
        """Higher weight should increase score."""
        registry = AgentTemplateRegistry()

        registry.register_template(
            name="heavy",
            agent_type=AgentType.LLM_CALL,
            description="Heavy weight",
            keywords=["common"],
            weight=2.0,
        )
        registry.register_template(
            name="light",
            agent_type=AgentType.LLM_CALL,
            description="Light weight",
            keywords=["common"],
            weight=0.5,
        )

        matches = registry.match("common task")
        assert len(matches) == 2
        # Heavy should score higher due to weight
        heavy_match = next(m for m in matches if m.template.agent_type == "heavy")
        light_match = next(m for m in matches if m.template.agent_type == "light")
        assert heavy_match.score > light_match.score


class TestDefaultTemplateRegistry:
    """Tests for the pre-populated DefaultTemplateRegistry."""

    def test_default_registry_has_templates(self):
        """Default registry should have pre-registered templates."""
        registry = DefaultTemplateRegistry()

        templates = registry.list_templates()
        assert len(templates) > 0

    def test_default_registry_has_common_agents(self):
        """Should have common agent types."""
        registry = DefaultTemplateRegistry()

        assert "email_sender" in registry.list_templates()
        assert "data_fetcher" in registry.list_templates()
        assert "slack_notifier" in registry.list_templates()

    def test_email_match(self):
        """Should match email-related intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Email the weekly report to the team")
        assert len(matches) > 0
        assert matches[0].template.agent_type == "email_sender"

    def test_slack_match(self):
        """Should match Slack-related intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Send a Slack notification")
        assert len(matches) > 0
        assert any(
            m.template.agent_type == "slack_notifier" for m in matches
        )

    def test_data_fetch_match(self):
        """Should match data fetching intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Fetch sales data from the API")
        assert len(matches) > 0
        assert any(m.template.agent_type == "data_fetcher" for m in matches)

    def test_report_generation_match(self):
        """Should match report generation intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Generate a quarterly report")
        assert len(matches) > 0
        assert any(
            m.template.agent_type == "report_generator" for m in matches
        )

    def test_analyze_data_match(self):
        """Should match analysis intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Analyze the sales trends")
        assert len(matches) > 0
        assert any(
            m.template.agent_type == "data_analyzer" for m in matches
        )

    def test_web_search_match(self):
        """Should match web search intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Search the web for latest news")
        assert len(matches) > 0
        assert any(
            m.template.agent_type == "web_searcher" for m in matches
        )

    def test_summarize_match(self):
        """Should match summarization intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Summarize this long document")
        assert len(matches) > 0
        assert any(m.template.agent_type == "summarizer" for m in matches)

    def test_database_match(self):
        """Should match database intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("Save the results to the database")
        assert len(matches) > 0
        assert any(
            m.template.agent_type == "database_writer" for m in matches
        )

    def test_multiple_matches_returned(self):
        """Should return multiple relevant matches."""
        registry = DefaultTemplateRegistry()

        # "Generate report" could match multiple templates
        matches = registry.match("Generate and email the report", top_k=3)
        assert len(matches) >= 1

    def test_no_false_positives(self):
        """Should not match unrelated intents."""
        registry = DefaultTemplateRegistry()

        matches = registry.match("xyz123 nonexistent gibberish")
        assert len(matches) == 0


class TestFactoryFunction:
    """Tests for create_compiler_registry factory."""

    def test_factory_creates_default_registry(self):
        """Factory should create configured registry."""
        registry = create_compiler_registry()

        assert isinstance(registry, DefaultTemplateRegistry)
        assert len(registry.list_templates()) > 0

    def test_factory_registry_is_usable(self):
        """Factory registry should work immediately."""
        registry = create_compiler_registry()

        matches = registry.match("Send email to team")
        assert len(matches) > 0


class TestTemplateMatchDataclass:
    """Tests for TemplateMatch dataclass."""

    def test_template_match_creation(self):
        """Should create TemplateMatch correctly."""
        template = AgentTemplate(
            agent_type="test",
            action_type=AgentType.LLM_CALL,
            description="Test",
        )
        match = TemplateMatch(
            template=template,
            score=0.85,
            matched_keywords=["email", "send"],
            explanation="Matched keywords: email, send",
        )

        assert match.template.agent_type == "test"
        assert match.score == 0.85
        assert match.matched_keywords == ["email", "send"]


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_intent(self):
        """Should handle empty intent gracefully."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="test",
            agent_type=AgentType.LLM_CALL,
            description="Test",
            keywords=["test"],
        )

        matches = registry.match("")
        assert len(matches) == 0

    def test_case_insensitive_matching(self):
        """Matching should be case insensitive."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="test",
            agent_type=AgentType.LLM_CALL,
            description="Test",
            keywords=["EMAIL"],  # Uppercase
        )

        matches = registry.match("send an email")  # lowercase
        assert len(matches) == 1

    def test_partial_keyword_match(self):
        """Should match partial keywords."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="emailer",
            agent_type=AgentType.LLM_CALL,
            description="Email",
            keywords=["email"],
        )

        # Should match "emailing" containing "email"
        matches = registry.match("Emailing the team")
        assert len(matches) == 1

    def test_duplicate_registration(self):
        """Should overwrite on duplicate registration."""
        registry = AgentTemplateRegistry()
        registry.register_template(
            name="duplicate",
            agent_type=AgentType.LLM_CALL,
            description="First",
        )
        registry.register_template(
            name="duplicate",
            agent_type=AgentType.TOOL_USE,
            tool_name="test",
            description="Second",
        )

        template = registry.get_template("duplicate")
        assert template is not None
        assert template.action_type == AgentType.TOOL_USE
