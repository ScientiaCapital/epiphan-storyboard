"""Router job state management using Redis + Supabase.

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

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore

try:
    from supabase import Client, create_client
except ImportError:
    Client = None  # type: ignore
    create_client = None  # type: ignore

from src.router.schemas import RouterJob, RouterJobStatus

logger = logging.getLogger(__name__)


class RouterJobManager:
    """Manages router job state across Redis (hot) and Supabase (cold) storage.

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
        """Initialize RouterJobManager.

        Args:
            redis_url: Redis connection string (default: from REDIS_URL env var)
            supabase_url: Supabase project URL (default: from SUPABASE_URL env var)
            supabase_key: Supabase service key (default: from SUPABASE_SERVICE_KEY env var)
            job_ttl: TTL in seconds for Redis entries (default: 3600)
        """
        self._job_ttl = job_ttl

        # Redis setup (optional for testing)
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None
        if self._redis_url and aioredis:
            self._redis = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

        # Supabase setup (optional for testing)
        self._supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
        self._supabase: Client | None = None

        if self._supabase_url and supabase_key and create_client is not None:
            self._supabase = create_client(self._supabase_url, supabase_key)

    async def close(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.aclose()

    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for a job."""
        return f"router:job:{job_id}"

    async def create_job(
        self,
        org_id: str,
        query: str,
        context: dict | None = None,
        max_steps: int = 10,
    ) -> RouterJob:
        """Create a new router job.

        Args:
            org_id: Organization ID
            query: User query
            context: Optional context
            max_steps: Maximum execution steps

        Returns:
            Created RouterJob
        """
        job = RouterJob(
            org_id=org_id,
            query=query,
            context=context or {},
            max_steps=max_steps,
            status=RouterJobStatus.PENDING,
        )

        # Store in Redis
        if self._redis:
            job_data = job.model_dump_json()
            job_key = self._job_key(job.job_id)
            await self._redis.setex(job_key, self._job_ttl, job_data)

        logger.info(f"[ROUTER_JOB] Created job {job.job_id}")
        return job

    async def get_job(
        self,
        job_id: str,
        org_id: str | None = None,
    ) -> RouterJob | None:
        """Get job by ID.

        Args:
            job_id: Job ID
            org_id: Optional org ID for verification

        Returns:
            RouterJob or None if not found
        """
        # Try Redis first
        if self._redis:
            job_key = self._job_key(job_id)
            job_data = await self._redis.get(job_key)

            if job_data:
                job = RouterJob.model_validate_json(job_data)
                if org_id and job.org_id != org_id:
                    logger.warning(f"Org mismatch for job {job_id}")
                    return None
                return job

        # Fallback to Supabase
        if self._supabase:
            try:
                query = self._supabase.table("router_jobs").select("*").eq("job_id", job_id)
                if org_id:
                    query = query.eq("org_id", org_id)

                response = query.execute()

                if response.data:
                    return RouterJob.model_validate(response.data[0])
            except Exception as e:
                logger.debug(f"Job {job_id} not found in Supabase: {e}")

        return None

    async def update_job(self, job: RouterJob) -> None:
        """Update job state in Redis.

        Args:
            job: Job to update
        """
        if self._redis:
            job_data = job.model_dump_json()
            job_key = self._job_key(job.job_id)
            await self._redis.setex(job_key, self._job_ttl, job_data)

        logger.debug(f"Updated job {job.job_id} (status={job.status.value})")

    async def persist_to_supabase(self, job: RouterJob) -> None:
        """Persist completed job to Supabase and remove from Redis.

        Args:
            job: Job to persist
        """
        if not self._supabase:
            logger.warning("Supabase not configured, skipping persistence")
            return

        try:
            # Convert to dict for Supabase
            job_dict = job.model_dump(mode="json")

            # Upsert to Supabase
            self._supabase.table("router_jobs").upsert(
                job_dict, on_conflict="job_id"
            ).execute()

            # Remove from Redis
            if self._redis:
                job_key = self._job_key(job.job_id)
                await self._redis.delete(job_key)

            logger.info(f"Persisted job {job.job_id} to Supabase")

        except Exception as e:
            logger.error(f"Failed to persist job {job.job_id}: {e}")
            raise
