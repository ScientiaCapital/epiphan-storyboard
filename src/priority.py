"""
Request Priority Queuing Module

Enables tiered pricing by giving premium users faster queue times.
Higher priority requests are processed before lower priority ones.
"""

import os
import time
import asyncio
import logging
import heapq
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import IntEnum

logging.basicConfig(level=logging.INFO)


class PriorityLevel(IntEnum):
    """Priority levels for requests (lower number = higher priority)"""
    CRITICAL = 1    # System/admin requests
    ENTERPRISE = 2  # Enterprise tier
    PRO = 3         # Pro tier
    BASIC = 5       # Basic tier
    FREE = 10       # Free tier

    @classmethod
    def from_tier(cls, tier: str) -> "PriorityLevel":
        """Convert user tier to priority level"""
        tier_map = {
            "enterprise": cls.ENTERPRISE,
            "pro": cls.PRO,
            "basic": cls.BASIC,
            "free": cls.FREE,
        }
        return tier_map.get(tier.lower(), cls.FREE)


@dataclass(order=True)
class PrioritizedRequest:
    """A request with priority for queue ordering"""
    priority: int
    timestamp: float = field(compare=False)
    request_id: str = field(compare=False)
    future: asyncio.Future = field(compare=False, repr=False)

    # Metadata for tracking
    user_id: str = field(default="", compare=False)
    tier: str = field(default="free", compare=False)
    enqueued_at: float = field(default=0.0, compare=False)


@dataclass
class QueueStats:
    """Queue statistics"""
    total_enqueued: int = 0
    total_dequeued: int = 0
    current_size: int = 0
    avg_wait_time_ms: float = 0.0
    max_wait_time_ms: float = 0.0
    by_priority: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "current_size": self.current_size,
            "avg_wait_time_ms": round(self.avg_wait_time_ms, 2),
            "max_wait_time_ms": round(self.max_wait_time_ms, 2),
            "by_priority": self.by_priority,
        }


class PriorityQueue:
    """
    Priority queue for request scheduling.

    Premium users get processed faster than free tier users.
    Uses a min-heap where lower priority numbers = higher priority.

    Configure via environment variables:
    - PRIORITY_QUEUE_ENABLED: Enable/disable priority queuing (default: false)
    - PRIORITY_QUEUE_MAX_SIZE: Maximum queue size (default: 1000)
    - PRIORITY_BOOST_WAIT_MS: Boost priority after waiting this long (default: 30000)
    """

    def __init__(self):
        self.enabled = os.getenv("PRIORITY_QUEUE_ENABLED", "false").lower() == "true"
        self.max_size = int(os.getenv("PRIORITY_QUEUE_MAX_SIZE", "1000"))
        self.boost_wait_ms = int(os.getenv("PRIORITY_BOOST_WAIT_MS", "30000"))

        # Priority queue (min-heap)
        self._queue: List[PrioritizedRequest] = []
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = QueueStats()
        self._wait_times: List[float] = []

        if self.enabled:
            logging.info(f"[PRIORITY] Priority queuing enabled (max_size={self.max_size})")
        else:
            logging.info("[PRIORITY] Priority queuing disabled")

    async def enqueue(
        self,
        request_id: str,
        priority: int = PriorityLevel.FREE,
        user_id: str = "",
        tier: str = "free"
    ) -> asyncio.Future:
        """
        Add a request to the queue.

        Args:
            request_id: Unique request identifier
            priority: Priority level (lower = higher priority)
            user_id: User ID for tracking
            tier: User tier name

        Returns:
            Future that resolves when request can be processed
        """
        if not self.enabled:
            # Return immediately resolved future if queuing disabled
            future = asyncio.get_event_loop().create_future()
            future.set_result(True)
            return future

        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise QueueFullError(f"Queue is full (max_size={self.max_size})")

            future = asyncio.get_event_loop().create_future()
            now = time.time()

            request = PrioritizedRequest(
                priority=priority,
                timestamp=now,
                request_id=request_id,
                future=future,
                user_id=user_id,
                tier=tier,
                enqueued_at=now,
            )

            heapq.heappush(self._queue, request)

            # Update stats
            self._stats.total_enqueued += 1
            self._stats.current_size = len(self._queue)
            priority_name = self._get_priority_name(priority)
            self._stats.by_priority[priority_name] = self._stats.by_priority.get(priority_name, 0) + 1

            logging.debug(f"[PRIORITY] Enqueued {request_id} with priority {priority} ({tier})")

            return future

    async def dequeue(self) -> Optional[PrioritizedRequest]:
        """
        Get the highest priority request from the queue.

        Returns:
            The highest priority request, or None if queue is empty
        """
        if not self.enabled:
            return None

        async with self._lock:
            if not self._queue:
                return None

            # Apply priority boost to long-waiting requests
            self._apply_priority_boost()

            # Get highest priority request
            request = heapq.heappop(self._queue)

            # Calculate wait time
            wait_time_ms = (time.time() - request.enqueued_at) * 1000
            self._wait_times.append(wait_time_ms)

            # Keep only last 1000 wait times for averaging
            if len(self._wait_times) > 1000:
                self._wait_times = self._wait_times[-1000:]

            # Update stats
            self._stats.total_dequeued += 1
            self._stats.current_size = len(self._queue)
            self._stats.avg_wait_time_ms = sum(self._wait_times) / len(self._wait_times)
            self._stats.max_wait_time_ms = max(self._stats.max_wait_time_ms, wait_time_ms)

            priority_name = self._get_priority_name(request.priority)
            if priority_name in self._stats.by_priority:
                self._stats.by_priority[priority_name] = max(0, self._stats.by_priority[priority_name] - 1)

            # Signal the future
            if not request.future.done():
                request.future.set_result(True)

            logging.debug(f"[PRIORITY] Dequeued {request.request_id} after {wait_time_ms:.0f}ms wait")

            return request

    def _apply_priority_boost(self):
        """Boost priority of requests that have been waiting too long"""
        if not self.boost_wait_ms:
            return

        now = time.time()
        boost_threshold = self.boost_wait_ms / 1000

        # Rebuild queue with boosted priorities
        new_queue = []
        for request in self._queue:
            wait_time = now - request.enqueued_at
            if wait_time > boost_threshold and request.priority > PriorityLevel.ENTERPRISE:
                # Boost by 1 level for each boost_wait_ms waited
                boost_levels = int(wait_time / boost_threshold)
                boosted_priority = max(PriorityLevel.ENTERPRISE, request.priority - boost_levels)
                request.priority = boosted_priority
            new_queue.append(request)

        # Rebuild heap
        heapq.heapify(new_queue)
        self._queue = new_queue

    def _get_priority_name(self, priority: int) -> str:
        """Get human-readable priority name"""
        for level in PriorityLevel:
            if level.value == priority:
                return level.name.lower()
        return f"priority_{priority}"

    def get_position(self, request_id: str) -> Optional[int]:
        """Get queue position for a request (1-indexed)"""
        for i, request in enumerate(sorted(self._queue)):
            if request.request_id == request_id:
                return i + 1
        return None

    def get_stats(self) -> QueueStats:
        """Get queue statistics"""
        self._stats.current_size = len(self._queue)
        return self._stats

    async def cancel(self, request_id: str) -> bool:
        """Cancel a queued request"""
        async with self._lock:
            for i, request in enumerate(self._queue):
                if request.request_id == request_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)

                    if not request.future.done():
                        request.future.cancel()

                    self._stats.current_size = len(self._queue)
                    return True
        return False


class QueueFullError(Exception):
    """Raised when the priority queue is full"""
    pass


# Global priority queue instance
_queue: Optional[PriorityQueue] = None


def get_priority_queue() -> PriorityQueue:
    """Get or create the global priority queue"""
    global _queue
    if _queue is None:
        _queue = PriorityQueue()
    return _queue


def handle_queue_stats_request() -> Dict[str, Any]:
    """Handle /queue/stats request"""
    queue = get_priority_queue()
    stats = queue.get_stats()
    return {
        "enabled": queue.enabled,
        "max_size": queue.max_size,
        **stats.to_dict()
    }


def handle_queue_position_request(request_id: str) -> Dict[str, Any]:
    """Handle /queue/position request"""
    queue = get_priority_queue()
    position = queue.get_position(request_id)
    return {
        "request_id": request_id,
        "position": position,
        "queue_size": queue.get_stats().current_size,
    }
