"""
Pydantic models for Brand-Influencer Matchmaker agent.

This module defines structured output schemas for the matchmaker agent,
ensuring consistent and CRM-ready output formats.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class RecommendationType(str, Enum):
    """Partnership recommendation levels."""

    STRONGLY_RECOMMEND = "strongly_recommend"
    RECOMMEND = "recommend"
    PROCEED_WITH_CAUTION = "proceed_with_caution"
    NOT_RECOMMENDED = "not_recommended"


class ConfidenceLevel(str, Enum):
    """Data confidence levels based on information quality."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BrandProfile(BaseModel):
    """
    Extracted brand profile from website analysis.

    Contains the 'Brand DNA' representing core identity, values,
    and target audience information.
    """

    brand_name: str = Field(description="Name of the brand")
    website_url: str = Field(description="Primary website URL analyzed")
    industry: str = Field(default="", description="Primary industry/sector")
    values: list[str] = Field(
        default_factory=list,
        description="Core values the brand promotes (e.g., sustainability, innovation)",
    )
    tone: str = Field(
        default="",
        description="Communication style (e.g., professional, casual, edgy)",
    )
    target_demographics: dict[str, Any] = Field(
        default_factory=dict,
        description="Target audience demographics and interests",
    )
    key_messages: list[str] = Field(
        default_factory=list,
        description="Primary marketing messages or taglines",
    )
    competitive_positioning: str = Field(
        default="",
        description="How the brand positions itself in the market",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="URLs and sources used to build this profile",
    )

    model_config = {"extra": "allow"}


class InfluencerProfile(BaseModel):
    """
    Profile of an influencer based on public data analysis.

    Captures content themes, audience sentiment, and potential risks.
    """

    name: str = Field(description="Influencer's name or handle")
    handle: str = Field(description="Primary social media handle")
    platforms: list[str] = Field(
        default_factory=list,
        description="Social platforms where they're active",
    )
    content_themes: list[str] = Field(
        default_factory=list,
        description="Main topics they create content about",
    )
    audience_size_estimate: str = Field(
        default="unknown",
        description="Estimated follower count (e.g., '100K-500K')",
    )
    audience_demographics: dict[str, Any] = Field(
        default_factory=dict,
        description="Estimated audience demographics",
    )
    engagement_style: str = Field(
        default="",
        description="How they engage with their audience",
    )
    past_brand_partnerships: list[str] = Field(
        default_factory=list,
        description="Known previous brand collaborations",
    )
    controversies: list[str] = Field(
        default_factory=list,
        description="Any controversies or negative press",
    )
    overall_sentiment: str = Field(
        default="unknown",
        description="General audience sentiment (positive/mixed/negative)",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="URLs and sources used to build this profile",
    )

    model_config = {"extra": "allow"}


class AlignmentScore(BaseModel):
    """
    Detailed breakdown of alignment scoring.

    Each criterion is scored independently to provide
    transparency into the overall match score.
    """

    values_alignment: int = Field(
        default=0,
        ge=0,
        le=30,
        description="Score for values alignment (0-30 points)",
    )
    values_rationale: str = Field(
        default="",
        description="Explanation for values alignment score",
    )

    audience_overlap: int = Field(
        default=0,
        ge=0,
        le=25,
        description="Score for audience overlap (0-25 points)",
    )
    audience_rationale: str = Field(
        default="",
        description="Explanation for audience overlap score",
    )

    tone_compatibility: int = Field(
        default=0,
        ge=0,
        le=20,
        description="Score for tone compatibility (0-20 points)",
    )
    tone_rationale: str = Field(
        default="",
        description="Explanation for tone compatibility score",
    )

    risk_score: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Score for risk assessment (0-15 points, higher = less risk)",
    )
    risk_rationale: str = Field(
        default="",
        description="Explanation for risk assessment score",
    )

    authenticity_score: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Score for authenticity (0-10 points)",
    )
    authenticity_rationale: str = Field(
        default="",
        description="Explanation for authenticity score",
    )

    @computed_field
    @property
    def total_score(self) -> int:
        """Calculate total match score from all criteria."""
        return (
            self.values_alignment
            + self.audience_overlap
            + self.tone_compatibility
            + self.risk_score
            + self.authenticity_score
        )


class MatchResult(BaseModel):
    """
    Complete match analysis between a brand and influencer.

    This is the core output of the reasoning engine.
    """

    match_score: int = Field(
        ge=0,
        le=100,
        description="Overall match score (0-100)",
    )
    alignment_breakdown: AlignmentScore = Field(
        default_factory=AlignmentScore,
        description="Detailed scoring breakdown",
    )
    pros: list[str] = Field(
        default_factory=list,
        description="Specific advantages of this partnership",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Potential risks or concerns",
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence in the analysis based on data quality",
    )

    @computed_field
    @property
    def match_tier(self) -> str:
        """Categorize match quality based on score."""
        if self.match_score >= 80:
            return "Excellent Match"
        elif self.match_score >= 60:
            return "Good Match"
        elif self.match_score >= 40:
            return "Moderate Match"
        elif self.match_score >= 20:
            return "Weak Match"
        else:
            return "Poor Match"

    @computed_field
    @property
    def recommendation(self) -> RecommendationType:
        """Generate recommendation based on score and red flags."""
        has_critical_flags = any(
            "controversy" in flag.lower() or "scandal" in flag.lower()
            for flag in self.red_flags
        )

        if has_critical_flags and self.match_score < 70:
            return RecommendationType.NOT_RECOMMENDED
        elif self.match_score >= 80:
            return RecommendationType.STRONGLY_RECOMMEND
        elif self.match_score >= 60:
            return RecommendationType.RECOMMEND
        elif self.match_score >= 40:
            return RecommendationType.PROCEED_WITH_CAUTION
        else:
            return RecommendationType.NOT_RECOMMENDED


class SalesBrief(BaseModel):
    """
    Structured sales brief for CRM integration.

    Designed to be actionable and easy to parse by sales teams.
    """

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the brief was generated",
    )
    executive_summary: str = Field(
        description="2-3 sentence overview of the match",
    )

    # Match overview
    match_score: int = Field(ge=0, le=100)
    match_tier: str = Field(description="Human-readable match category")
    confidence: ConfidenceLevel
    recommendation: RecommendationType

    # Profiles
    brand_summary: str = Field(
        description="Brief overview of the brand",
    )
    influencer_summary: str = Field(
        description="Brief overview of the influencer",
    )

    # Analysis
    pros: list[str] = Field(
        description="Partnership advantages",
    )
    red_flags: list[str] = Field(
        description="Potential risks",
    )

    # Actionable items
    next_steps: list[str] = Field(
        description="Recommended actions for sales team",
    )

    # Metadata for CRM
    crm_ready: bool = Field(
        default=True,
        description="Flag indicating CRM compatibility",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization in CRM",
    )

    model_config = {"extra": "allow"}

    def to_markdown(self) -> str:
        """Generate markdown-formatted sales brief."""
        lines = [
            "# Brand-Influencer Match Analysis",
            "",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Executive Summary",
            self.executive_summary,
            "",
            "## Match Dashboard",
            f"- **Score:** {self.match_score}/100 ({self.match_tier})",
            f"- **Confidence:** {self.confidence.value.title()}",
            f"- **Recommendation:** {self.recommendation.value.replace('_', ' ').title()}",
            "",
            "## Brand Profile",
            self.brand_summary,
            "",
            "## Influencer Profile",
            self.influencer_summary,
            "",
            "## Partnership Pros",
        ]

        for pro in self.pros:
            lines.append(f"- ✅ {pro}")

        lines.append("")
        lines.append("## Red Flags & Considerations")

        if self.red_flags:
            for flag in self.red_flags:
                lines.append(f"- ⚠️ {flag}")
        else:
            lines.append("- No significant red flags identified.")

        lines.append("")
        lines.append("## Recommended Next Steps")

        for i, step in enumerate(self.next_steps, 1):
            lines.append(f"{i}. {step}")

        return "\n".join(lines)


class MatchmakerInput(BaseModel):
    """Input schema for the Brand-Influencer Matchmaker agent."""

    brand_url: str = Field(
        description="URL of the brand's website (e.g., https://www.patagonia.com)",
    )
    influencer_handle: str = Field(
        description="Influencer's social media handle or full name",
    )


class MatchmakerOutput(BaseModel):
    """Complete output from the Brand-Influencer Matchmaker agent."""

    brand_profile: BrandProfile
    influencer_profile: InfluencerProfile
    match_result: MatchResult
    sales_brief: SalesBrief

    def to_json(self) -> str:
        """Export complete analysis as JSON."""
        return self.model_dump_json(indent=2)
