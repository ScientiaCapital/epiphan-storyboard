"""
Hybrid state manager for demo pipeline jobs using Redis + Supabase.

Architecture (follows StoryboardJobManager pattern from src/storyboard/state.py):
- Redis: Fast in-memory storage for active jobs (1 hour TTL)
- Supabase: Durable PostgreSQL storage for completed jobs
- Lazy Supabase init to avoid constructor failures when env vars aren't set

Key difference from StoryboardJobManager: Supabase client is created lazily
on first persist call, not eagerly in __init__. This makes testing easier
and avoids failures when only Redis is configured.
"""

from __future__ import annotations

import logging
import os

import redis.asyncio as aioredis

from src.tools.video.demo_pipeline_schemas import (
    DemoPipelineJob,
    DemoPipelineStatus,
)

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "demo_pipeline:job"
DEFAULT_JOB_TTL = 3600  # 1 hour


class DemoPipelineJobManager:
    """Manages demo pipeline job state across Redis (hot) and Supabase (cold) storage.

    Attributes:
        _redis: Async Redis client for hot state
        _supabase: Lazy-initialized Supabase client for cold persistence
        _job_ttl: TTL in seconds for Redis job keys (default: 3600)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        job_ttl: int = DEFAULT_JOB_TTL,
    ):
        """Initialize with Redis connection. Supabase is lazily initialized.

        Args:
            redis_url: Redis connection string (default: from REDIS_URL env var)
            supabase_url: Supabase project URL (stored for lazy init)
            supabase_key: Supabase service key (stored for lazy init)
            job_ttl: TTL in seconds for Redis entries (default: 3600)
        """
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        if not self._redis_url:
            raise ValueError(
                "Redis URL must be provided or set via REDIS_URL environment variable"
            )

        self._redis = aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Store Supabase config for lazy init
        self._supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self._supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
        self._supabase = None  # Lazy init
        self._job_ttl = job_ttl

    def _get_supabase(self):  # type: ignore[no-untyped-def]
        """Lazily initialize Supabase client on first use."""
        if self._supabase is not None:
            return self._supabase

        try:
            from supabase import create_client
        except ImportError as e:
            raise ImportError(
                "supabase package is required for persistence. "
                "Install with: pip install supabase"
            ) from e

        if not self._supabase_url or not self._supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided "
                "or set as environment variables for persistence"
            )

        self._supabase = create_client(self._supabase_url, self._supabase_key)
        return self._supabase

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.aclose()

    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for job data."""
        return f"{REDIS_KEY_PREFIX}:{job_id}"

    async def create_job(
        self,
        org_id: str,
        understanding: dict,
        persona: str = "av_director",
        vertical: str = "higher_ed",
        product_focus: str = "pearl_mini",
        skip_video_generation: bool = False,
    ) -> DemoPipelineJob:
        """Create a new demo pipeline job in Redis.

        Args:
            org_id: Organization identifier
            understanding: StoryboardUnderstanding dict
            persona: Target persona key
            vertical: Target vertical key
            product_focus: Product to feature
            skip_video_generation: If True, only extract scenes

        Returns:
            Newly created DemoPipelineJob
        """
        job = DemoPipelineJob(
            org_id=org_id,
            understanding=understanding,
            persona=persona,
            vertical=vertical,
            product_focus=product_focus,
            skip_video_generation=skip_video_generation,
        )

        job_key = self._job_key(job.job_id)
        await self._redis.setex(job_key, self._job_ttl, job.model_dump_json())

        logger.info(
            f"[DEMO_PIPELINE_STATE] Created job {job.job_id} "
            f"(persona={persona}, vertical={vertical}, org={org_id})"
        )

        return job

    async def get_job(
        self, job_id: str, org_id: str | None = None
    ) -> DemoPipelineJob | None:
        """Get job from Redis (fast path) or Supabase (cold storage).

        Args:
            job_id: Unique job identifier
            org_id: Organization ID to validate ownership (optional)

        Returns:
            DemoPipelineJob if found and authorized, None otherwise
        """
        # Try Redis first (hot state)
        job_key = self._job_key(job_id)
        job_data = await self._redis.get(job_key)

        if job_data:
            job = DemoPipelineJob.model_validate_json(job_data)
            if org_id and job.org_id != org_id:
                logger.warning(
                    f"[DEMO_PIPELINE_STATE] Org mismatch for job {job_id}: "
                    f"requested={org_id}, actual={job.org_id}"
                )
                return None
            return job

        # Fallback to Supabase (cold storage)
        try:
            supabase = self._get_supabase()
            query = supabase.table("demo_pipeline_jobs").select("*").eq("id", job_id)
            if org_id:
                query = query.eq("org_id", org_id)

            response = query.single().execute()

            if response.data:
                job_dict = response.data
                job_dict["job_id"] = job_dict.pop("id")
                return DemoPipelineJob.model_validate(job_dict)

        except Exception as e:
            logger.debug(
                f"[DEMO_PIPELINE_STATE] Job {job_id} not found in Supabase: {e}"
            )
            return None

        return None

    async def update_job(self, job: DemoPipelineJob) -> None:
        """Update job in Redis and reset TTL.

        Args:
            job: DemoPipelineJob to update
        """
        job_key = self._job_key(job.job_id)
        await self._redis.setex(job_key, self._job_ttl, job.model_dump_json())

        logger.debug(
            f"[DEMO_PIPELINE_STATE] Updated job {job.job_id} "
            f"(status={job.status.value})"
        )

    async def update_status(
        self, job_id: str, status: DemoPipelineStatus
    ) -> DemoPipelineJob | None:
        """Convenience method to update just the job status.

        Args:
            job_id: Job identifier
            status: New status

        Returns:
            Updated job or None if not found
        """
        job = await self.get_job(job_id)
        if job is None:
            return None

        job.status = status
        await self.update_job(job)
        return job

    async def persist_to_supabase(self, job: DemoPipelineJob) -> None:
        """Persist job to Supabase and remove from Redis.

        Should be called when job reaches terminal state (completed/failed).

        Args:
            job: DemoPipelineJob to persist
        """
        job_dict = job.model_dump(exclude={"job_id"})
        job_dict["id"] = job.job_id

        try:
            supabase = self._get_supabase()
            supabase.table("demo_pipeline_jobs").upsert(job_dict).execute()

            # Delete from Redis only after successful persist
            job_key = self._job_key(job.job_id)
            await self._redis.delete(job_key)

            logger.info(
                f"[DEMO_PIPELINE_STATE] Persisted job {job.job_id} to Supabase "
                f"(status={job.status.value}, time={job.execution_time_ms}ms)"
            )
        except Exception as e:
            logger.error(
                f"[DEMO_PIPELINE_STATE] Failed to persist job {job.job_id}: {e}"
            )
            raise
