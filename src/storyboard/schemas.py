"""
Pydantic schemas for Storyboard Pipeline API.

Defines request/response models for async storyboard generation jobs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enum."""

    CODE_TO_STORYBOARD = "code_to_storyboard"
    ROADMAP_TO_STORYBOARD = "roadmap_to_storyboard"
    TRANSCRIPT_TO_STORYBOARD = "transcript_to_storyboard"


class CodeStoryboardRequest(BaseModel):
    """Request model for POST /storyboard/code endpoint."""

    file_content: str = Field(
        ...,
        description="The source code content to analyze",
        min_length=1,
    )
    file_name: str | None = Field(
        None,
        description="Name of the file for context (e.g., 'main.py')",
    )
    icp_preset: str = Field(
        "epiphan_av",
        description="ICP preset to use",
    )
    stage: Literal["preview", "demo", "shipped"] = Field(
        "preview",
        description="Storyboard stage for BDR cadence",
    )
    audience: Literal[
        "av_director",
        "ld_director",
        "sim_center_director",
        "court_admin",
        "corp_comms",
        "ehs_manager",
        "law_firm_it",
        "provost",
        "university_president",
        "university_finance",
        "technical_director",
    ] = Field(
        "av_director",
        description="Target audience persona",
    )
    custom_headline: str | None = Field(
        None,
        description="Optional custom headline override",
    )

    @field_validator("file_content")
    @classmethod
    def validate_file_content_not_empty(cls, v: str) -> str:
        """Ensure file_content is not empty."""
        if not v or not v.strip():
            raise ValueError("file_content must not be empty")
        return v


class RoadmapStoryboardRequest(BaseModel):
    """Request model for POST /storyboard/roadmap endpoint."""

    image_data: str = Field(
        ...,
        description="Base64-encoded image data or data URL",
        min_length=1,
    )
    icp_preset: str = Field(
        "epiphan_av",
        description="ICP preset to use",
    )
    audience: Literal[
        "av_director",
        "ld_director",
        "sim_center_director",
        "court_admin",
        "corp_comms",
        "ehs_manager",
        "law_firm_it",
        "provost",
        "university_president",
        "university_finance",
        "technical_director",
    ] = Field(
        "av_director",
        description="Target audience persona",
    )
    custom_headline: str | None = Field(
        None,
        description="Optional custom headline override",
    )
    sanitize_ip: bool = Field(
        True,
        description="Apply extra IP sanitization",
    )

    @field_validator("image_data")
    @classmethod
    def validate_image_data_not_empty(cls, v: str) -> str:
        """Ensure image_data is not empty."""
        if not v or not v.strip():
            raise ValueError("image_data must not be empty")
        return v


class StoryboardJobResponse(BaseModel):
    """Response model for POST /storyboard/{code|roadmap} (202 Accepted)."""

    job_id: str = Field(
        ...,
        description="Unique job identifier for polling",
    )
    status: JobStatus = Field(
        ...,
        description="Current job status",
    )
    poll_url: str = Field(
        ...,
        description="URL to poll for job status and results",
    )


class StoryboardJobStatusResponse(BaseModel):
    """Response model for GET /storyboard/jobs/{job_id}."""

    job_id: str = Field(
        ...,
        description="Unique job identifier",
    )
    status: JobStatus = Field(
        ...,
        description="Current job status",
    )
    result_image: str | None = Field(
        None,
        description="Base64-encoded PNG storyboard image (available when status=completed)",
    )
    understanding: dict | None = Field(
        None,
        description="Extracted business insights (available when status=completed)",
    )
    error_message: str | None = Field(
        None,
        description="Error details (available when status=failed)",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Total execution time in milliseconds (available when completed/failed)",
    )
    created_at: datetime = Field(
        ...,
        description="Job creation timestamp",
    )
    completed_at: datetime | None = Field(
        None,
        description="Job completion timestamp (available when completed/failed)",
    )


class StoryboardJob(BaseModel):
    """Internal model for storyboard job state."""

    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique job identifier",
    )
    org_id: str = Field(
        ...,
        description="Organization identifier",
    )
    job_type: JobType = Field(
        ...,
        description="Type of storyboard job",
    )
    status: JobStatus = Field(
        JobStatus.PENDING,
        description="Current job status",
    )
    input_params: dict = Field(
        ...,
        description="Input parameters for the job",
    )
    result_image: str | None = Field(
        None,
        description="Base64-encoded PNG storyboard image",
    )
    understanding: dict | None = Field(
        None,
        description="Extracted business insights",
    )
    error_message: str | None = Field(
        None,
        description="Error details if job failed",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Job creation timestamp",
    )
    completed_at: datetime | None = Field(
        None,
        description="Job completion timestamp",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Total execution time in milliseconds",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata",
    )


# ============================================================================
# Transcript-to-Scenarios Pipeline Models
# ============================================================================


class TranscriptStoryboardRequest(BaseModel):
    """Request model for POST /storyboard/transcript endpoint."""

    transcript: str = Field(
        ...,
        description="Pasted call transcript or summary text",
        min_length=1,
        max_length=100_000,
    )
    vertical_hint: str | None = Field(
        None,
        description="Optional vertical hint if BDR already knows (e.g., 'higher_ed')",
    )
    persona_hint: str | None = Field(
        None,
        description="Optional persona hint if BDR already knows (e.g., 'av_director')",
    )
    prospect_name: str | None = Field(
        None,
        description="Prospect name for email personalization",
        max_length=200,
    )
    prospect_company: str | None = Field(
        None,
        description="Prospect company name for email personalization",
        max_length=200,
    )

    @field_validator("transcript")
    @classmethod
    def validate_transcript_not_empty(cls, v: str) -> str:
        """Ensure transcript is not empty."""
        if not v or not v.strip():
            raise ValueError("transcript must not be empty")
        return v


class EmailDraft(BaseModel):
    """BDR follow-up email draft."""

    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text (under 150 words)")


class ScenarioResult(BaseModel):
    """A single matched and customized deployment scenario."""

    scenario_id: str = Field(..., description="Scenario identifier")
    scenario_name: str = Field(..., description="Human-readable scenario name")
    vertical: str = Field(..., description="Target vertical")
    products: list[str] = Field(
        default_factory=list,
        description="Recommended product names (no pricing)",
    )
    bundle_name: str | None = Field(
        None,
        description="Optional bundle name",
    )
    setup_description: str = Field(
        ...,
        description="Customized deployment narrative with call-specific details",
    )
    reference_story: str | None = Field(
        None,
        description="Customer reference story for proof",
    )
    storyboard_png: str = Field(
        default="",
        description="Base64-encoded PNG storyboard image",
    )
    creative_hook: str = Field(
        default="",
        description="The non-obvious angle that sparks imagination",
    )


class TranscriptStoryboardResponse(BaseModel):
    """Response model for completed transcript-to-scenarios job."""

    scenarios: list[ScenarioResult] = Field(
        default_factory=list,
        description="Matched and customized deployment scenarios with storyboard PNGs",
    )
    email_draft: EmailDraft | None = Field(
        None,
        description="BDR follow-up email draft",
    )
    detected_vertical: str = Field(
        default="",
        description="AI-detected vertical from transcript",
    )
    detected_persona: str = Field(
        default="",
        description="AI-detected buyer persona from transcript",
    )
    extraction_confidence: float = Field(
        default=0.0,
        description="Confidence score for transcript extraction (0-1)",
    )


# ── Meeting Recap Schemas ────────────────────────────────────────────────────


class ForcesOfProgress(BaseModel):
    """JTBD Forces of Progress extracted from a call transcript."""

    push: str = Field(default="", description="Current pain driving change")
    pull: str = Field(default="", description="New solution attraction")
    anxiety: str = Field(default="", description="Fear of switching")
    habit: str = Field(default="", description="Comfort of current state")


class HiringFiring(BaseModel):
    """JTBD Hiring/Firing analysis — what they currently 'hire' and why they'd 'fire' it."""

    currently_hired: str = Field(
        default="", description="Current solution (the frankenstack)"
    )
    fired_for: str = Field(default="", description="Why it fails")
    workarounds: str = Field(default="", description="Hacks they've assembled")


class BuyerSignals(BaseModel):
    """Structured buyer signal extraction from call transcript."""

    pain: str = Field(default="", description="Frustrations/problems described")
    need: str = Field(default="", description="Capabilities they're looking for")
    timeline: str = Field(default="", description="Budget cycle, event date, mandate")
    authority: str = Field(default="", description="Who else weighs in on the decision")
    proof: str = Field(
        default="", description="Competitors, reference checks, current vendor"
    )


class ProductRecommendation(BaseModel):
    """Product recommendation with rationale and validated link."""

    product_id: str = Field(..., description="Product ID from EPIPHAN_PRODUCTS")
    product_name: str = Field(..., description="Human-readable product name")
    reason: str = Field(..., description="Why this product fits their job")
    url: str = Field(default="", description="Validated product page URL")
    bundle_option: str | None = Field(None, description="Relevant bundle with savings")


class MeetingRecapRequest(BaseModel):
    """Request model for POST /storyboard/meeting-recap."""

    transcript: str = Field(
        ...,
        description="Raw call transcript (Clari, Gong, Fireflies, or pasted text)",
        min_length=50,
        max_length=100_000,
    )
    audience: str = Field(
        "av_integrator",
        description="Target audience persona (defaults to av_integrator for meetings)",
    )
    vertical: str | None = Field(
        None,
        description="Optional vertical hint (auto-detected from transcript if not provided)",
    )
    include_product_recs: bool = Field(
        True,
        description="Include Epiphan product recommendations based on discussed needs",
    )
    include_follow_up: bool = Field(
        True,
        description="Include NSTTD-style follow-up email draft",
    )

    @field_validator("transcript")
    @classmethod
    def validate_transcript_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("transcript must not be empty")
        return v


class MeetingRecapResponse(BaseModel):
    """Response model for POST /storyboard/meeting-recap.

    Synthesizes JTBD + Challenger + NSTTD frameworks into a structured
    meeting recap with product recommendations and follow-up actions.
    """

    # ── JTBD Analysis ────────────────────────────────────────────
    job_statement: str = Field(
        default="",
        description="JTBD: When [X], I want to [Y], so I can [Z]",
    )
    forces_of_progress: ForcesOfProgress = Field(
        default_factory=ForcesOfProgress,
        description="Forces driving/resisting change",
    )
    hiring_firing: HiringFiring = Field(
        default_factory=HiringFiring,
        description="What they currently hire/fire and workarounds",
    )

    # ── Call Summary ─────────────────────────────────────────────
    summary: str = Field(
        default="",
        description="3-5 bullet executive summary of the call",
    )
    key_topics: list[str] = Field(
        default_factory=list,
        description="Main topics discussed",
    )
    participants: list[dict] = Field(
        default_factory=list,
        description="Participant roles (no names) — e.g., [{role: 'AV Director'}]",
    )
    frankenstack_description: str | None = Field(
        None,
        description="Their current messy AV setup (mismatched vendors, workarounds)",
    )

    # ── Buyer Signals ────────────────────────────────────────────
    buyer_signals: BuyerSignals = Field(
        default_factory=BuyerSignals,
        description="Structured buyer signals (pain, need, timeline, authority, proof)",
    )

    # ── Challenger Reframe ───────────────────────────────────────
    challenger_reframe: str = Field(
        default="",
        description="The insight: Most [persona]s believe X, but Y shows Z",
    )
    rational_drowning: str = Field(
        default="",
        description="Quantified impact — numbers from the call",
    )
    emotional_impact: str = Field(
        default="",
        description="Personal consequence for their role",
    )

    # ── Product Recommendations ──────────────────────────────────
    product_recommendations: list[ProductRecommendation] = Field(
        default_factory=list,
        description="Epiphan products that match discussed needs",
    )
    scenario_matches: list[str] = Field(
        default_factory=list,
        description="Matched deployment scenario IDs from scenario library",
    )

    # ── NSTTD Follow-up ──────────────────────────────────────────
    follow_up_email: str = Field(
        default="",
        description="Tactical empathy email: accusation audit + label + no-oriented CTA",
    )
    calibrated_questions: list[str] = Field(
        default_factory=list,
        description="How/What questions for the next call (never Why)",
    )
    thats_right_summary: str = Field(
        default="",
        description="Summary designed to get 'That\\'s right' (not 'You\\'re right')",
    )

    # ── Metadata ─────────────────────────────────────────────────
    detected_vertical: str | None = Field(
        None,
        description="AI-detected vertical from transcript",
    )
    detected_persona: str | None = Field(
        None,
        description="AI-detected buyer persona from transcript",
    )
    odi_opportunity_score: float | None = Field(
        None,
        description="JTBD Opportunity Index (0-100) — how underserved is this prospect?",
    )


# ── Phase 1.4: Vertical Workflow Surveys ─────────────────────────────────────


class SurveyQuestion(BaseModel):
    """One question in a vertical workflow survey.

    Each question is tagged with its JTBD job-map step so survey responses
    can be aggregated into a coherent BuyerProfile downstream. The optional
    ``force_signal`` tags tell the prompt builder which Force of Progress
    (push/pull/anxiety/habit) the answer feeds.
    """

    id: str = Field(..., description="Stable question id (unique within a survey).")
    section: str = Field(..., description="Section header for the question.")
    text: str = Field(..., description="Question text shown to the respondent.")
    type: Literal["single", "multi", "matrix", "open"] = Field(
        ..., description="Form-control type."
    )
    options: list[str] | None = Field(
        None,
        description="Choice options for single/multi/matrix questions.",
    )
    limit: int | None = Field(
        None,
        description="For multi-select with a cap (e.g. 'select up to 2').",
    )
    job_map_step: Literal[
        "define",
        "locate",
        "prepare",
        "confirm",
        "execute",
        "monitor",
        "modify",
        "conclude",
    ] = Field(..., description="JTBD job-map step this question maps to.")
    force_signal: Literal["push", "pull", "anxiety", "habit"] | None = Field(
        None,
        description="Force of Progress this answer signals when present.",
    )
    internal_intent: str | None = Field(
        None,
        description=(
            "BDR-only note describing why this question exists. Not shown "
            "to respondent; consumed by the prompt builder to weight the "
            "answer correctly."
        ),
    )


class WorkflowSurvey(BaseModel):
    """A vertical-specific workflow survey, modelled after the JTBD switch
    interview. Sourced from the BDR playbook + Live Events workflow doc."""

    vertical: str = Field(..., description="Vertical key — matches EPIPHAN_VERTICALS.")
    title: str = Field(..., description="Display title.")
    intro: str = Field(..., description="Intro copy shown above the form.")
    sections: list[str] = Field(..., description="Ordered list of section headers.")
    questions: list[SurveyQuestion] = Field(
        ..., description="All questions, in display order."
    )


class SurveyResponse(BaseModel):
    """One submitted set of answers to a WorkflowSurvey."""

    survey_id: str = Field(..., description="The vertical key of the survey.")
    answers: dict[str, str | list[str] | dict[str, int]] = Field(
        ...,
        description=(
            "Map of question_id -> answer. Type depends on question.type: "
            "single→str, multi→list[str], matrix→dict[str,int], open→str."
        ),
    )


class BuyerProfile(BaseModel):
    """Survey + transcript signals fused into the shape the prompt builders
    consume. Fed into ``meeting-recap`` to enrich extraction."""

    detected_persona: str = Field(
        ..., description="AudiencePersona enum value selected from survey."
    )
    detected_vertical: str = Field(
        ..., description="Vertical key (matches EPIPHAN_VERTICALS)."
    )
    forces_of_progress: ForcesOfProgress = Field(
        default_factory=ForcesOfProgress,
        description="Per-Force narrative inferred from survey answers.",
    )
    pain_points_ranked: list[tuple[str, float]] = Field(
        default_factory=list,
        description="(pain_anchor, severity 0-1) pairs derived from survey.",
    )
    workflow_signals: dict[str, str] = Field(
        default_factory=dict,
        description="Misc structured signals (room count, tools used, etc.).",
    )
    matched_problem_statements: list[str] = Field(
        default_factory=list,
        description="Verbatim problem statements that resonate with this profile.",
    )
