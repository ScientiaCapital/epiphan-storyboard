"""
FastAPI router for Demo Video Pipeline API.

Endpoints:
- POST /video/demo-pipeline — Start pipeline (202 Accepted, background)
- GET /video/demo-pipeline/jobs/{job_id} — Poll job status and results
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from src.tools.video.demo_pipeline_schemas import (
    DemoPipelineJob,
    DemoPipelineRequest,
    DemoPipelineResponse,
    DemoPipelineStatus,
    DemoPipelineStatusResponse,
)
from src.tools.video.demo_pipeline_state import DemoPipelineJobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["video"])


# ============================================================================
# Dependencies
# ============================================================================


@lru_cache
def get_pipeline_job_manager() -> DemoPipelineJobManager:
    """Dependency to get singleton DemoPipelineJobManager instance."""
    return DemoPipelineJobManager(
        redis_url=os.getenv("REDIS_URL"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
    )


# ============================================================================
# Background Task
# ============================================================================


async def run_demo_pipeline_task(
    job_id: str,
    request: DemoPipelineRequest,
    job_manager: DemoPipelineJobManager,
) -> None:
    """Background task to run the full demo pipeline.

    Flow:
    1. Resolve understanding from request (dict, storyboard_job_id, or raw fields)
    2. Extract scenes via SceneExtractorTool → status: extracting_scenes
    3. Generate video assets via VideoAssetGeneratorTool → status: generating_assets
       (skipped if skip_video_generation=True)
    4. Persist to Supabase → status: completed
    """
    from src.tools.video.scene_extractor import SceneExtractorTool
    from src.tools.video.video_asset_generator import VideoAssetGeneratorTool

    start_time = perf_counter()

    try:
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"[DEMO_PIPELINE_TASK] Job {job_id} not found")
            return

        # ------------------------------------------------------------------
        # Step 1: Resolve understanding
        # ------------------------------------------------------------------
        understanding = _resolve_understanding(request)
        if not understanding:
            job.status = DemoPipelineStatus.FAILED
            job.error_message = (
                "No understanding provided. Supply 'understanding' dict, "
                "'storyboard_job_id', or 'headline' + 'pain_point' + 'business_value'."
            )
            job.execution_time_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.now(UTC)
            await _persist_job(job, job_manager)
            return

        # ------------------------------------------------------------------
        # Step 2: Extract scenes
        # ------------------------------------------------------------------
        job.status = DemoPipelineStatus.EXTRACTING_SCENES
        await job_manager.update_job(job)

        extractor = SceneExtractorTool()
        extraction_result = await extractor.run(
            {
                "understanding": understanding,
                "persona": request.persona,
                "vertical": request.vertical,
                "product_focus": request.product_focus,
            }
        )

        if not extraction_result.success:
            job.status = DemoPipelineStatus.FAILED
            job.error_message = f"Scene extraction failed: {extraction_result.error}"
            job.execution_time_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.now(UTC)
            await _persist_job(job, job_manager)
            return

        job.scene_extraction = extraction_result.result

        # ------------------------------------------------------------------
        # Step 3: Generate video assets (optional)
        # ------------------------------------------------------------------
        if not request.skip_video_generation:
            job.status = DemoPipelineStatus.GENERATING_ASSETS
            await job_manager.update_job(job)

            result_data = extraction_result.result or {}
            scenes = result_data.get("scenes", [])
            generator = VideoAssetGeneratorTool()
            asset_result = await generator.run(
                {
                    "scenes": scenes,
                    "provider": request.provider,
                }
            )

            if asset_result.success:
                job.video_assets = asset_result.result
            else:
                # Video generation failure is non-fatal — scenes are still available
                logger.warning(
                    f"[DEMO_PIPELINE_TASK] Video generation failed for job {job_id}: "
                    f"{asset_result.error}. Scenes still available."
                )
                job.video_assets = {"error": asset_result.error}

        # ------------------------------------------------------------------
        # Step 4: Complete
        # ------------------------------------------------------------------
        job.status = DemoPipelineStatus.COMPLETED
        job.execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.completed_at = datetime.now(UTC)

        logger.info(
            f"[DEMO_PIPELINE_TASK] Job {job_id} completed in {job.execution_time_ms}ms"
        )

        await _persist_job(job, job_manager)

    except Exception as e:
        logger.error(f"[DEMO_PIPELINE_TASK] Unexpected error for job {job_id}: {e}")
        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = DemoPipelineStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                await _persist_job(job, job_manager)
        except Exception as persist_error:
            logger.error(
                f"[DEMO_PIPELINE_TASK] Failed to persist error for {job_id}: {persist_error}"
            )


def _resolve_understanding(request: DemoPipelineRequest) -> dict | None:
    """Resolve understanding from the 3 possible entry points."""
    # Entry point 1: Direct understanding dict
    if request.understanding:
        return request.understanding

    # Entry point 2: Storyboard job ID — would need StoryboardJobManager lookup
    # For MVP, this requires the caller to pass the understanding directly
    if request.storyboard_job_id:
        logger.warning(
            "[DEMO_PIPELINE_TASK] storyboard_job_id lookup not yet implemented. "
            "Pass 'understanding' dict directly."
        )
        return None

    # Entry point 3: Raw content fields
    if request.headline and request.pain_point and request.business_value:
        return {
            "headline": request.headline,
            "pain_point_addressed": request.pain_point,
            "business_value": request.business_value,
            "what_it_does": "",
            "who_benefits": "",
            "differentiator": "",
        }

    return None


async def _persist_job(
    job: DemoPipelineJob, job_manager: DemoPipelineJobManager
) -> None:
    """Try to persist job to Supabase, fallback to Redis update."""
    try:
        await job_manager.persist_to_supabase(job)
    except Exception:
        # If Supabase persistence fails, at least update Redis
        await job_manager.update_job(job)


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/demo-pipeline",
    response_model=DemoPipelineResponse,
    status_code=202,
    summary="Start demo video pipeline",
    description=(
        "Transform storyboard understanding into video scene prompts and "
        "optionally generate video assets. Returns immediately with job_id. "
        "Poll GET /video/demo-pipeline/jobs/{job_id} for results."
    ),
)
async def start_demo_pipeline(
    request: DemoPipelineRequest,
    background_tasks: BackgroundTasks,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    job_manager: DemoPipelineJobManager = Depends(get_pipeline_job_manager),
) -> DemoPipelineResponse:
    """Start the demo video pipeline.

    Returns 202 Accepted with job_id and poll_url.
    """
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Resolve understanding early for validation
    understanding = _resolve_understanding(request)
    if not understanding:
        raise HTTPException(
            status_code=422,
            detail=(
                "Must provide one of: 'understanding' dict, 'storyboard_job_id', "
                "or 'headline' + 'pain_point' + 'business_value'"
            ),
        )

    job = await job_manager.create_job(
        org_id=x_org_id,
        understanding=understanding,
        persona=request.persona,
        vertical=request.vertical,
        product_focus=request.product_focus,
        skip_video_generation=request.skip_video_generation,
    )

    background_tasks.add_task(
        run_demo_pipeline_task,
        job_id=job.job_id,
        request=request,
        job_manager=job_manager,
    )

    return DemoPipelineResponse(
        job_id=job.job_id,
        status=job.status,
        poll_url=f"/video/demo-pipeline/jobs/{job.job_id}",
    )


@router.get(
    "/demo-pipeline/jobs/{job_id}",
    response_model=DemoPipelineStatusResponse,
    summary="Get demo pipeline job status",
    description=(
        "Get status and results of a demo pipeline job. "
        "Poll until status is 'completed' or 'failed'."
    ),
    responses={404: {"description": "Job not found"}},
)
async def get_pipeline_job_status(
    job_id: str,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    job_manager: DemoPipelineJobManager = Depends(get_pipeline_job_manager),
) -> DemoPipelineStatusResponse:
    """Get demo pipeline job status and results."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    job = await job_manager.get_job(job_id, org_id=x_org_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return DemoPipelineStatusResponse(
        job_id=job.job_id,
        status=job.status,
        scene_extraction=job.scene_extraction,
        video_assets=job.video_assets,
        error_message=job.error_message,
        execution_time_ms=job.execution_time_ms,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
