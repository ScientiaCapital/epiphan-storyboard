"""
Graceful Shutdown & Request Draining Module

Ensures clean shutdown during deployments with no lost requests.
Handles SIGTERM/SIGINT signals and drains in-flight requests.
"""

import os
import signal
import asyncio
import logging
import time
from typing import Optional, Set, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)


@dataclass
class ShutdownStats:
    """Statistics about shutdown process"""
    shutdown_initiated_at: Optional[str] = None
    shutdown_completed_at: Optional[str] = None
    requests_drained: int = 0
    requests_cancelled: int = 0
    drain_timeout_seconds: int = 0
    graceful: bool = True


class GracefulShutdown:
    """
    Manages graceful shutdown with request draining.

    Configure via environment variables:
    - SHUTDOWN_DRAIN_TIMEOUT: Seconds to wait for requests to drain (default: 30)
    - SHUTDOWN_FORCE_TIMEOUT: Seconds before force kill (default: 60)
    """

    def __init__(self):
        self.drain_timeout = int(os.getenv("SHUTDOWN_DRAIN_TIMEOUT", "30"))
        self.force_timeout = int(os.getenv("SHUTDOWN_FORCE_TIMEOUT", "60"))

        # State
        self._shutting_down = False
        self._active_requests: Set[str] = set()
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

        # Callbacks
        self._pre_shutdown_callbacks: list[Callable] = []
        self._post_drain_callbacks: list[Callable] = []

        # Statistics
        self._stats = ShutdownStats(drain_timeout_seconds=self.drain_timeout)

        # Register signal handlers
        self._setup_signal_handlers()

        logging.info(f"[SHUTDOWN] Graceful shutdown initialized (drain_timeout={self.drain_timeout}s)")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_event_loop()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
            logging.debug("[SHUTDOWN] Signal handlers registered")
        except Exception as e:
            # Signal handlers may not work in all environments
            logging.warning(f"[SHUTDOWN] Could not register signal handlers: {e}")

    async def _handle_signal(self, sig: signal.Signals):
        """Handle shutdown signal"""
        logging.info(f"[SHUTDOWN] Received {sig.name}, initiating graceful shutdown...")
        await self.initiate_shutdown()

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self._shutting_down

    def register_pre_shutdown(self, callback: Callable):
        """Register callback to run before draining starts"""
        self._pre_shutdown_callbacks.append(callback)

    def register_post_drain(self, callback: Callable):
        """Register callback to run after draining completes"""
        self._post_drain_callbacks.append(callback)

    async def register_request(self, request_id: str) -> bool:
        """
        Register a new request.

        Returns:
            True if request accepted, False if shutting down
        """
        async with self._lock:
            if self._shutting_down:
                logging.warning(f"[SHUTDOWN] Rejected request {request_id} - shutting down")
                return False

            self._active_requests.add(request_id)
            logging.debug(f"[SHUTDOWN] Registered request {request_id} (active: {len(self._active_requests)})")
            return True

    async def complete_request(self, request_id: str):
        """Mark a request as completed"""
        async with self._lock:
            self._active_requests.discard(request_id)
            logging.debug(f"[SHUTDOWN] Completed request {request_id} (active: {len(self._active_requests)})")

            # Signal if we're draining and no more requests
            if self._shutting_down and not self._active_requests:
                self._shutdown_event.set()

    async def initiate_shutdown(self):
        """Initiate graceful shutdown"""
        if self._shutting_down:
            return

        self._shutting_down = True
        self._stats.shutdown_initiated_at = datetime.now(timezone.utc).isoformat()

        logging.info(f"[SHUTDOWN] Starting graceful shutdown with {len(self._active_requests)} active requests")

        # Run pre-shutdown callbacks
        for callback in self._pre_shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logging.error(f"[SHUTDOWN] Pre-shutdown callback error: {e}")

        # Wait for requests to drain
        await self._drain_requests()

        # Run post-drain callbacks
        for callback in self._post_drain_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logging.error(f"[SHUTDOWN] Post-drain callback error: {e}")

        self._stats.shutdown_completed_at = datetime.now(timezone.utc).isoformat()
        logging.info(f"[SHUTDOWN] Graceful shutdown complete (drained: {self._stats.requests_drained}, cancelled: {self._stats.requests_cancelled})")

    async def _drain_requests(self):
        """Wait for active requests to complete"""
        if not self._active_requests:
            logging.info("[SHUTDOWN] No active requests to drain")
            return

        start_time = time.time()
        initial_count = len(self._active_requests)

        logging.info(f"[SHUTDOWN] Draining {initial_count} active requests (timeout: {self.drain_timeout}s)...")

        try:
            # Wait for requests to complete or timeout
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self.drain_timeout
            )
            self._stats.requests_drained = initial_count
            logging.info(f"[SHUTDOWN] Successfully drained all {initial_count} requests")

        except asyncio.TimeoutError:
            # Timeout - some requests still active
            remaining = len(self._active_requests)
            self._stats.requests_drained = initial_count - remaining
            self._stats.requests_cancelled = remaining
            self._stats.graceful = False

            logging.warning(f"[SHUTDOWN] Drain timeout after {self.drain_timeout}s, {remaining} requests cancelled")

            # Clear remaining requests
            async with self._lock:
                self._active_requests.clear()

    def get_active_count(self) -> int:
        """Get number of active requests"""
        return len(self._active_requests)

    def get_stats(self) -> ShutdownStats:
        """Get shutdown statistics"""
        return self._stats

    def check_accepting_requests(self) -> bool:
        """Check if worker is accepting new requests"""
        return not self._shutting_down


# Global shutdown manager
_shutdown_manager: Optional[GracefulShutdown] = None


def get_shutdown_manager() -> GracefulShutdown:
    """Get or create the global shutdown manager"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdown()
    return _shutdown_manager


def handle_shutdown_status_request() -> dict:
    """Handle /shutdown/status request"""
    manager = get_shutdown_manager()
    return {
        "accepting_requests": manager.check_accepting_requests(),
        "active_requests": manager.get_active_count(),
        "shutting_down": manager.is_shutting_down,
        "drain_timeout_seconds": manager.drain_timeout,
    }
