"""FastAPI router for Agent Router API.

Endpoints:
- POST /agents/route - Auto-classify and route task
- GET /agents/route/{job_id} - Poll job status and results
- GET /agents/route/chains - List available chains
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from src.billing.middleware import BillingContext, require_billing
from src.router.schemas import (
    ClassificationRequest,
    ClassificationResult,
    RouterJobResponse,
    RouterJobStatus,
    RouterJobStatusResponse,
    RouterRequest,
)

if TYPE_CHECKING:
    from src.router.chains import ChainRegistry
    from src.router.classifier import TaskClassifier
    from src.router.state import RouterJobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/route", tags=["agent-router"])


# ============================================================================
# Dependencies
# ============================================================================


def get_job_manager() -> RouterJobManager:
    """Dependency to get RouterJobManager."""
    from src.router.state import RouterJobManager

    return RouterJobManager(
        redis_url=os.getenv("REDIS_URL"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
    )


def get_classifier() -> TaskClassifier:
    """Dependency to get TaskClassifier."""
    from src.router.classifier import TaskClassifier

    return TaskClassifier()


def get_chain_registry() -> ChainRegistry:
    """Dependency to get ChainRegistry."""
    from src.router.chains import ChainRegistry
    from src.tools.registry import ToolRegistry

    tool_registry = ToolRegistry()
    return ChainRegistry(tool_registry)


# ============================================================================
# Background Task
# ============================================================================


async def execute_route_job(
    job_id: str,
    request: RouterRequest,
    org_id: str,
    job_manager: RouterJobManager,
    classifier: TaskClassifier,
    chain_registry: ChainRegistry,
) -> None:
    """Background task to classify and execute chain."""
    start_time = perf_counter()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error(f"[ROUTE_TASK] Job {job_id} not found")
            return

        # Step 1: Classify (if not forced)
        if request.force_chain:
            classification = ClassificationResult(
                task_type=request.force_chain,
                confidence=1.0,
                reasoning="Forced chain selection",
                extracted_params=request.context or {},
                recommended_model=None,
            )
        else:
            job.status = RouterJobStatus.CLASSIFYING
            await job_manager.update_job(job)

            classification = await classifier.classify(
                ClassificationRequest(
                    query=request.query,
                    context=str(request.context) if request.context else None,
                )
            )

        job.classification = classification

        # Step 2: Route to chain
        job.status = RouterJobStatus.ROUTING
        await job_manager.update_job(job)

        chain = chain_registry.get(classification.task_type)
        if not chain:
            raise ValueError(
                f"No chain found for task type: {classification.task_type}"
            )

        # Step 3: Execute chain
        job.status = RouterJobStatus.EXECUTING
        await job_manager.update_job(job)

        # Merge params
        params = {**(request.context or {}), **classification.extracted_params}

        # Execute with timeout (10 minutes)
        try:
            result = await asyncio.wait_for(
                chain.execute(params=params, classification=classification),
                timeout=600.0,
            )
            job.chain_result = result
            job.status = RouterJobStatus.COMPLETED
        except TimeoutError as e:
            raise Exception("Chain execution timed out after 10 minutes") from e

        # Record timing
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        job.execution_time_ms = execution_time_ms
        job.completed_at = datetime.now(UTC)

        logger.info(f"[ROUTE_TASK] Job {job_id} completed in {execution_time_ms}ms")

        # Persist to Supabase
        await job_manager.persist_to_supabase(job)

    except Exception as e:
        logger.error(f"[ROUTE_TASK] Job {job_id} failed: {e}")

        try:
            job = await job_manager.get_job(job_id)
            if job:
                job.status = RouterJobStatus.FAILED
                job.error_message = str(e)
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                await job_manager.persist_to_supabase(job)
        except Exception as persist_error:
            logger.error(f"[ROUTE_TASK] Failed to persist error: {persist_error}")


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    response_model=RouterJobResponse,
    status_code=202,
    summary="Auto-classify and route task",
    description=(
        "Automatically classify a task and route to the appropriate execution chain. "
        "Returns immediately with job_id. Poll GET /agents/route/{job_id} for completion."
    ),
    responses={
        402: {"description": "Payment required - subscription issue"},
        429: {"description": "Quota exceeded"},
    },
)
async def route_task(
    request: RouterRequest,
    background_tasks: BackgroundTasks,
    billing: BillingContext = Depends(require_billing(estimated_tokens=10000)),
    job_manager: RouterJobManager = Depends(get_job_manager),
    classifier: TaskClassifier = Depends(get_classifier),
    chain_registry: ChainRegistry = Depends(get_chain_registry),
) -> RouterJobResponse:
    """
    Route a task to the appropriate chain.

    Requires valid subscription and available quota.
    """
    # Create job (billing.org_id is validated by require_billing)
    job = await job_manager.create_job(
        org_id=billing.org_id,
        query=request.query,
        context=request.context,
        max_steps=request.max_steps,
    )

    # Start background task
    background_tasks.add_task(
        execute_route_job,
        job_id=job.job_id,
        request=request,
        org_id=billing.org_id,
        job_manager=job_manager,
        classifier=classifier,
        chain_registry=chain_registry,
    )

    return RouterJobResponse(
        job_id=job.job_id,
        status=job.status,
        poll_url=f"/agents/route/{job.job_id}",
        classification=None,  # Not available yet
    )


@router.get(
    "/chains",
    summary="List available chains",
    description="Get list of all available tool chains and their required tools.",
)
async def list_chains(
    chain_registry: ChainRegistry = Depends(get_chain_registry),
) -> dict:
    """List all available chains."""
    return {
        "chains": chain_registry.list_chains(),
        "count": len(chain_registry.list_chains()),
    }


@router.get(
    "/{job_id}",
    response_model=RouterJobStatusResponse,
    summary="Get router job status",
    description="Poll for job status and results.",
    responses={404: {"description": "Job not found"}},
)
async def get_route_job(
    job_id: str,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    job_manager: RouterJobManager = Depends(get_job_manager),
) -> RouterJobStatusResponse:
    """Get job status and results."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    job = await job_manager.get_job(job_id, org_id=x_org_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return RouterJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        task_type=job.classification.task_type if job.classification else None,
        classification=job.classification,
        chain_result=job.chain_result,
        error_message=job.error_message,
        execution_time_ms=job.execution_time_ms,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
