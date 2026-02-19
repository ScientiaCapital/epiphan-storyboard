"""
Request Deduplication & Idempotency Module

Prevents duplicate request processing and enables idempotent operations.
Saves costs and improves reliability.
"""

import os
import time
import hashlib
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import OrderedDict

logging.basicConfig(level=logging.INFO)


@dataclass
class CachedResponse:
    """A cached response for deduplication"""
    idempotency_key: str
    request_hash: str
    response: Any
    created_at: float
    expires_at: float
    request_id: str
    user_id: Optional[str] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class DeduplicationStats:
    """Deduplication statistics"""
    total_requests: int = 0
    duplicates_detected: int = 0
    responses_replayed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "duplicates_detected": self.duplicates_detected,
            "responses_replayed": self.responses_replayed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_size": self.cache_size,
        }


class DeduplicationManager:
    """
    Manages request deduplication and idempotency.

    Configure via environment variables:
    - DEDUP_ENABLED: Enable deduplication (default: true)
    - DEDUP_TTL_SECONDS: Time to keep responses (default: 3600)
    - DEDUP_MAX_SIZE: Maximum cache size (default: 10000)
    - DEDUP_CHECK_CONTENT: Also check content hash (default: true)
    - DEDUP_CLEANUP_INTERVAL: Cleanup interval in seconds (default: 300)
    """

    def __init__(self):
        self.enabled = os.getenv("DEDUP_ENABLED", "true").lower() == "true"
        self.ttl_seconds = int(os.getenv("DEDUP_TTL_SECONDS", "3600"))
        self.max_size = int(os.getenv("DEDUP_MAX_SIZE", "10000"))
        self.check_content = os.getenv("DEDUP_CHECK_CONTENT", "true").lower() == "true"
        self.cleanup_interval = int(os.getenv("DEDUP_CLEANUP_INTERVAL", "300"))

        # Cache storage
        self._by_idempotency_key: Dict[str, CachedResponse] = {}
        self._by_content_hash: Dict[str, CachedResponse] = {}
        self._in_progress: Dict[str, asyncio.Event] = {}  # For concurrent dedup
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = DeduplicationStats()

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        if self.enabled:
            logging.info(f"[DEDUP] Deduplication enabled (TTL={self.ttl_seconds}s, max_size={self.max_size})")

    async def check_duplicate(
        self,
        request_id: str,
        idempotency_key: Optional[str] = None,
        messages: Any = None,
        sampling_params: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Check if this is a duplicate request.

        Args:
            request_id: Request identifier
            idempotency_key: Client-provided idempotency key
            messages: Request messages for content hashing
            sampling_params: Sampling parameters for content hashing
            user_id: User identifier

        Returns:
            (is_duplicate, cached_response, wait_key)
            - If duplicate with response: (True, response, None)
            - If duplicate in progress: (True, None, wait_key)
            - If not duplicate: (False, None, None)
        """
        if not self.enabled:
            return False, None, None

        self._stats.total_requests += 1

        async with self._lock:
            # Check by idempotency key first
            if idempotency_key:
                if idempotency_key in self._by_idempotency_key:
                    cached = self._by_idempotency_key[idempotency_key]
                    if not cached.is_expired():
                        self._stats.duplicates_detected += 1
                        self._stats.cache_hits += 1
                        logging.info(f"[DEDUP] Duplicate detected by idempotency key: {idempotency_key}")
                        return True, cached.response, None

                # Check if in progress
                if idempotency_key in self._in_progress:
                    self._stats.duplicates_detected += 1
                    logging.info(f"[DEDUP] Request in progress for key: {idempotency_key}")
                    return True, None, idempotency_key

            # Check by content hash
            content_hash = None
            if self.check_content and messages:
                content_hash = self._compute_hash(messages, sampling_params, user_id)

                if content_hash in self._by_content_hash:
                    cached = self._by_content_hash[content_hash]
                    if not cached.is_expired():
                        self._stats.duplicates_detected += 1
                        self._stats.cache_hits += 1
                        logging.info(f"[DEDUP] Duplicate detected by content hash")
                        return True, cached.response, None

                # Check if in progress
                if content_hash in self._in_progress:
                    self._stats.duplicates_detected += 1
                    logging.info(f"[DEDUP] Request in progress for content hash")
                    return True, None, content_hash

            # Not a duplicate - mark as in progress
            key = idempotency_key or content_hash or request_id
            self._in_progress[key] = asyncio.Event()
            self._stats.cache_misses += 1

            # Start cleanup task if not running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            return False, None, None

    async def wait_for_duplicate(self, wait_key: str, timeout: float = 30.0) -> Optional[Any]:
        """
        Wait for a duplicate request to complete.

        Args:
            wait_key: Key from check_duplicate
            timeout: Maximum time to wait

        Returns:
            Cached response if available, None on timeout
        """
        if wait_key not in self._in_progress:
            return None

        try:
            event = self._in_progress[wait_key]
            await asyncio.wait_for(event.wait(), timeout=timeout)

            # Get the response
            async with self._lock:
                if wait_key in self._by_idempotency_key:
                    self._stats.responses_replayed += 1
                    return self._by_idempotency_key[wait_key].response
                if wait_key in self._by_content_hash:
                    self._stats.responses_replayed += 1
                    return self._by_content_hash[wait_key].response

        except asyncio.TimeoutError:
            logging.warning(f"[DEDUP] Timeout waiting for duplicate: {wait_key}")

        return None

    async def store_response(
        self,
        request_id: str,
        response: Any,
        idempotency_key: Optional[str] = None,
        messages: Any = None,
        sampling_params: Optional[Dict] = None,
        user_id: Optional[str] = None
    ):
        """
        Store a response for future deduplication.

        Args:
            request_id: Request identifier
            response: Response to cache
            idempotency_key: Client-provided idempotency key
            messages: Request messages
            sampling_params: Sampling parameters
            user_id: User identifier
        """
        if not self.enabled:
            return

        content_hash = ""
        if self.check_content and messages:
            content_hash = self._compute_hash(messages, sampling_params, user_id)

        now = time.time()
        cached = CachedResponse(
            idempotency_key=idempotency_key or "",
            request_hash=content_hash,
            response=response,
            created_at=now,
            expires_at=now + self.ttl_seconds,
            request_id=request_id,
            user_id=user_id,
        )

        async with self._lock:
            # Enforce max size
            await self._enforce_max_size()

            # Store by idempotency key
            if idempotency_key:
                self._by_idempotency_key[idempotency_key] = cached

                # Signal waiting requests
                if idempotency_key in self._in_progress:
                    self._in_progress[idempotency_key].set()
                    del self._in_progress[idempotency_key]

            # Store by content hash
            if content_hash:
                self._by_content_hash[content_hash] = cached

                # Signal waiting requests
                if content_hash in self._in_progress:
                    self._in_progress[content_hash].set()
                    del self._in_progress[content_hash]

            # Clean up in-progress marker
            if request_id in self._in_progress:
                self._in_progress[request_id].set()
                del self._in_progress[request_id]

            self._stats.cache_size = len(self._by_idempotency_key) + len(self._by_content_hash)

    async def cancel_in_progress(self, request_id: str, idempotency_key: Optional[str] = None):
        """Cancel an in-progress request (on error)"""
        async with self._lock:
            for key in [idempotency_key, request_id]:
                if key and key in self._in_progress:
                    self._in_progress[key].set()
                    del self._in_progress[key]

    def _compute_hash(
        self,
        messages: Any,
        sampling_params: Optional[Dict],
        user_id: Optional[str]
    ) -> str:
        """Compute a hash for request content"""
        content = {
            "messages": messages,
            "sampling_params": sampling_params or {},
            "user_id": user_id,
        }
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:32]

    async def _enforce_max_size(self):
        """Remove oldest entries if over max size"""
        total_size = len(self._by_idempotency_key) + len(self._by_content_hash)

        if total_size >= self.max_size:
            # Remove oldest from each cache
            if self._by_idempotency_key:
                oldest_key = min(
                    self._by_idempotency_key.keys(),
                    key=lambda k: self._by_idempotency_key[k].created_at
                )
                del self._by_idempotency_key[oldest_key]

            if self._by_content_hash and total_size > self.max_size:
                oldest_key = min(
                    self._by_content_hash.keys(),
                    key=lambda k: self._by_content_hash[k].created_at
                )
                del self._by_content_hash[oldest_key]

    async def _cleanup_loop(self):
        """Background task to clean up expired entries"""
        while True:
            await asyncio.sleep(self.cleanup_interval)

            async with self._lock:
                now = time.time()

                # Clean idempotency key cache
                expired_keys = [
                    k for k, v in self._by_idempotency_key.items()
                    if v.is_expired()
                ]
                for key in expired_keys:
                    del self._by_idempotency_key[key]

                # Clean content hash cache
                expired_hashes = [
                    k for k, v in self._by_content_hash.items()
                    if v.is_expired()
                ]
                for key in expired_hashes:
                    del self._by_content_hash[key]

                self._stats.cache_size = len(self._by_idempotency_key) + len(self._by_content_hash)

                if expired_keys or expired_hashes:
                    logging.debug(f"[DEDUP] Cleaned up {len(expired_keys) + len(expired_hashes)} expired entries")

    def get_stats(self) -> DeduplicationStats:
        """Get deduplication statistics"""
        self._stats.cache_size = len(self._by_idempotency_key) + len(self._by_content_hash)
        return self._stats

    async def clear(self):
        """Clear all cached responses"""
        async with self._lock:
            self._by_idempotency_key.clear()
            self._by_content_hash.clear()
            self._stats.cache_size = 0


# Global deduplication manager
_dedup_manager: Optional[DeduplicationManager] = None


def get_dedup_manager() -> DeduplicationManager:
    """Get or create the global deduplication manager"""
    global _dedup_manager
    if _dedup_manager is None:
        _dedup_manager = DeduplicationManager()
    return _dedup_manager


def handle_dedup_stats_request() -> Dict[str, Any]:
    """Handle /dedup/stats request"""
    manager = get_dedup_manager()
    stats = manager.get_stats()
    return {
        "enabled": manager.enabled,
        "ttl_seconds": manager.ttl_seconds,
        "max_size": manager.max_size,
        "check_content": manager.check_content,
        **stats.to_dict(),
    }


async def handle_dedup_clear_request() -> Dict[str, Any]:
    """Handle /dedup/clear request"""
    manager = get_dedup_manager()
    await manager.clear()
    return {"cleared": True}
