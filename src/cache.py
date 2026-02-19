"""
Response Caching Module

Provides caching for LLM responses to reduce GPU costs and improve latency.
Supports exact match caching with TTL expiration.
"""

import os
import time
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock

logging.basicConfig(level=logging.INFO)


@dataclass
class CacheEntry:
    """A cached response entry"""
    key: str
    response: Any
    created_at: float
    expires_at: float
    hit_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 4),
            "size": self.size,
            "max_size": self.max_size,
        }


class ResponseCache:
    """
    LRU cache for LLM responses with TTL expiration.

    Configure via environment variables:
    - CACHE_ENABLED: Enable/disable caching (default: false)
    - CACHE_TTL_SECONDS: Time to live for cache entries (default: 3600)
    - CACHE_MAX_SIZE: Maximum number of entries (default: 1000)
    - CACHE_SKIP_STREAMING: Don't cache streaming responses (default: true)
    """

    def __init__(self):
        self.enabled = os.getenv("CACHE_ENABLED", "false").lower() == "true"
        self.ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))
        self.skip_streaming = os.getenv("CACHE_SKIP_STREAMING", "true").lower() == "true"

        # LRU cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

        # Statistics
        self._stats = CacheStats(max_size=self.max_size)

        if self.enabled:
            logging.info(f"[CACHE] Response caching enabled (TTL={self.ttl_seconds}s, max_size={self.max_size})")
        else:
            logging.info("[CACHE] Response caching disabled")

    def _generate_key(
        self,
        model: str,
        messages: Any,
        sampling_params: Dict[str, Any]
    ) -> str:
        """Generate a cache key from request parameters"""
        # Create deterministic representation
        key_data = {
            "model": model,
            "messages": messages,
            # Include params that affect output
            "temperature": sampling_params.get("temperature", 1.0),
            "top_p": sampling_params.get("top_p", 1.0),
            "max_tokens": sampling_params.get("max_tokens"),
            "seed": sampling_params.get("seed"),
        }

        # Hash the key data
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        model: str,
        messages: Any,
        sampling_params: Dict[str, Any],
        stream: bool = False
    ) -> Tuple[Optional[Any], bool]:
        """
        Get a cached response if available.

        Args:
            model: Model name
            messages: Input messages/prompt
            sampling_params: Sampling parameters
            stream: Whether this is a streaming request

        Returns:
            (response, is_cache_hit)
        """
        if not self.enabled:
            return None, False

        # Don't cache streaming by default
        if stream and self.skip_streaming:
            return None, False

        key = self._generate_key(model, messages, sampling_params)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None, False

            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.size = len(self._cache)
                return None, False

            # Cache hit - move to end (LRU)
            self._cache.move_to_end(key)
            entry.hit_count += 1
            self._stats.hits += 1

            logging.debug(f"[CACHE] Hit for key {key[:16]}... (hits: {entry.hit_count})")
            return entry.response, True

    def put(
        self,
        model: str,
        messages: Any,
        sampling_params: Dict[str, Any],
        response: Any,
        input_tokens: int = 0,
        output_tokens: int = 0,
        stream: bool = False
    ):
        """
        Cache a response.

        Args:
            model: Model name
            messages: Input messages/prompt
            sampling_params: Sampling parameters
            response: Response to cache
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            stream: Whether this was a streaming request
        """
        if not self.enabled:
            return

        # Don't cache streaming by default
        if stream and self.skip_streaming:
            return

        key = self._generate_key(model, messages, sampling_params)
        now = time.time()

        entry = CacheEntry(
            key=key,
            response=response,
            created_at=now,
            expires_at=now + self.ttl_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )

        with self._lock:
            # Remove oldest if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats.evictions += 1

            self._cache[key] = entry
            self._stats.size = len(self._cache)

        logging.debug(f"[CACHE] Stored key {key[:16]}... (size: {self._stats.size})")

    def invalidate(self, model: Optional[str] = None):
        """
        Invalidate cache entries.

        Args:
            model: If provided, only invalidate entries for this model
        """
        with self._lock:
            if model is None:
                self._cache.clear()
            else:
                keys_to_remove = [
                    k for k, v in self._cache.items()
                    if v.model == model
                ]
                for key in keys_to_remove:
                    del self._cache[key]

            self._stats.size = len(self._cache)

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        self._stats.size = len(self._cache)
        return self._stats

    def cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        with self._lock:
            keys_to_remove = [
                k for k, v in self._cache.items()
                if now > v.expires_at
            ]
            for key in keys_to_remove:
                del self._cache[key]
                self._stats.evictions += 1

            self._stats.size = len(self._cache)


# Global cache instance
_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create the global response cache"""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


def handle_cache_stats_request() -> Dict[str, Any]:
    """Handle /cache/stats request"""
    cache = get_cache()
    stats = cache.get_stats()
    return {
        "enabled": cache.enabled,
        "ttl_seconds": cache.ttl_seconds,
        "max_size": cache.max_size,
        **stats.to_dict()
    }
