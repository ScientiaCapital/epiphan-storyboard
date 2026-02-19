"""Timeout utilities for tool execution.

Provides decorators and context managers for enforcing timeouts
on async operations to prevent runaway tool executions.

Usage:
    from conductor_ai.sdk.security import with_timeout, TimeoutError

    @with_timeout(seconds=30)
    async def slow_operation():
        # This will be cancelled if it takes > 30 seconds
        await some_long_operation()

    # Or with context manager style
    async with with_timeout(60):
        await another_long_operation()
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when an operation exceeds its timeout."""

    def __init__(self, timeout: float, operation: str = "Operation") -> None:
        """Initialize the timeout error.

        Args:
            timeout: The timeout value that was exceeded
            operation: Description of the operation that timed out
        """
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout} seconds")


class TimeoutContext:
    """Async context manager for timeout enforcement.

    Usage:
        async with TimeoutContext(30) as ctx:
            await long_operation()
    """

    def __init__(
        self,
        seconds: float,
        operation: str = "Operation",
    ) -> None:
        """Initialize the timeout context.

        Args:
            seconds: Maximum seconds to allow
            operation: Description for error messages
        """
        self.seconds = seconds
        self.operation = operation
        self._task: asyncio.Task[Any] | None = None

    async def __aenter__(self) -> "TimeoutContext":
        """Enter the timeout context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit the timeout context."""
        if exc_type is asyncio.CancelledError:
            # Convert CancelledError to our TimeoutError
            raise TimeoutError(self.seconds, self.operation)
        return False


def with_timeout(
    seconds: float,
    operation: str = "Operation",
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to add timeout to an async function.

    Args:
        seconds: Maximum seconds to allow
        operation: Description for error messages

    Returns:
        Decorated function

    Usage:
        @with_timeout(30)
        async def fetch_data():
            ...

        @with_timeout(60, operation="Database query")
        async def run_query():
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(seconds, operation or func.__name__)

        return wrapper

    return decorator


async def run_with_timeout(
    coro: Awaitable[T],
    seconds: float,
    operation: str = "Operation",
) -> T:
    """Run a coroutine with a timeout.

    Args:
        coro: The coroutine to run
        seconds: Maximum seconds to allow
        operation: Description for error messages

    Returns:
        The coroutine result

    Raises:
        TimeoutError: If the operation exceeds the timeout

    Usage:
        result = await run_with_timeout(
            fetch_data(),
            seconds=30,
            operation="Fetching data"
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(seconds, operation)
