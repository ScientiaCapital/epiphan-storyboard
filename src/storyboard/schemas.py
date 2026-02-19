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
