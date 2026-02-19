"""
Usage Metering Module for Enterprise Billing

Tracks token usage, calculates costs, and sends usage data to webhooks
for billing integration (Stripe, custom APIs, etc.)
"""

import os
import json
import time
import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from dlq import get_webhook_sender

logging.basicConfig(level=logging.INFO)

# Default pricing per 1K tokens (in USD) - can be overridden via env vars
DEFAULT_PRICING = {
    "input": 0.0001,   # $0.10 per 1M input tokens
    "output": 0.0003,  # $0.30 per 1M output tokens
}


@dataclass
class UsageRecord:
    """Record of a single API request for billing purposes"""
    # Request identification
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Model info
    model: str = ""
    model_type: str = "chat"  # "chat" or "completion"

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Cost estimation (USD)
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0

    # Performance metrics
    latency_ms: float = 0.0
    time_to_first_token_ms: float = 0.0
    tokens_per_second: float = 0.0

    # Request metadata
    stream: bool = False
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Custom metadata for billing
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    api_key_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class UsageMeter:
    """
    Tracks and reports usage metrics for billing purposes.

    Configure via environment variables:
    - METERING_WEBHOOK_URL: URL to send usage data (required for billing)
    - METERING_WEBHOOK_AUTH: Authorization header value for webhook
    - METERING_PRICE_INPUT: Price per 1K input tokens (default: 0.0001)
    - METERING_PRICE_OUTPUT: Price per 1K output tokens (default: 0.0003)
    - METERING_ENABLED: Enable/disable metering (default: true)
    - METERING_BATCH_SIZE: Number of records to batch before sending (default: 1)
    - METERING_FLUSH_INTERVAL: Seconds between batch flushes (default: 60)
    """

    def __init__(self):
        self.enabled = os.getenv("METERING_ENABLED", "true").lower() == "true"
        self.webhook_url = os.getenv("METERING_WEBHOOK_URL", "")
        self.webhook_auth = os.getenv("METERING_WEBHOOK_AUTH", "")

        # Pricing configuration
        self.price_input = float(os.getenv("METERING_PRICE_INPUT", DEFAULT_PRICING["input"]))
        self.price_output = float(os.getenv("METERING_PRICE_OUTPUT", DEFAULT_PRICING["output"]))

        # Batching configuration
        self.batch_size = int(os.getenv("METERING_BATCH_SIZE", "1"))
        self.flush_interval = int(os.getenv("METERING_FLUSH_INTERVAL", "60"))

        # Internal state
        self._pending_records: list[UsageRecord] = []
        self._last_flush = time.time()
        self._lock = asyncio.Lock()

        if self.enabled and not self.webhook_url:
            logging.warning("METERING_ENABLED=true but METERING_WEBHOOK_URL not set. Usage will be logged but not sent.")

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
        """Calculate costs based on token usage"""
        input_cost = (input_tokens / 1000) * self.price_input
        output_cost = (output_tokens / 1000) * self.price_output
        total_cost = input_cost + output_cost
        return input_cost, output_cost, total_cost

    def create_record(
        self,
        request_id: str,
        model: str = "",
        model_type: str = "chat",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        time_to_first_token_ms: float = 0.0,
        stream: bool = False,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
    ) -> UsageRecord:
        """Create a usage record with cost calculations"""
        input_cost, output_cost, total_cost = self.calculate_cost(input_tokens, output_tokens)

        # Calculate tokens per second
        tokens_per_second = 0.0
        if latency_ms > 0 and output_tokens > 0:
            tokens_per_second = output_tokens / (latency_ms / 1000)

        return UsageRecord(
            request_id=request_id,
            model=model,
            model_type=model_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost=round(input_cost, 8),
            output_cost=round(output_cost, 8),
            total_cost=round(total_cost, 8),
            latency_ms=round(latency_ms, 2),
            time_to_first_token_ms=round(time_to_first_token_ms, 2),
            tokens_per_second=round(tokens_per_second, 2),
            stream=stream,
            success=success,
            error_code=error_code,
            error_message=error_message,
            user_id=user_id,
            organization_id=organization_id,
            api_key_id=api_key_id,
        )

    async def record_usage(self, record: UsageRecord):
        """Record usage and send to webhook if configured"""
        if not self.enabled:
            return

        # Log usage locally
        logging.info(f"[USAGE] request_id={record.request_id} model={record.model} "
                    f"tokens={record.total_tokens} cost=${record.total_cost:.6f} "
                    f"latency={record.latency_ms}ms success={record.success}")

        # Add to pending batch
        async with self._lock:
            self._pending_records.append(record)

            # Check if we should flush
            should_flush = (
                len(self._pending_records) >= self.batch_size or
                time.time() - self._last_flush >= self.flush_interval
            )

            if should_flush:
                await self._flush_records()

    async def _flush_records(self):
        """Send pending records to webhook"""
        if not self._pending_records:
            return

        if not self.webhook_url:
            # Clear records if no webhook configured
            self._pending_records = []
            self._last_flush = time.time()
            return

        records_to_send = self._pending_records.copy()
        self._pending_records = []
        self._last_flush = time.time()

        # Send asynchronously
        asyncio.create_task(self._send_to_webhook(records_to_send))

    async def _send_to_webhook(self, records: list[UsageRecord]):
        """Send usage records to configured webhook with DLQ retry support"""
        headers = {}
        if self.webhook_auth:
            headers["Authorization"] = self.webhook_auth

        payload = {
            "records": [r.to_dict() for r in records],
            "batch_size": len(records),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        # Use DLQ-enabled webhook sender for automatic retries
        sender = get_webhook_sender()
        message_id = f"usage_{int(time.time() * 1000)}_{len(records)}"

        await sender.send(
            url=self.webhook_url,
            payload=payload,
            headers=headers,
            message_id=message_id
        )

        logging.debug(f"[METERING] Queued {len(records)} records for webhook delivery")

    async def flush(self):
        """Force flush any pending records"""
        async with self._lock:
            await self._flush_records()


class RequestTimer:
    """Context manager for timing requests"""

    def __init__(self):
        self.start_time: float = 0
        self.first_token_time: Optional[float] = None
        self.end_time: float = 0

    def start(self):
        self.start_time = time.time()
        return self

    def mark_first_token(self):
        if self.first_token_time is None:
            self.first_token_time = time.time()

    def stop(self):
        self.end_time = time.time()
        return self

    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def time_to_first_token_ms(self) -> float:
        if self.first_token_time is None:
            return 0.0
        return (self.first_token_time - self.start_time) * 1000


# Global meter instance
_meter: Optional[UsageMeter] = None


def get_meter() -> UsageMeter:
    """Get or create the global usage meter"""
    global _meter
    if _meter is None:
        _meter = UsageMeter()
    return _meter
