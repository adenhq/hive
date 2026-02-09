"""
Tests for Brand-Influencer Matchmaker agent.

This module tests:
- Pydantic model validation
- Scoring logic
- Match tier calculations
- Recommendation generation
- Sales brief formatting
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

# Adjust import path based on test execution context
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "exports"))

from brand_influencer_matchmaker.models import (
    AlignmentScore,
    BrandProfile,
    ConfidenceLevel,
    InfluencerProfile,
    MatchmakerInput,
    MatchmakerOutput,
    MatchResult,
    RecommendationType,
    SalesBrief,
)


class TestBrandProfile:
    """Tests for BrandProfile model."""

    def test_valid_brand_profile(self):
        """Test creating a valid BrandProfile."""
        profile = BrandProfile(
            brand_name="Patagonia",
            website_url="https://www.patagonia.com",
            industry="Outdoor Apparel",
            values=["sustainability", "environmental activism", "quality"],
            tone="authentic",
            target_demographics={
                "age_range": "25-45",
                "interests": ["outdoor activities", "environmental causes"],
            },
        )

        assert profile.brand_name == "Patagonia"
        assert "sustainability" in profile.values
        assert profile.industry == "Outdoor Apparel"

    def test_default_values(self):
        """Test BrandProfile default values."""
        profile = BrandProfile(
            brand_name="Test Brand",
            website_url="https://example.com",
        )

        assert profile.values == []
        assert profile.tone == ""
        assert profile.industry == ""

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        profile = BrandProfile(
            brand_name="Test",
            website_url="https://test.com",
            custom_field="custom_value",
        )

        assert hasattr(profile, "custom_field")


class TestInfluencerProfile:
    """Tests for InfluencerProfile model."""

    def test_valid_influencer_profile(self):
        """Test creating a valid InfluencerProfile."""
        profile = InfluencerProfile(
            name="Sustainable Amber",
            handle="@sustainableamber",
            platforms=["Instagram", "TikTok", "YouTube"],
            content_themes=["sustainability", "eco-fashion", "zero waste"],
            audience_size_estimate="100K-500K",
            overall_sentiment="positive",
        )

        assert profile.handle == "@sustainableamber"
        assert "sustainability" in profile.content_themes
        assert len(profile.platforms) == 3

    def test_controversies_nullable(self):
        """Test that controversies can be empty."""
        profile = InfluencerProfile(
            name="Test Influencer",
            handle="@test",
        )

        assert profile.controversies == []

    def test_with_controversies(self):
        """Test influencer with controversies."""
        profile = InfluencerProfile(
            name="Controversial Creator",
            handle="@controversial",
            controversies=[
                "2023: Misleading product claims",
                "2024: Brand partnership scandal",
            ],
        )

        assert len(profile.controversies) == 2


class TestAlignmentScore:
    """Tests for AlignmentScore model."""

    def test_valid_alignment_score(self):
        """Test creating a valid AlignmentScore."""
        score = AlignmentScore(
            values_alignment=25,
            values_rationale="Strong alignment with sustainability values",
            audience_overlap=20,
            audience_rationale="Good demographic match",
            tone_compatibility=15,
            tone_rationale="Compatible authentic communication",
            risk_score=12,
            risk_rationale="No significant controversies",
            authenticity_score=8,
            authenticity_rationale="Genuine engagement patterns",
        )

        assert score.values_alignment == 25
        assert score.total_score == 80

    def test_total_score_calculation(self):
        """Test that total_score is computed correctly."""
        score = AlignmentScore(
            values_alignment=30,
            audience_overlap=25,
            tone_compatibility=20,
            risk_score=15,
            authenticity_score=10,
        )

        assert score.total_score == 100

    def test_min_scores(self):
        """Test minimum score values."""
        score = AlignmentScore(
            values_alignment=0,
            audience_overlap=0,
            tone_compatibility=0,
            risk_score=0,
            authenticity_score=0,
        )

        assert score.total_score == 0

    def test_max_bounds_validation(self):
        """Test that scores are bounded correctly."""
        with pytest.raises(ValueError):
            AlignmentScore(values_alignment=35)  # Max is 30

        with pytest.raises(ValueError):
            AlignmentScore(audience_overlap=30)  # Max is 25


class TestMatchResult:
    """Tests for MatchResult model."""

    def test_excellent_match(self):
        """Test excellent match tier."""
        result = MatchResult(
            match_score=85,
            pros=["Strong values alignment", "Great audience fit"],
            red_flags=[],
            confidence_level=ConfidenceLevel.HIGH,
        )

        assert result.match_tier == "Excellent Match"
        assert result.recommendation == RecommendationType.STRONGLY_RECOMMEND

    def test_good_match(self):
        """Test good match tier."""
        result = MatchResult(
            match_score=70,
            pros=["Good values alignment"],
            red_flags=["Minor audience mismatch"],
            confidence_level=ConfidenceLevel.MEDIUM,
        )

        assert result.match_tier == "Good Match"
        assert result.recommendation == RecommendationType.RECOMMEND

    def test_moderate_match(self):
        """Test moderate match tier."""
        result = MatchResult(
            match_score=50,
            pros=["Some overlap"],
            red_flags=["Significant differences"],
            confidence_level=ConfidenceLevel.MEDIUM,
        )

        assert result.match_tier == "Moderate Match"
        assert result.recommendation == RecommendationType.PROCEED_WITH_CAUTION

    def test_weak_match(self):
        """Test weak match tier."""
        result = MatchResult(
            match_score=30,
            pros=[],
            red_flags=["Many misalignments"],
            confidence_level=ConfidenceLevel.LOW,
        )

        assert result.match_tier == "Weak Match"
        assert result.recommendation == RecommendationType.NOT_RECOMMENDED

    def test_poor_match(self):
        """Test poor match tier."""
        result = MatchResult(
            match_score=10,
            pros=[],
            red_flags=["Complete misalignment"],
            confidence_level=ConfidenceLevel.HIGH,
        )

        assert result.match_tier == "Poor Match"
        assert result.recommendation == RecommendationType.NOT_RECOMMENDED

    def test_controversy_impacts_recommendation(self):
        """Test that controversies affect recommendation."""
        result = MatchResult(
            match_score=65,  # Normally would be "recommend"
            pros=["Some good points"],
            red_flags=["Major controversy in 2024"],
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Should downgrade due to controversy
        assert result.recommendation == RecommendationType.NOT_RECOMMENDED

    def test_high_score_overrides_controversy(self):
        """Test that very high scores can still recommend despite controversies."""
        result = MatchResult(
            match_score=85,  # Very high score
            pros=["Excellent fit"],
            red_flags=["Minor controversy resolved"],  # Contains "controversy"
            confidence_level=ConfidenceLevel.HIGH,
        )

        # High score wins over moderate controversy
        assert result.recommendation == RecommendationType.STRONGLY_RECOMMEND


class TestSalesBrief:
    """Tests for SalesBrief model."""

    def test_valid_sales_brief(self):
        """Test creating a valid SalesBrief."""
        brief = SalesBrief(
            executive_summary="Excellent brand-influencer match with strong values alignment.",
            match_score=85,
            match_tier="Excellent Match",
            confidence=ConfidenceLevel.HIGH,
            recommendation=RecommendationType.STRONGLY_RECOMMEND,
            brand_summary="Patagonia is an outdoor apparel brand focused on sustainability.",
            influencer_summary="@sustainableamber creates eco-conscious content.",
            pros=["Values alignment", "Audience fit"],
            red_flags=[],
            next_steps=["Schedule call", "Request demographics"],
        )

        assert brief.match_score == 85
        assert brief.crm_ready is True

    def test_markdown_output(self):
        """Test markdown generation."""
        brief = SalesBrief(
            executive_summary="Good match overall.",
            match_score=75,
            match_tier="Good Match",
            confidence=ConfidenceLevel.MEDIUM,
            recommendation=RecommendationType.RECOMMEND,
            brand_summary="Test brand",
            influencer_summary="Test influencer",
            pros=["Pro 1", "Pro 2"],
            red_flags=["Risk 1"],
            next_steps=["Step 1", "Step 2"],
        )

        markdown = brief.to_markdown()

        assert "# Brand-Influencer Match Analysis" in markdown
        assert "75/100" in markdown
        assert "Good Match" in markdown
        assert "✅ Pro 1" in markdown
        assert "⚠️ Risk 1" in markdown
        assert "1. Step 1" in markdown

    def test_markdown_no_red_flags(self):
        """Test markdown when no red flags exist."""
        brief = SalesBrief(
            executive_summary="Perfect match.",
            match_score=95,
            match_tier="Excellent Match",
            confidence=ConfidenceLevel.HIGH,
            recommendation=RecommendationType.STRONGLY_RECOMMEND,
            brand_summary="Brand",
            influencer_summary="Influencer",
            pros=["Perfect alignment"],
            red_flags=[],
            next_steps=["Proceed immediately"],
        )

        markdown = brief.to_markdown()

        assert "No significant red flags identified" in markdown


class TestMatchmakerInput:
    """Tests for MatchmakerInput model."""

    def test_valid_input(self):
        """Test valid input schema."""
        input_data = MatchmakerInput(
            brand_url="https://www.patagonia.com",
            influencer_handle="@sustainableamber",
        )

        assert input_data.brand_url == "https://www.patagonia.com"
        assert input_data.influencer_handle == "@sustainableamber"

    def test_input_requires_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValueError):
            MatchmakerInput(brand_url="https://example.com")

        with pytest.raises(ValueError):
            MatchmakerInput(influencer_handle="@test")


class TestMatchmakerOutput:
    """Tests for complete MatchmakerOutput model."""

    def test_complete_output(self):
        """Test creating a complete output."""
        output = MatchmakerOutput(
            brand_profile=BrandProfile(
                brand_name="Patagonia",
                website_url="https://www.patagonia.com",
                industry="Outdoor Apparel",
                values=["sustainability"],
            ),
            influencer_profile=InfluencerProfile(
                name="Sustainable Amber",
                handle="@sustainableamber",
                content_themes=["sustainability"],
            ),
            match_result=MatchResult(
                match_score=85,
                pros=["Values alignment"],
                red_flags=[],
                confidence_level=ConfidenceLevel.HIGH,
            ),
            sales_brief=SalesBrief(
                executive_summary="Excellent match.",
                match_score=85,
                match_tier="Excellent Match",
                confidence=ConfidenceLevel.HIGH,
                recommendation=RecommendationType.STRONGLY_RECOMMEND,
                brand_summary="Outdoor brand",
                influencer_summary="Eco influencer",
                pros=["Values alignment"],
                red_flags=[],
                next_steps=["Schedule call"],
            ),
        )

        assert output.match_result.match_score == 85
        assert output.sales_brief.recommendation == RecommendationType.STRONGLY_RECOMMEND

    def test_json_export(self):
        """Test JSON export functionality."""
        output = MatchmakerOutput(
            brand_profile=BrandProfile(
                brand_name="Test",
                website_url="https://test.com",
            ),
            influencer_profile=InfluencerProfile(
                name="Test",
                handle="@test",
            ),
            match_result=MatchResult(
                match_score=50,
                pros=[],
                red_flags=[],
                confidence_level=ConfidenceLevel.LOW,
            ),
            sales_brief=SalesBrief(
                executive_summary="Test match.",
                match_score=50,
                match_tier="Moderate Match",
                confidence=ConfidenceLevel.LOW,
                recommendation=RecommendationType.PROCEED_WITH_CAUTION,
                brand_summary="Test",
                influencer_summary="Test",
                pros=[],
                red_flags=[],
                next_steps=["Test"],
            ),
        )

        json_output = output.to_json()
        parsed = json.loads(json_output)

        assert parsed["match_result"]["match_score"] == 50
        assert parsed["brand_profile"]["brand_name"] == "Test"


class TestAgentJsonSchema:
    """Tests for agent.json schema validation."""

    @pytest.fixture
    def agent_json_path(self):
        """Path to agent.json file."""
        return Path(__file__).parent.parent.parent / "exports" / "brand_influencer_matchmaker" / "agent.json"

    def test_agent_json_exists(self, agent_json_path):
        """Test that agent.json exists."""
        assert agent_json_path.exists(), f"agent.json not found at {agent_json_path}"

    def test_agent_json_valid_json(self, agent_json_path):
        """Test that agent.json is valid JSON."""
        with open(agent_json_path) as f:
            data = json.load(f)

        assert "agent" in data
        assert "graph" in data
        assert "goal" in data

    def test_agent_json_has_required_nodes(self, agent_json_path):
        """Test that all required nodes exist."""
        with open(agent_json_path) as f:
            data = json.load(f)

        node_ids = [node["id"] for node in data["graph"]["nodes"]]

        assert "brand-analyst" in node_ids
        assert "influencer-discovery" in node_ids
        assert "reasoning-node" in node_ids
        assert "output-formatter" in node_ids

    def test_agent_json_has_required_edges(self, agent_json_path):
        """Test that all required edges exist."""
        with open(agent_json_path) as f:
            data = json.load(f)

        edges = data["graph"]["edges"]
        edge_connections = [(e["source"], e["target"]) for e in edges]

        assert ("brand-analyst", "influencer-discovery") in edge_connections
        assert ("influencer-discovery", "reasoning-node") in edge_connections
        assert ("reasoning-node", "output-formatter") in edge_connections

    def test_agent_json_has_success_criteria(self, agent_json_path):
        """Test that goal has success criteria."""
        with open(agent_json_path) as f:
            data = json.load(f)

        criteria = data["goal"]["success_criteria"]
        assert len(criteria) >= 4  # At least 4 criteria

    def test_agent_json_has_constraints(self, agent_json_path):
        """Test that goal has constraints."""
        with open(agent_json_path) as f:
            data = json.load(f)

        constraints = data["goal"]["constraints"]
        assert len(constraints) >= 2  # At least privacy and accuracy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
