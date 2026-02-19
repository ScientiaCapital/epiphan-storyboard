"""
Hybrid state manager for storyboard jobs using Redis + Supabase.

Architecture:
- Redis: Fast in-memory storage for active jobs (1 hour TTL)
- Supabase: Durable PostgreSQL storage for completed jobs
- Jobs are created in Redis with automatic TTL
- Completed jobs are persisted to Supabase and removed from Redis
- Read operations check Redis first, then fallback to Supabase
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import redis.asyncio as aioredis

try:
    from supabase import Client, create_client
except ImportError:
    # Allow module to load even if supabase is not installed
    Client = None
    create_client = None

from src.storyboard.schemas import JobStatus, JobType, StoryboardJob

logger = logging.getLogger(__name__)


class StoryboardJobManager:
    """Manages storyboard job state across Redis (hot) and Supabase (cold) storage.

    Attributes:
        _redis: Async Redis client for hot state
        _supabase: Supabase client for cold persistence
        _job_ttl: TTL in seconds for Redis job keys (default: 3600 = 1 hour)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        job_ttl: int = 3600,
    ):
        """Initialize StoryboardJobManager with Redis and Supabase connections.

        Args:
            redis_url: Redis connection string (default: from REDIS_URL env var)
            supabase_url: Supabase project URL (default: from SUPABASE_URL env var)
            supabase_key: Supabase service key (default: from SUPABASE_SERVICE_KEY env var)
            job_ttl: TTL in seconds for Redis entries (default: 3600)
        """
        # Redis setup
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

        # Supabase setup
        self._supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self._supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided "
                "or set as environment variables"
            )

        if create_client is None:
            raise ImportError(
                "supabase package is required. Install with: pip install supabase"
            )

        self._supabase: Client = create_client(self._supabase_url, supabase_key)
        self._job_ttl = job_ttl

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.aclose()

    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for job data."""
        return f"storyboard:job:{job_id}"

    async def create_job(
        self,
        org_id: str,
        job_type: JobType,
        input_params: dict,
    ) -> StoryboardJob:
        """Create a new storyboard job in Redis.

        Args:
            org_id: Organization identifier
            job_type: Type of storyboard job
            input_params: Input parameters for the job

        Returns:
            Newly created StoryboardJob with generated UUID

        Raises:
            redis.RedisError: If Redis operations fail
        """
        job = StoryboardJob(
            org_id=org_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            input_params=input_params,
        )

        # Store job in Redis with TTL
        job_data = job.model_dump_json()
        job_key = self._job_key(job.job_id)

        await self._redis.setex(
            job_key,
            self._job_ttl,
            job_data,
        )

        logger.info(
            f"[STORYBOARD_JOB_MANAGER] Created job {job.job_id} "
            f"(type={job_type.value}, org={org_id})"
        )

        return job

    async def get_job(self, job_id: str, org_id: str | None = None) -> StoryboardJob | None:
        """Get job from Redis (fast path) or Supabase (cold storage).

        Args:
            job_id: Unique job identifier
            org_id: Organization ID to validate ownership (optional but recommended)

        Returns:
            StoryboardJob if found and authorized, None otherwise

        Raises:
            redis.RedisError: If Redis operations fail
            Exception: If Supabase query fails
        """
        # Try Redis first (hot state)
        job_key = self._job_key(job_id)
        job_data = await self._redis.get(job_key)

        if job_data:
            job = StoryboardJob.model_validate_json(job_data)
            # Validate org_id if provided
            if org_id and job.org_id != org_id:
                logger.warning(
                    f"[STORYBOARD_JOB_MANAGER] Org mismatch for job {job_id}: "
                    f"requested={org_id}, actual={job.org_id}"
                )
                return None
            return job

        # Fallback to Supabase (cold storage)
        try:
            query = self._supabase.table("storyboard_jobs").select("*").eq("id", job_id)

            # Add org filter if provided for multi-tenant isolation
            if org_id:
                query = query.eq("org_id", org_id)

            response = query.single().execute()

            if response.data:
                # Convert Supabase response to StoryboardJob
                job_dict = response.data
                # Map 'id' to 'job_id'
                job_dict["job_id"] = job_dict.pop("id")
                return StoryboardJob.model_validate(job_dict)

        except Exception as e:
            # Job not found in Supabase either
            logger.debug(f"[STORYBOARD_JOB_MANAGER] Job {job_id} not found in Supabase: {e}")
            return None

        return None

    async def update_job(self, job: StoryboardJob) -> None:
        """Update job in Redis and reset TTL.

        Args:
            job: StoryboardJob to update

        Raises:
            redis.RedisError: If Redis operations fail
        """
        job_data = job.model_dump_json()
        job_key = self._job_key(job.job_id)

        # Update with fresh TTL
        await self._redis.setex(
            job_key,
            self._job_ttl,
            job_data,
        )

        logger.debug(
            f"[STORYBOARD_JOB_MANAGER] Updated job {job.job_id} "
            f"(status={job.status.value})"
        )

    async def persist_to_supabase(self, job: StoryboardJob) -> None:
        """Persist job to Supabase and remove from Redis.

        This should be called when a job reaches a terminal state:
        - completed
        - failed

        Args:
            job: StoryboardJob to persist

        Raises:
            Exception: If Supabase operations fail (job remains in Redis)
        """
        # Prepare job data for Supabase
        job_dict = job.model_dump(exclude={"job_id"})
        # Map 'job_id' to 'id' for Supabase
        job_dict["id"] = job.job_id

        try:
            # Insert or update job in Supabase
            self._supabase.table("storyboard_jobs").upsert(job_dict).execute()

            # Delete from Redis only after successful persist
            job_key = self._job_key(job.job_id)
            await self._redis.delete(job_key)

            logger.info(
                f"[STORYBOARD_JOB_MANAGER] Persisted job {job.job_id} to Supabase "
                f"(status={job.status.value}, execution_time={job.execution_time_ms}ms)"
            )
        except Exception as e:
            logger.error(
                f"[STORYBOARD_JOB_MANAGER] Failed to persist job {job.job_id} to Supabase: {e}"
            )
            # Keep job in Redis so it's not lost
            raise
