"""
Circuit Breaker & Retry Logic Module

Prevents cascading failures by detecting unhealthy backends
and automatically recovering when they become healthy again.
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit"""
    state: str = "closed"
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_at: Optional[str] = None
    last_success_at: Optional[str] = None
    opened_at: Optional[str] = None
    half_opened_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_at": self.last_failure_at,
            "last_success_at": self.last_success_at,
            "opened_at": self.opened_at,
            "half_opened_at": self.half_opened_at,
        }


class Circuit:
    """
    Circuit breaker for a single backend/service.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at: float = 0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    async def can_execute(self) -> bool:
        """Check if a request can be executed"""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self._opened_at >= self.recovery_timeout:
                    self._transition_to_half_open()
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """Record a successful request"""
        async with self._lock:
            self._stats.success_count += 1
            self._stats.total_requests += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_at = datetime.now(timezone.utc).isoformat()

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.success_threshold:
                    self._transition_to_closed()

    async def record_failure(self, error: Optional[str] = None):
        """Record a failed request"""
        async with self._lock:
            self._stats.failure_count += 1
            self._stats.total_requests += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_at = datetime.now(timezone.utc).isoformat()

            if self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.failure_threshold:
                    self._transition_to_open()

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens circuit
                self._transition_to_open()

    def _transition_to_open(self):
        """Transition to open state"""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self._stats.state = "open"
        self._stats.opened_at = datetime.now(timezone.utc).isoformat()
        logging.warning(f"[CIRCUIT] {self.name}: Circuit OPENED after {self._stats.consecutive_failures} failures")

    def _transition_to_half_open(self):
        """Transition to half-open state"""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._stats.state = "half_open"
        self._stats.half_opened_at = datetime.now(timezone.utc).isoformat()
        self._stats.consecutive_successes = 0
        logging.info(f"[CIRCUIT] {self.name}: Circuit HALF-OPEN, testing recovery")

    def _transition_to_closed(self):
        """Transition to closed state"""
        self._state = CircuitState.CLOSED
        self._stats.state = "closed"
        self._stats.consecutive_failures = 0
        logging.info(f"[CIRCUIT] {self.name}: Circuit CLOSED, recovered successfully")

    def get_stats(self) -> CircuitStats:
        """Get circuit statistics"""
        self._stats.state = self._state.value
        return self._stats

    async def reset(self):
        """Manually reset the circuit"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._opened_at = 0
            self._half_open_calls = 0
            logging.info(f"[CIRCUIT] {self.name}: Circuit manually reset")


class CircuitBreakerManager:
    """
    Manages circuit breakers for multiple backends.

    Configure via environment variables:
    - CIRCUIT_BREAKER_ENABLED: Enable circuit breakers (default: true)
    - CIRCUIT_FAILURE_THRESHOLD: Failures before opening (default: 5)
    - CIRCUIT_RECOVERY_TIMEOUT: Seconds before trying recovery (default: 30)
    - CIRCUIT_HALF_OPEN_MAX: Max calls in half-open state (default: 3)
    - CIRCUIT_SUCCESS_THRESHOLD: Successes to close circuit (default: 2)
    """

    def __init__(self):
        self.enabled = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
        self.failure_threshold = int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "5"))
        self.recovery_timeout = float(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "30"))
        self.half_open_max = int(os.getenv("CIRCUIT_HALF_OPEN_MAX", "3"))
        self.success_threshold = int(os.getenv("CIRCUIT_SUCCESS_THRESHOLD", "2"))

        self._circuits: Dict[str, Circuit] = {}
        self._lock = asyncio.Lock()

        if self.enabled:
            logging.info(f"[CIRCUIT] Circuit breaker enabled "
                        f"(threshold={self.failure_threshold}, recovery={self.recovery_timeout}s)")

    async def get_circuit(self, name: str) -> Circuit:
        """Get or create a circuit for a backend"""
        async with self._lock:
            if name not in self._circuits:
                self._circuits[name] = Circuit(
                    name=name,
                    failure_threshold=self.failure_threshold,
                    recovery_timeout=self.recovery_timeout,
                    half_open_max_calls=self.half_open_max,
                    success_threshold=self.success_threshold,
                )
            return self._circuits[name]

    async def execute(
        self,
        name: str,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            name: Circuit name
            func: Async function to execute
            fallback: Fallback function if circuit is open
            *args, **kwargs: Arguments for the function

        Returns:
            Function result or fallback result

        Raises:
            CircuitOpenError: If circuit is open and no fallback
        """
        if not self.enabled:
            return await func(*args, **kwargs)

        circuit = await self.get_circuit(name)

        if not await circuit.can_execute():
            if fallback:
                return await fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit {name} is open")

        try:
            result = await func(*args, **kwargs)
            await circuit.record_success()
            return result
        except Exception as e:
            await circuit.record_failure(str(e))
            raise

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuits"""
        return {
            name: circuit.get_stats().to_dict()
            for name, circuit in self._circuits.items()
        }

    async def reset_circuit(self, name: str) -> bool:
        """Reset a specific circuit"""
        if name in self._circuits:
            await self._circuits[name].reset()
            return True
        return False

    async def reset_all(self):
        """Reset all circuits"""
        for circuit in self._circuits.values():
            await circuit.reset()


class CircuitOpenError(Exception):
    """Raised when trying to execute through an open circuit"""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    backoff_multiplier: float = 2.0
    retryable_errors: tuple = ("timeout", "connection", "unavailable")


class RetryHandler:
    """
    Handles retry logic with exponential backoff.

    Configure via environment variables:
    - RETRY_ENABLED: Enable retries (default: true)
    - RETRY_MAX_ATTEMPTS: Maximum retry attempts (default: 3)
    - RETRY_INITIAL_DELAY_MS: Initial delay (default: 100)
    - RETRY_MAX_DELAY_MS: Maximum delay (default: 5000)
    - RETRY_BACKOFF_MULTIPLIER: Backoff multiplier (default: 2)
    """

    def __init__(self):
        self.enabled = os.getenv("RETRY_ENABLED", "true").lower() == "true"
        self.config = RetryConfig(
            max_retries=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            initial_delay_ms=int(os.getenv("RETRY_INITIAL_DELAY_MS", "100")),
            max_delay_ms=int(os.getenv("RETRY_MAX_DELAY_MS", "5000")),
            backoff_multiplier=float(os.getenv("RETRY_BACKOFF_MULTIPLIER", "2")),
        )

        # Statistics
        self._total_retries = 0
        self._successful_retries = 0
        self._failed_retries = 0

        if self.enabled:
            logging.info(f"[RETRY] Retry handler enabled "
                        f"(max={self.config.max_retries}, backoff={self.config.backoff_multiplier}x)")

    def _is_retryable(self, error: Exception) -> bool:
        """Check if an error is retryable"""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in self.config.retryable_errors)

    async def execute(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Async function to execute
            config: Optional custom retry config
            *args, **kwargs: Arguments for the function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        if not self.enabled:
            return await func(*args, **kwargs)

        config = config or self.config
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self._successful_retries += 1
                    logging.info(f"[RETRY] Succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e

                if attempt >= config.max_retries:
                    self._failed_retries += 1
                    logging.warning(f"[RETRY] All {config.max_retries + 1} attempts failed")
                    raise

                if not self._is_retryable(e):
                    logging.debug(f"[RETRY] Error not retryable: {e}")
                    raise

                # Calculate delay with exponential backoff
                delay_ms = min(
                    config.initial_delay_ms * (config.backoff_multiplier ** attempt),
                    config.max_delay_ms
                )

                self._total_retries += 1
                logging.warning(f"[RETRY] Attempt {attempt + 1} failed, retrying in {delay_ms}ms: {e}")

                await asyncio.sleep(delay_ms / 1000)

        raise last_exception

    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics"""
        return {
            "enabled": self.enabled,
            "max_retries": self.config.max_retries,
            "total_retries": self._total_retries,
            "successful_retries": self._successful_retries,
            "failed_retries": self._failed_retries,
        }


# Global instances
_circuit_manager: Optional[CircuitBreakerManager] = None
_retry_handler: Optional[RetryHandler] = None


def get_circuit_manager() -> CircuitBreakerManager:
    """Get or create the global circuit breaker manager"""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager


def get_retry_handler() -> RetryHandler:
    """Get or create the global retry handler"""
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = RetryHandler()
    return _retry_handler


def handle_circuit_stats_request() -> Dict[str, Any]:
    """Handle /circuit/stats request"""
    manager = get_circuit_manager()
    return {
        "enabled": manager.enabled,
        "failure_threshold": manager.failure_threshold,
        "recovery_timeout": manager.recovery_timeout,
        "circuits": manager.get_all_stats(),
    }


async def handle_circuit_reset_request(name: Optional[str] = None) -> Dict[str, Any]:
    """Handle /circuit/reset request"""
    manager = get_circuit_manager()

    if name:
        success = await manager.reset_circuit(name)
        return {"circuit": name, "reset": success}
    else:
        await manager.reset_all()
        return {"reset": "all"}


def handle_retry_stats_request() -> Dict[str, Any]:
    """Handle /retry/stats request"""
    handler = get_retry_handler()
    return handler.get_stats()
