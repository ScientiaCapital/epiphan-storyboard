"""
Request Timeout Management Module

Configurable timeouts with graceful cancellation and partial results.
Prevents hanging requests and improves user experience.
"""

import os
import asyncio
import logging
from typing import Optional, AsyncGenerator, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)


@dataclass
class TimeoutConfig:
    """Timeout configuration for a request"""
    total_timeout: float  # Total request timeout in seconds
    first_token_timeout: float  # Timeout for first token
    idle_timeout: float  # Timeout between tokens
    warning_threshold: float  # Warn when this % of timeout used

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        """Create config from environment variables"""
        return cls(
            total_timeout=float(os.getenv("TIMEOUT_TOTAL_SECONDS", "300")),
            first_token_timeout=float(os.getenv("TIMEOUT_FIRST_TOKEN_SECONDS", "60")),
            idle_timeout=float(os.getenv("TIMEOUT_IDLE_SECONDS", "30")),
            warning_threshold=float(os.getenv("TIMEOUT_WARNING_THRESHOLD", "0.8")),
        )


@dataclass
class TimeoutResult:
    """Result of a timeout check"""
    timed_out: bool
    timeout_type: Optional[str] = None  # "total", "first_token", "idle"
    elapsed_seconds: float = 0.0
    message: Optional[str] = None


class TimeoutManager:
    """
    Manages request timeouts with different timeout types.

    Configure via environment variables:
    - TIMEOUT_ENABLED: Enable timeout management (default: true)
    - TIMEOUT_TOTAL_SECONDS: Total request timeout (default: 300)
    - TIMEOUT_FIRST_TOKEN_SECONDS: First token timeout (default: 60)
    - TIMEOUT_IDLE_SECONDS: Idle timeout between tokens (default: 30)
    - TIMEOUT_WARNING_THRESHOLD: Warn at this % of timeout (default: 0.8)
    - TIMEOUT_STREAMING_MULTIPLIER: Multiply timeouts for streaming (default: 2)
    """

    def __init__(self):
        self.enabled = os.getenv("TIMEOUT_ENABLED", "true").lower() == "true"
        self.streaming_multiplier = float(os.getenv("TIMEOUT_STREAMING_MULTIPLIER", "2"))
        self.default_config = TimeoutConfig.from_env()

        if self.enabled:
            logging.info(f"[TIMEOUT] Timeout management enabled "
                        f"(total={self.default_config.total_timeout}s, "
                        f"first_token={self.default_config.first_token_timeout}s)")

    def get_config(self, stream: bool = False, custom_timeout: Optional[float] = None) -> TimeoutConfig:
        """Get timeout configuration, optionally adjusted for streaming"""
        config = TimeoutConfig(
            total_timeout=custom_timeout or self.default_config.total_timeout,
            first_token_timeout=self.default_config.first_token_timeout,
            idle_timeout=self.default_config.idle_timeout,
            warning_threshold=self.default_config.warning_threshold,
        )

        # Streaming requests get longer timeouts
        if stream:
            config.total_timeout *= self.streaming_multiplier
            config.idle_timeout *= self.streaming_multiplier

        return config

    @asynccontextmanager
    async def timeout_context(
        self,
        request_id: str,
        config: Optional[TimeoutConfig] = None
    ):
        """
        Context manager for request timeout tracking.

        Usage:
            async with timeout_manager.timeout_context(request_id) as tracker:
                async for chunk in generator:
                    tracker.mark_activity()
                    yield chunk
        """
        if not self.enabled:
            yield _NoOpTracker()
            return

        config = config or self.default_config
        tracker = TimeoutTracker(request_id, config)

        try:
            yield tracker
        finally:
            tracker.stop()

    async def wrap_generator(
        self,
        request_id: str,
        generator: AsyncGenerator,
        config: Optional[TimeoutConfig] = None,
        on_timeout: Optional[callable] = None
    ) -> AsyncGenerator:
        """
        Wrap an async generator with timeout management.

        Args:
            request_id: Request identifier
            generator: The generator to wrap
            config: Timeout configuration
            on_timeout: Callback when timeout occurs

        Yields:
            Items from the generator with timeout enforcement
        """
        if not self.enabled:
            async for item in generator:
                yield item
            return

        config = config or self.default_config
        tracker = TimeoutTracker(request_id, config)

        try:
            # Wait for first token with specific timeout
            try:
                first_item = await asyncio.wait_for(
                    generator.__anext__(),
                    timeout=config.first_token_timeout
                )
                tracker.mark_first_token()
                yield first_item
            except asyncio.TimeoutError:
                logging.warning(f"[TIMEOUT] Request {request_id} timed out waiting for first token "
                              f"after {config.first_token_timeout}s")
                if on_timeout:
                    await on_timeout("first_token", config.first_token_timeout)
                return
            except StopAsyncIteration:
                return

            # Continue with remaining tokens
            while True:
                try:
                    # Check total timeout
                    remaining = config.total_timeout - tracker.elapsed_seconds
                    if remaining <= 0:
                        logging.warning(f"[TIMEOUT] Request {request_id} exceeded total timeout "
                                      f"of {config.total_timeout}s")
                        if on_timeout:
                            await on_timeout("total", config.total_timeout)
                        return

                    # Check for warning threshold
                    if not tracker.warning_sent and tracker.elapsed_seconds >= config.total_timeout * config.warning_threshold:
                        logging.warning(f"[TIMEOUT] Request {request_id} at {config.warning_threshold*100:.0f}% "
                                      f"of timeout ({tracker.elapsed_seconds:.1f}s / {config.total_timeout}s)")
                        tracker.warning_sent = True

                    # Use minimum of remaining total and idle timeout
                    timeout = min(remaining, config.idle_timeout)

                    item = await asyncio.wait_for(
                        generator.__anext__(),
                        timeout=timeout
                    )
                    tracker.mark_activity()
                    yield item

                except asyncio.TimeoutError:
                    # Determine which timeout was hit
                    if tracker.elapsed_seconds >= config.total_timeout:
                        timeout_type = "total"
                        timeout_value = config.total_timeout
                    else:
                        timeout_type = "idle"
                        timeout_value = config.idle_timeout

                    logging.warning(f"[TIMEOUT] Request {request_id} hit {timeout_type} timeout "
                                  f"after {tracker.elapsed_seconds:.1f}s")
                    if on_timeout:
                        await on_timeout(timeout_type, timeout_value)
                    return

                except StopAsyncIteration:
                    break

        finally:
            tracker.stop()


class TimeoutTracker:
    """Tracks timeout state for a single request"""

    def __init__(self, request_id: str, config: TimeoutConfig):
        self.request_id = request_id
        self.config = config

        import time
        self._start_time = time.time()
        self._last_activity = self._start_time
        self._first_token_time: Optional[float] = None
        self._stopped = False
        self.warning_sent = False

    @property
    def elapsed_seconds(self) -> float:
        """Total elapsed time in seconds"""
        import time
        return time.time() - self._start_time

    @property
    def idle_seconds(self) -> float:
        """Time since last activity in seconds"""
        import time
        return time.time() - self._last_activity

    def mark_activity(self):
        """Mark that activity occurred (token received)"""
        import time
        self._last_activity = time.time()

    def mark_first_token(self):
        """Mark that first token was received"""
        import time
        self._first_token_time = time.time()
        self._last_activity = self._first_token_time

    def stop(self):
        """Stop the tracker"""
        self._stopped = True

    def check_timeout(self) -> TimeoutResult:
        """Check if any timeout has been exceeded"""
        if self._stopped:
            return TimeoutResult(timed_out=False, elapsed_seconds=self.elapsed_seconds)

        # Check total timeout
        if self.elapsed_seconds >= self.config.total_timeout:
            return TimeoutResult(
                timed_out=True,
                timeout_type="total",
                elapsed_seconds=self.elapsed_seconds,
                message=f"Total timeout of {self.config.total_timeout}s exceeded"
            )

        # Check first token timeout
        if self._first_token_time is None:
            if self.elapsed_seconds >= self.config.first_token_timeout:
                return TimeoutResult(
                    timed_out=True,
                    timeout_type="first_token",
                    elapsed_seconds=self.elapsed_seconds,
                    message=f"First token timeout of {self.config.first_token_timeout}s exceeded"
                )

        # Check idle timeout
        if self.idle_seconds >= self.config.idle_timeout:
            return TimeoutResult(
                timed_out=True,
                timeout_type="idle",
                elapsed_seconds=self.elapsed_seconds,
                message=f"Idle timeout of {self.config.idle_timeout}s exceeded"
            )

        return TimeoutResult(timed_out=False, elapsed_seconds=self.elapsed_seconds)


class _NoOpTracker:
    """No-op tracker when timeouts are disabled"""
    def mark_activity(self):
        pass

    def mark_first_token(self):
        pass

    def stop(self):
        pass


# Global timeout manager
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get or create the global timeout manager"""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager
