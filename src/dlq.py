"""
Dead Letter Queue Module

Handles webhook retry logic with exponential backoff and
stores failed messages in a dead letter queue for later retry.
"""

import os
import time
import asyncio
import logging
import json
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from collections import deque

logging.basicConfig(level=logging.INFO)


@dataclass
class WebhookMessage:
    """A message to be sent to a webhook"""
    id: str
    url: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Retry tracking
    attempts: int = 0
    max_attempts: int = 3
    last_attempt_at: Optional[str] = None
    last_error: Optional[str] = None
    next_retry_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DLQStats:
    """Dead letter queue statistics"""
    total_sent: int = 0
    total_failed: int = 0
    total_retried: int = 0
    total_dead_lettered: int = 0
    dlq_size: int = 0
    pending_retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "total_retried": self.total_retried,
            "total_dead_lettered": self.total_dead_lettered,
            "dlq_size": self.dlq_size,
            "pending_retries": self.pending_retries,
        }


class WebhookSender:
    """
    Webhook sender with retry logic and dead letter queue.

    Configure via environment variables:
    - DLQ_ENABLED: Enable DLQ (default: true when webhook configured)
    - DLQ_MAX_SIZE: Maximum DLQ size (default: 1000)
    - DLQ_MAX_RETRIES: Maximum retry attempts (default: 3)
    - DLQ_INITIAL_DELAY_MS: Initial retry delay (default: 1000)
    - DLQ_MAX_DELAY_MS: Maximum retry delay (default: 60000)
    - DLQ_BACKOFF_MULTIPLIER: Exponential backoff multiplier (default: 2)
    """

    def __init__(self):
        self.enabled = os.getenv("DLQ_ENABLED", "true").lower() == "true"
        self.max_size = int(os.getenv("DLQ_MAX_SIZE", "1000"))
        self.max_retries = int(os.getenv("DLQ_MAX_RETRIES", "3"))
        self.initial_delay_ms = int(os.getenv("DLQ_INITIAL_DELAY_MS", "1000"))
        self.max_delay_ms = int(os.getenv("DLQ_MAX_DELAY_MS", "60000"))
        self.backoff_multiplier = float(os.getenv("DLQ_BACKOFF_MULTIPLIER", "2"))

        # Queues
        self._retry_queue: deque[WebhookMessage] = deque()
        self._dead_letter_queue: deque[WebhookMessage] = deque()
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = DLQStats()

        # Background retry task
        self._retry_task: Optional[asyncio.Task] = None

        if self.enabled:
            logging.info(f"[DLQ] Dead letter queue enabled (max_retries={self.max_retries})")

    async def send(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        message_id: Optional[str] = None
    ) -> bool:
        """
        Send a webhook with retry support.

        Args:
            url: Webhook URL
            payload: JSON payload
            headers: HTTP headers
            message_id: Optional message ID for tracking

        Returns:
            True if sent successfully, False if queued for retry
        """
        if not url:
            return False

        message = WebhookMessage(
            id=message_id or f"msg_{int(time.time() * 1000)}",
            url=url,
            payload=payload,
            headers=headers or {},
            max_attempts=self.max_retries,
        )

        success = await self._send_message(message)

        if success:
            self._stats.total_sent += 1
            return True
        else:
            # Queue for retry
            await self._queue_for_retry(message)
            return False

    async def _send_message(self, message: WebhookMessage) -> bool:
        """Attempt to send a message"""
        message.attempts += 1
        message.last_attempt_at = datetime.now(timezone.utc).isoformat()

        try:
            headers = {
                "Content-Type": "application/json",
                **message.headers
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    message.url,
                    json=message.payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status < 400:
                        logging.debug(f"[DLQ] Sent message {message.id} successfully")
                        return True
                    else:
                        body = await response.text()
                        message.last_error = f"HTTP {response.status}: {body[:200]}"
                        logging.warning(f"[DLQ] Message {message.id} failed: {message.last_error}")
                        return False

        except asyncio.TimeoutError:
            message.last_error = "Request timeout after 30s"
            logging.warning(f"[DLQ] Message {message.id} timed out")
            return False
        except Exception as e:
            message.last_error = str(e)
            logging.warning(f"[DLQ] Message {message.id} error: {e}")
            return False

    async def _queue_for_retry(self, message: WebhookMessage):
        """Queue a message for retry"""
        if not self.enabled:
            self._stats.total_failed += 1
            return

        async with self._lock:
            if message.attempts >= message.max_attempts:
                # Move to dead letter queue
                await self._move_to_dlq(message)
                return

            # Calculate next retry time with exponential backoff
            delay_ms = min(
                self.initial_delay_ms * (self.backoff_multiplier ** (message.attempts - 1)),
                self.max_delay_ms
            )
            message.next_retry_at = time.time() + (delay_ms / 1000)

            self._retry_queue.append(message)
            self._stats.pending_retries = len(self._retry_queue)

            logging.info(f"[DLQ] Queued {message.id} for retry in {delay_ms}ms (attempt {message.attempts}/{message.max_attempts})")

            # Start retry task if not running
            if self._retry_task is None or self._retry_task.done():
                self._retry_task = asyncio.create_task(self._process_retries())

    async def _move_to_dlq(self, message: WebhookMessage):
        """Move a message to the dead letter queue"""
        # Trim DLQ if at capacity
        while len(self._dead_letter_queue) >= self.max_size:
            self._dead_letter_queue.popleft()

        self._dead_letter_queue.append(message)
        self._stats.total_dead_lettered += 1
        self._stats.dlq_size = len(self._dead_letter_queue)

        logging.warning(f"[DLQ] Message {message.id} moved to DLQ after {message.attempts} attempts")

    async def _process_retries(self):
        """Background task to process retry queue"""
        while True:
            await asyncio.sleep(1)  # Check every second

            async with self._lock:
                if not self._retry_queue:
                    break

                now = time.time()
                messages_to_retry = []

                # Find messages ready for retry
                new_queue = deque()
                for message in self._retry_queue:
                    if message.next_retry_at and message.next_retry_at <= now:
                        messages_to_retry.append(message)
                    else:
                        new_queue.append(message)

                self._retry_queue = new_queue
                self._stats.pending_retries = len(self._retry_queue)

            # Retry messages outside lock
            for message in messages_to_retry:
                self._stats.total_retried += 1
                success = await self._send_message(message)

                if success:
                    self._stats.total_sent += 1
                else:
                    await self._queue_for_retry(message)

    def get_dlq_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages from the dead letter queue"""
        messages = list(self._dead_letter_queue)[-limit:]
        return [m.to_dict() for m in messages]

    async def retry_dlq_message(self, message_id: str) -> bool:
        """Retry a specific message from the DLQ"""
        async with self._lock:
            for i, message in enumerate(self._dead_letter_queue):
                if message.id == message_id:
                    # Remove from DLQ
                    del self._dead_letter_queue[i]
                    self._stats.dlq_size = len(self._dead_letter_queue)

                    # Reset retry count and queue
                    message.attempts = 0
                    message.last_error = None

                    # Send immediately
                    success = await self._send_message(message)
                    if success:
                        self._stats.total_sent += 1
                        return True
                    else:
                        await self._queue_for_retry(message)
                        return False

        return False

    async def retry_all_dlq(self) -> int:
        """Retry all messages in the DLQ"""
        async with self._lock:
            messages = list(self._dead_letter_queue)
            self._dead_letter_queue.clear()
            self._stats.dlq_size = 0

        retried = 0
        for message in messages:
            message.attempts = 0
            message.last_error = None
            await self._queue_for_retry(message)
            retried += 1

        return retried

    async def clear_dlq(self) -> int:
        """Clear all messages from the DLQ"""
        async with self._lock:
            count = len(self._dead_letter_queue)
            self._dead_letter_queue.clear()
            self._stats.dlq_size = 0
            return count

    def get_stats(self) -> DLQStats:
        """Get DLQ statistics"""
        self._stats.dlq_size = len(self._dead_letter_queue)
        self._stats.pending_retries = len(self._retry_queue)
        return self._stats


# Global webhook sender
_sender: Optional[WebhookSender] = None


def get_webhook_sender() -> WebhookSender:
    """Get or create the global webhook sender"""
    global _sender
    if _sender is None:
        _sender = WebhookSender()
    return _sender


def handle_dlq_stats_request() -> Dict[str, Any]:
    """Handle /dlq/stats request"""
    sender = get_webhook_sender()
    stats = sender.get_stats()
    return {
        "enabled": sender.enabled,
        "max_retries": sender.max_retries,
        **stats.to_dict()
    }


def handle_dlq_list_request(limit: int = 100) -> Dict[str, Any]:
    """Handle /dlq/list request"""
    sender = get_webhook_sender()
    messages = sender.get_dlq_messages(limit)
    return {
        "count": len(messages),
        "messages": messages
    }


async def handle_dlq_retry_request(message_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle /dlq/retry request"""
    sender = get_webhook_sender()

    if message_id:
        success = await sender.retry_dlq_message(message_id)
        return {
            "message_id": message_id,
            "retried": success
        }
    else:
        count = await sender.retry_all_dlq()
        return {
            "retried_count": count
        }
