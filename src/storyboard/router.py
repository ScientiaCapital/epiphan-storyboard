"""
FastAPI router for Storyboard Pipeline API.

Endpoints:
- POST /storyboard/code - Generate storyboard from code
- POST /storyboard/roadmap - Generate storyboard from roadmap screenshot
- POST /storyboard/transcript - Generate deployment scenario storyboards from call transcript
- POST /storyboard/meeting-recap - Generate JTBD+Challenger+NSTTD meeting recap from transcript
- GET /storyboard/jobs/{job_id} - Get job status and results
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel

from src.storyboard.schemas import (
    BDRCallBrief,
    BuyerProfile,
    CodeStoryboardRequest,
    ForcesOfProgress,
    JobStatus,
    JobType,
    MeetingRecapRequest,
    MeetingRecapResponse,
    RoadmapStoryboardRequest,
    StoryboardJobResponse,
    StoryboardJobStatusResponse,
    SurveyResponse,
    TranscriptStoryboardRequest,
    WorkflowSurvey,
)
from src.storyboard.state import StoryboardJobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storyboard", tags=["storyboard"])


# ============================================================================
# Dependencies
# ============================================================================


@lru_cache
def get_job_manager() -> StoryboardJobManager:
    """Dependency to get singleton StoryboardJobManager instance."""
    return StoryboardJobManager(
        redis_url=os.getenv("REDIS_URL"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
    )


# ============================================================================
# Background Task Functions
# ============================================================================


async def run_code_storyboard_task(
    job_id: str,
    request: CodeStoryboardRequest,
    job_manager: StoryboardJobManager,
) -> None:
    """Background task to run code-to-storyboard pipeline."""
    from src.tools.storyboard.code_to_storyboard import CodeToStoryboardTool

    start_time = perf_counter()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"[CODE_STORYBOARD_TASK] Job {job_id} not found")
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING
        await job_manager.update_job(job)

        # Run tool with timeout (5 minutes)
        tool = CodeToStoryboardTool()
        try:
            result = await asyncio.wait_for(
                tool.run(
                    {
                        "file_content": request.file_content,
                        "file_name": request.file_name,
                        "icp_preset": request.icp_preset,
                        "stage": request.stage,
                        "audience": request.audience,
                        "custom_headline": request.custom_headline,
                    }
                ),
                timeout=300.0,
            )
        except TimeoutError as e:
            raise Exception("Job timed out after 5 minutes") from e

        # Update job with result or error
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(UTC)

        if result.success:
            job.status = JobStatus.COMPLETED
            job.result_image = result.result["storyboard_png"]
            job.understanding = result.result["understanding"]
            job.metadata = {
                "stage": result.result.get("stage"),
                "audience": result.result.get("audience"),
                "icp_preset": result.result.get("icp_preset"),
                "file_name": result.result.get("file_name"),
            }
            logger.info(
                f"[CODE_STORYBOARD_TASK] Job {job_id} completed in {execution_time_ms}ms"
            )
        else:
            job.status = JobStatus.FAILED
            job.error_message = result.error
            logger.error(f"[CODE_STORYBOARD_TASK] Job {job_id} failed: {result.error}")

        # Persist to Supabase
        await job_manager.persist_to_supabase(job)

    except Exception as e:
        logger.error(f"[CODE_STORYBOARD_TASK] Unexpected error for job {job_id}: {e}")
        # Try to update job status to failed
        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                await job_manager.persist_to_supabase(job)
        except Exception as persist_error:
            logger.error(
                f"[CODE_STORYBOARD_TASK] Failed to persist error for job {job_id}: {persist_error}"
            )


async def run_roadmap_storyboard_task(
    job_id: str,
    request: RoadmapStoryboardRequest,
    job_manager: StoryboardJobManager,
) -> None:
    """Background task to run roadmap-to-storyboard pipeline."""
    from src.tools.storyboard.roadmap_to_storyboard import RoadmapToStoryboardTool

    start_time = perf_counter()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"[ROADMAP_STORYBOARD_TASK] Job {job_id} not found")
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING
        await job_manager.update_job(job)

        # Run tool with timeout (5 minutes)
        tool = RoadmapToStoryboardTool()
        try:
            result = await asyncio.wait_for(
                tool.run(
                    {
                        "image_data": request.image_data,
                        "icp_preset": request.icp_preset,
                        "audience": request.audience,
                        "custom_headline": request.custom_headline,
                        "sanitize_ip": request.sanitize_ip,
                    }
                ),
                timeout=300.0,
            )
        except TimeoutError as e:
            raise Exception("Job timed out after 5 minutes") from e

        # Update job with result or error
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(UTC)

        if result.success:
            job.status = JobStatus.COMPLETED
            job.result_image = result.result["storyboard_png"]
            job.understanding = result.result["understanding"]
            job.metadata = {
                "stage": result.result.get("stage"),
                "audience": result.result.get("audience"),
                "icp_preset": result.result.get("icp_preset"),
                "is_teaser": result.result.get("is_teaser"),
                "ip_sanitized": result.result.get("ip_sanitized"),
            }
            logger.info(
                f"[ROADMAP_STORYBOARD_TASK] Job {job_id} completed in {execution_time_ms}ms"
            )
        else:
            job.status = JobStatus.FAILED
            job.error_message = result.error
            logger.error(
                f"[ROADMAP_STORYBOARD_TASK] Job {job_id} failed: {result.error}"
            )

        # Persist to Supabase
        await job_manager.persist_to_supabase(job)

    except Exception as e:
        logger.error(
            f"[ROADMAP_STORYBOARD_TASK] Unexpected error for job {job_id}: {e}"
        )
        # Try to update job status to failed
        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                await job_manager.persist_to_supabase(job)
        except Exception as persist_error:
            logger.error(
                f"[ROADMAP_STORYBOARD_TASK] Failed to persist error for job {job_id}: {persist_error}"
            )


async def run_transcript_storyboard_task(
    job_id: str,
    request: TranscriptStoryboardRequest,
    job_manager: StoryboardJobManager,
) -> None:
    """Background task to run transcript-to-scenarios pipeline."""
    from src.tools.storyboard.transcript_to_scenarios import TranscriptToScenariosTool

    start_time = perf_counter()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"[TRANSCRIPT_STORYBOARD_TASK] Job {job_id} not found")
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING
        await job_manager.update_job(job)

        # Run tool with timeout (10 minutes — generates multiple storyboards)
        tool = TranscriptToScenariosTool()
        try:
            result = await asyncio.wait_for(
                tool.run(
                    {
                        "transcript": request.transcript,
                        "vertical_hint": request.vertical_hint,
                        "persona_hint": request.persona_hint,
                        "prospect_name": request.prospect_name,
                        "prospect_company": request.prospect_company,
                    }
                ),
                timeout=600.0,
            )
        except TimeoutError as e:
            raise Exception("Job timed out after 10 minutes") from e

        # Update job with result or error
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(UTC)

        if result.success:
            job.status = JobStatus.COMPLETED
            # Store first scenario storyboard as result_image for compatibility
            scenarios = result.result.get("scenarios", [])
            if scenarios and scenarios[0].get("storyboard_png"):
                job.result_image = scenarios[0]["storyboard_png"]
            job.understanding = {
                "scenarios": scenarios,
                "email_draft": result.result.get("email_draft"),
                "detected_vertical": result.result.get("detected_vertical"),
                "detected_persona": result.result.get("detected_persona"),
                "extraction_confidence": result.result.get("extraction_confidence"),
            }
            job.metadata = {
                "scenario_count": len(scenarios),
                "detected_vertical": result.result.get("detected_vertical"),
                "detected_persona": result.result.get("detected_persona"),
                "prospect_company": request.prospect_company,
            }
            logger.info(
                f"[TRANSCRIPT_STORYBOARD_TASK] Job {job_id} completed in {execution_time_ms}ms "
                f"({len(scenarios)} scenarios)"
            )
        else:
            job.status = JobStatus.FAILED
            job.error_message = result.error
            logger.error(
                f"[TRANSCRIPT_STORYBOARD_TASK] Job {job_id} failed: {result.error}"
            )

        # Persist to Supabase
        await job_manager.persist_to_supabase(job)

    except Exception as e:
        logger.error(
            f"[TRANSCRIPT_STORYBOARD_TASK] Unexpected error for job {job_id}: {e}"
        )
        # Try to update job status to failed
        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                await job_manager.persist_to_supabase(job)
        except Exception as persist_error:
            logger.error(
                f"[TRANSCRIPT_STORYBOARD_TASK] Failed to persist error for job {job_id}: {persist_error}"
            )


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/code",
    response_model=StoryboardJobResponse,
    status_code=202,
    summary="Generate storyboard from code",
    description=(
        "Transform code files into beautiful one-page PNG storyboards. "
        "Returns immediately with job_id and poll_url. "
        "Use GET /storyboard/jobs/{job_id} to poll for completion."
    ),
)
async def generate_code_storyboard(
    request: CodeStoryboardRequest,
    background_tasks: BackgroundTasks,
    x_org_id: str = Header("default", alias="X-Org-ID"),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobResponse:
    """
    Generate storyboard from code file.

    Returns immediately with job ID. Poll GET /storyboard/jobs/{job_id} for completion.
    """
    job = await job_manager.create_job(
        org_id=x_org_id,
        job_type=JobType.CODE_TO_STORYBOARD,
        input_params=request.model_dump(),
    )

    # Start background task
    background_tasks.add_task(
        run_code_storyboard_task,
        job_id=job.job_id,
        request=request,
        job_manager=job_manager,
    )

    return StoryboardJobResponse(
        job_id=job.job_id,
        status=job.status,
        poll_url=f"/storyboard/jobs/{job.job_id}",
    )


@router.post(
    "/roadmap",
    response_model=StoryboardJobResponse,
    status_code=202,
    summary="Generate storyboard from roadmap screenshot",
    description=(
        "Transform Miro/roadmap screenshots into sanitized 'Coming Soon' teasers. "
        "Returns immediately with job_id and poll_url. "
        "Use GET /storyboard/jobs/{job_id} to poll for completion."
    ),
)
async def generate_roadmap_storyboard(
    request: RoadmapStoryboardRequest,
    background_tasks: BackgroundTasks,
    x_org_id: str = Header("default", alias="X-Org-ID"),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobResponse:
    """
    Generate storyboard from roadmap screenshot.

    Returns immediately with job ID. Poll GET /storyboard/jobs/{job_id} for completion.
    """
    job = await job_manager.create_job(
        org_id=x_org_id,
        job_type=JobType.ROADMAP_TO_STORYBOARD,
        input_params=request.model_dump(),
    )

    # Start background task
    background_tasks.add_task(
        run_roadmap_storyboard_task,
        job_id=job.job_id,
        request=request,
        job_manager=job_manager,
    )

    return StoryboardJobResponse(
        job_id=job.job_id,
        status=job.status,
        poll_url=f"/storyboard/jobs/{job.job_id}",
    )


@router.post(
    "/transcript",
    response_model=StoryboardJobResponse,
    status_code=202,
    summary="Generate deployment scenario storyboards from call transcript",
    description=(
        "Paste a call transcript or summary to get 2-4 deployment scenario storyboards "
        "tailored to the prospect's vertical and interests, plus a BDR follow-up email draft. "
        "Returns immediately with job_id and poll_url. "
        "Use GET /storyboard/jobs/{job_id} to poll for completion."
    ),
)
async def generate_transcript_storyboard(
    request: TranscriptStoryboardRequest,
    background_tasks: BackgroundTasks,
    x_org_id: str = Header("default", alias="X-Org-ID"),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobResponse:
    """
    Generate deployment scenario storyboards from call transcript.

    Returns immediately with job ID. Poll GET /storyboard/jobs/{job_id} for completion.
    Result includes 2-4 scenario storyboard PNGs and a BDR follow-up email draft.
    """
    job = await job_manager.create_job(
        org_id=x_org_id,
        job_type=JobType.TRANSCRIPT_TO_STORYBOARD,
        input_params=request.model_dump(),
    )

    # Start background task
    background_tasks.add_task(
        run_transcript_storyboard_task,
        job_id=job.job_id,
        request=request,
        job_manager=job_manager,
    )

    return StoryboardJobResponse(
        job_id=job.job_id,
        status=job.status,
        poll_url=f"/storyboard/jobs/{job.job_id}",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=StoryboardJobStatusResponse,
    summary="Get storyboard job status",
    description=(
        "Get status and results of a storyboard generation job. "
        "Poll this endpoint until status is 'completed' or 'failed'."
    ),
    responses={404: {"description": "Job not found"}},
)
async def get_job_status(
    job_id: str,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobStatusResponse:
    """
    Get job status and results.

    Use this to poll for completion after starting a job.
    """
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    job = await job_manager.get_job(job_id, org_id=x_org_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return StoryboardJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        result_image=job.result_image,
        understanding=job.understanding,
        error_message=job.error_message,
        execution_time_ms=job.execution_time_ms,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post(
    "/meeting-recap",
    response_model=MeetingRecapResponse,
    summary="Generate structured meeting recap from call transcript",
    description=(
        "Drop a Clari, Gong, or Fireflies call transcript and get a JTBD-structured "
        "recap with Challenger reframe, product recommendations, and NSTTD-style "
        "follow-up email draft. Synchronous — returns immediately with results."
    ),
)
async def generate_meeting_recap(
    request: MeetingRecapRequest,
) -> MeetingRecapResponse:
    """
    Generate a structured meeting recap from a call transcript.

    Analyzes the transcript using three sales frameworks:
    - JTBD: Job statement, Forces of Progress, frankenstack detection
    - Challenger: Reframe, rational drowning, emotional impact
    - NSTTD: Accusation audit email, calibrated questions, "That's right" summary

    Returns product recommendations with validated links and deployment scenario matches.
    """
    from src.tools.storyboard.meeting_recap import process_meeting_recap

    start = perf_counter()

    try:
        result = await process_meeting_recap(
            transcript=request.transcript,
            audience=request.audience,
            vertical=request.vertical,
            include_product_recs=request.include_product_recs,
            include_follow_up=request.include_follow_up,
        )
    except Exception as e:
        logger.error("Meeting recap failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Meeting recap generation failed: {e}",
        ) from e

    elapsed_ms = int((perf_counter() - start) * 1000)
    logger.info("Meeting recap completed in %d ms", elapsed_ms)

    # Map raw dict result to Pydantic response model
    return MeetingRecapResponse(
        job_statement=result.get("job_statement", ""),
        forces_of_progress=result.get("forces_of_progress", {}),
        hiring_firing=result.get("hiring_firing", {}),
        summary=result.get("summary", ""),
        key_topics=result.get("key_topics", []),
        participants=result.get("participants", []),
        frankenstack_description=result.get("frankenstack_description"),
        buyer_signals=result.get("buyer_signals", {}),
        challenger_reframe=result.get("challenger_reframe", ""),
        rational_drowning=result.get("rational_drowning", ""),
        emotional_impact=result.get("emotional_impact", ""),
        product_recommendations=result.get("product_recommendations", []),
        scenario_matches=result.get("scenario_matches", []),
        follow_up_email=result.get("follow_up_email", ""),
        calibrated_questions=result.get("calibrated_questions", []),
        thats_right_summary=result.get("thats_right_summary", ""),
        detected_vertical=result.get("detected_vertical"),
        detected_persona=result.get("detected_persona"),
        odi_opportunity_score=result.get("odi_opportunity_score"),
    )


# ============================================================================
# Phase 1.5 — Vertical Workflow Survey endpoints
# ============================================================================


@router.get(
    "/survey/templates/{vertical}",
    response_model=WorkflowSurvey,
    summary="Fetch the workflow survey template for a vertical",
    description=(
        "Returns the JTBD-structured workflow survey for the requested "
        "vertical. Phase 1 ships higher_ed, legal, and live_events. "
        "Other verticals return 404."
    ),
)
async def get_survey_template(vertical: str) -> WorkflowSurvey:
    """Return the WorkflowSurvey for ``vertical`` or 404 if not registered."""
    from src.tools.storyboard.vertical_surveys import get_survey

    survey = get_survey(vertical)
    if survey is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No workflow survey registered for vertical '{vertical}'. "
                f"Phase 1 covers higher_ed, legal, live_events. Phase 2 "
                f"will add the remaining verticals."
            ),
        )
    return survey


# Request schema for the submit endpoint — defined inline so the router
# stays the single source of truth for the survey-submission contract.
class SurveySubmitRequest(BaseModel):
    """Body for POST /storyboard/survey/submit.

    The transcript is optional — survey-only submissions still produce a
    BDR brief, just with confidence=lower.
    """

    vertical: str
    responses: SurveyResponse
    transcript: str | None = None
    prospect_company: str | None = None
    prospect_first_name: str | None = None


class SurveySubmitResponse(BaseModel):
    """Response for POST /storyboard/survey/submit."""

    bdr_call_brief: BDRCallBrief
    buyer_profile: BuyerProfile


def _persona_from_role_text(role_text: str | None) -> str:
    """Heuristic: map a role-question answer to AudiencePersona.

    Falls back to 'av_director' when the role string can't be matched —
    'av_director' is the most common buyer across verticals per memory.
    """
    from src.tools.storyboard.problem_statements import normalize_doc_persona

    if not role_text:
        return "av_director"
    direct = normalize_doc_persona(role_text)
    if direct:
        return direct
    lower = role_text.lower()
    if "av director" in lower or "av architecture" in lower:
        return "av_director"
    if "production manager" in lower or "technical director" in lower:
        return "technical_director"
    if "court admin" in lower:
        return "court_admin"
    if "venue" in lower or "event technology" in lower:
        return "venue_manager"
    if "design engineer" in lower or "systems integrator" in lower:
        return "system_engineer"
    if "reseller" in lower or "account development" in lower:
        return "av_integrator"
    return "av_director"


def _profile_from_responses(vertical: str, responses: SurveyResponse) -> BuyerProfile:
    """Build a BuyerProfile from raw survey answers.

    The first answer to a question whose id ends in `_q1` is treated as the
    role disambiguator. Workflow signals get copied through verbatim. Forces
    of Progress are filled in only when we have enough signal — empty
    fields are fine; the brief generator handles them.
    """
    answers = responses.answers
    role_q_id = next(
        (qid for qid in answers if qid.endswith("_q1")),
        None,
    )
    role_value = answers.get(role_q_id) if role_q_id else None
    role_str = role_value if isinstance(role_value, str) else None
    persona = _persona_from_role_text(role_str)

    workflow_signals: dict[str, str] = {}
    for k, v in answers.items():
        if isinstance(v, str):
            workflow_signals[k] = v
        elif isinstance(v, list):
            workflow_signals[k] = "; ".join(v)

    return BuyerProfile(
        detected_persona=persona,
        detected_vertical=vertical,
        forces_of_progress=ForcesOfProgress(),
        pain_points_ranked=[],
        workflow_signals=workflow_signals,
    )


@router.post(
    "/survey/submit",
    response_model=SurveySubmitResponse,
    summary="Submit a workflow survey response and get a BDR call brief",
    description=(
        "Accepts a SurveyResponse (and optional transcript). Returns a "
        "BDRCallBrief with persona detection, top-3 verbatim problem "
        "statements, JTBD job statement, Forces of Progress, calibrated "
        "questions, and an NSTTD-style follow-up email."
    ),
)
async def submit_survey(request: SurveySubmitRequest) -> SurveySubmitResponse:
    """Build a BDR brief from survey responses + optional transcript."""
    from src.tools.storyboard.bdr_brief_generator import (
        generate_brief_from_profile,
        generate_brief_from_transcript,
    )
    from src.tools.storyboard.vertical_surveys import get_survey

    if get_survey(request.vertical) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No workflow survey registered for vertical "
                f"'{request.vertical}'. Phase 1 covers higher_ed, legal, "
                f"live_events."
            ),
        )

    profile = _profile_from_responses(request.vertical, request.responses)

    if request.transcript and request.transcript.strip():
        brief = generate_brief_from_transcript(
            transcript=request.transcript,
            vertical=profile.detected_vertical,
            persona=profile.detected_persona,
            forces=profile.forces_of_progress,
            extraction_confidence=0.7,
            prospect_first_name=request.prospect_first_name,
        )
    else:
        brief = generate_brief_from_profile(
            profile,
            extraction_confidence=0.6,
            prospect_first_name=request.prospect_first_name,
        )

    return SurveySubmitResponse(bdr_call_brief=brief, buyer_profile=profile)
