"""
FastAPI router for Storyboard Pipeline API.

Endpoints:
- POST /storyboard/code - Generate storyboard from code
- POST /storyboard/roadmap - Generate storyboard from roadmap screenshot
- GET /storyboard/jobs/{job_id} - Get job status and results
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from src.billing.middleware import BillingContext, require_billing
from src.storyboard.schemas import (
    CodeStoryboardRequest,
    JobStatus,
    JobType,
    RoadmapStoryboardRequest,
    StoryboardJobResponse,
    StoryboardJobStatusResponse,
)
from src.storyboard.state import StoryboardJobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storyboard", tags=["storyboard"])


# ============================================================================
# Dependencies
# ============================================================================


@lru_cache()
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
        except asyncio.TimeoutError:
            raise Exception("Job timed out after 5 minutes")

        # Update job with result or error
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(timezone.utc)

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
            logger.error(
                f"[CODE_STORYBOARD_TASK] Job {job_id} failed: {result.error}"
            )

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
                job.completed_at = datetime.now(timezone.utc)
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
        except asyncio.TimeoutError:
            raise Exception("Job timed out after 5 minutes")

        # Update job with result or error
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(timezone.utc)

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
        logger.error(f"[ROADMAP_STORYBOARD_TASK] Unexpected error for job {job_id}: {e}")
        # Try to update job status to failed
        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(timezone.utc)
                await job_manager.persist_to_supabase(job)
        except Exception as persist_error:
            logger.error(
                f"[ROADMAP_STORYBOARD_TASK] Failed to persist error for job {job_id}: {persist_error}"
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
    responses={
        402: {"description": "Payment required - subscription issue"},
        429: {"description": "Quota exceeded"},
    },
)
async def generate_code_storyboard(
    request: CodeStoryboardRequest,
    background_tasks: BackgroundTasks,
    billing: BillingContext = Depends(require_billing(estimated_tokens=5000)),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobResponse:
    """
    Generate storyboard from code file.

    Returns immediately with job ID. Poll GET /storyboard/jobs/{job_id} for completion.

    Requires valid subscription and available quota.
    """
    # Create job (billing.org_id is validated by require_billing)
    job = await job_manager.create_job(
        org_id=billing.org_id,
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
    responses={
        402: {"description": "Payment required - subscription issue"},
        429: {"description": "Quota exceeded"},
    },
)
async def generate_roadmap_storyboard(
    request: RoadmapStoryboardRequest,
    background_tasks: BackgroundTasks,
    billing: BillingContext = Depends(require_billing(estimated_tokens=5000)),
    job_manager: StoryboardJobManager = Depends(get_job_manager),
) -> StoryboardJobResponse:
    """
    Generate storyboard from roadmap screenshot.

    Returns immediately with job ID. Poll GET /storyboard/jobs/{job_id} for completion.

    Requires valid subscription and available quota.
    """
    # Create job (billing.org_id is validated by require_billing)
    job = await job_manager.create_job(
        org_id=billing.org_id,
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
