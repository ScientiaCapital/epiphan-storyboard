"""
Webhooks & Event Streaming Module

Enables real-time event notifications to external systems.
Supports subscriptions, filtering, and reliable delivery via DLQ.
"""

import os
import time
import asyncio
import logging
import json
import hashlib
import hmac
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logging.basicConfig(level=logging.INFO)


class EventType(Enum):
    """Types of events that can be subscribed to"""
    # Request lifecycle
    REQUEST_START = "request.start"
    REQUEST_COMPLETE = "request.complete"
    REQUEST_ERROR = "request.error"

    # Authentication
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"

    # Quota
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"

    # System
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_DEGRADED = "health.degraded"

    # Cache
    CACHE_HIT = "cache.hit"
    CACHE_EVICTION = "cache.eviction"


@dataclass
class WebhookSubscription:
    """A webhook subscription"""
    id: str
    url: str
    events: List[str]  # Event types to subscribe to
    secret: Optional[str] = None  # For signature verification

    # Filtering
    user_ids: List[str] = field(default_factory=list)
    tiers: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)

    # State
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Statistics
    total_sent: int = 0
    total_failed: int = 0
    last_sent_at: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "user_ids": self.user_ids,
            "tiers": self.tiers,
            "models": self.models,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "stats": {
                "total_sent": self.total_sent,
                "total_failed": self.total_failed,
                "last_sent_at": self.last_sent_at,
                "last_error": self.last_error,
            }
        }


@dataclass
class Event:
    """An event to be sent to webhooks"""
    id: str
    type: str
    timestamp: str
    data: Dict[str, Any]

    # Context for filtering
    user_id: Optional[str] = None
    tier: Optional[str] = None
    model: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "data": self.data,
            "user_id": self.user_id,
            "tier": self.tier,
            "model": self.model,
            "request_id": self.request_id,
        }


@dataclass
class WebhookStats:
    """Webhook manager statistics"""
    total_events: int = 0
    total_sent: int = 0
    total_failed: int = 0
    active_subscriptions: int = 0
    by_event_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "active_subscriptions": self.active_subscriptions,
            "by_event_type": self.by_event_type,
        }


class WebhookManager:
    """
    Manages webhook subscriptions and event delivery.

    Configure via environment variables:
    - WEBHOOKS_ENABLED: Enable webhooks (default: true)
    - WEBHOOKS_MAX_SUBSCRIPTIONS: Max subscriptions (default: 100)
    - WEBHOOKS_BATCH_SIZE: Events per batch (default: 10)
    - WEBHOOKS_FLUSH_INTERVAL: Seconds between flushes (default: 5)
    - WEBHOOKS_SIGNING_KEY: Key for signing payloads (default: none)
    """

    def __init__(self):
        self.enabled = os.getenv("WEBHOOKS_ENABLED", "true").lower() == "true"
        self.max_subscriptions = int(os.getenv("WEBHOOKS_MAX_SUBSCRIPTIONS", "100"))
        self.batch_size = int(os.getenv("WEBHOOKS_BATCH_SIZE", "10"))
        self.flush_interval = int(os.getenv("WEBHOOKS_FLUSH_INTERVAL", "5"))
        self.signing_key = os.getenv("WEBHOOKS_SIGNING_KEY")

        # Subscriptions
        self._subscriptions: Dict[str, WebhookSubscription] = {}
        self._lock = asyncio.Lock()

        # Event buffer
        self._event_buffer: List[Event] = []
        self._buffer_lock = asyncio.Lock()

        # Statistics
        self._stats = WebhookStats()

        # Background flush task
        self._flush_task: Optional[asyncio.Task] = None

        if self.enabled:
            logging.info(f"[WEBHOOKS] Webhook manager enabled "
                        f"(batch_size={self.batch_size}, flush_interval={self.flush_interval}s)")

    async def subscribe(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
        tiers: Optional[List[str]] = None,
        models: Optional[List[str]] = None
    ) -> WebhookSubscription:
        """
        Create a webhook subscription.

        Args:
            url: Webhook URL
            events: List of event types to subscribe to
            secret: Secret for signature verification
            user_ids: Filter to specific users
            tiers: Filter to specific tiers
            models: Filter to specific models

        Returns:
            Created subscription
        """
        async with self._lock:
            if len(self._subscriptions) >= self.max_subscriptions:
                raise MaxSubscriptionsError(f"Maximum subscriptions reached ({self.max_subscriptions})")

            sub_id = f"sub_{int(time.time() * 1000)}"
            subscription = WebhookSubscription(
                id=sub_id,
                url=url,
                events=events,
                secret=secret,
                user_ids=user_ids or [],
                tiers=tiers or [],
                models=models or [],
            )

            self._subscriptions[sub_id] = subscription
            self._stats.active_subscriptions = len(self._subscriptions)

            logging.info(f"[WEBHOOKS] Created subscription {sub_id} for {len(events)} events")
            return subscription

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription"""
        async with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                self._stats.active_subscriptions = len(self._subscriptions)
                logging.info(f"[WEBHOOKS] Removed subscription {subscription_id}")
                return True
            return False

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        tier: Optional[str] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """
        Emit an event to matching webhooks.

        Args:
            event_type: Type of event
            data: Event data
            user_id: User context for filtering
            tier: User tier for filtering
            model: Model for filtering
            request_id: Request ID for correlation
        """
        if not self.enabled:
            return

        event = Event(
            id=f"evt_{int(time.time() * 1000000)}",
            type=event_type.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
            user_id=user_id,
            tier=tier,
            model=model,
            request_id=request_id,
        )

        async with self._buffer_lock:
            self._event_buffer.append(event)
            self._stats.total_events += 1
            self._stats.by_event_type[event_type.value] = \
                self._stats.by_event_type.get(event_type.value, 0) + 1

            # Check if we should flush
            if len(self._event_buffer) >= self.batch_size:
                await self._flush()

            # Start flush task if not running
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self):
        """Background task to periodically flush events"""
        while True:
            await asyncio.sleep(self.flush_interval)
            async with self._buffer_lock:
                if self._event_buffer:
                    await self._flush()

    async def _flush(self):
        """Flush buffered events to webhooks"""
        if not self._event_buffer:
            return

        events = self._event_buffer.copy()
        self._event_buffer = []

        # Get DLQ sender for reliable delivery
        try:
            from dlq import get_webhook_sender
            sender = get_webhook_sender()
        except ImportError:
            sender = None

        # Send to each matching subscription
        for sub in self._subscriptions.values():
            if not sub.enabled:
                continue

            # Filter events for this subscription
            matching_events = [
                e for e in events
                if self._matches_subscription(e, sub)
            ]

            if not matching_events:
                continue

            # Build payload
            payload = {
                "subscription_id": sub.id,
                "events": [e.to_dict() for e in matching_events],
                "count": len(matching_events),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

            # Add signature if configured
            headers = {"Content-Type": "application/json"}
            if sub.secret or self.signing_key:
                signature = self._sign_payload(payload, sub.secret or self.signing_key)
                headers["X-Webhook-Signature"] = signature

            # Send via DLQ for reliability
            try:
                if sender:
                    success = await sender.send(
                        url=sub.url,
                        payload=payload,
                        headers=headers,
                        message_id=f"webhook_{sub.id}_{int(time.time() * 1000)}"
                    )
                else:
                    # Fallback to direct send
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            sub.url,
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            success = response.status < 400

                if success:
                    sub.total_sent += len(matching_events)
                    sub.last_sent_at = datetime.now(timezone.utc).isoformat()
                    self._stats.total_sent += len(matching_events)
                else:
                    sub.total_failed += len(matching_events)
                    self._stats.total_failed += len(matching_events)

            except Exception as e:
                sub.total_failed += len(matching_events)
                sub.last_error = str(e)
                self._stats.total_failed += len(matching_events)
                logging.error(f"[WEBHOOKS] Failed to send to {sub.url}: {e}")

    def _matches_subscription(self, event: Event, sub: WebhookSubscription) -> bool:
        """Check if an event matches a subscription's filters"""
        # Check event type
        if event.type not in sub.events and "*" not in sub.events:
            return False

        # Check user filter
        if sub.user_ids and event.user_id not in sub.user_ids:
            return False

        # Check tier filter
        if sub.tiers and event.tier not in sub.tiers:
            return False

        # Check model filter
        if sub.models and event.model not in sub.models:
            return False

        return True

    def _sign_payload(self, payload: Dict[str, Any], secret: str) -> str:
        """Sign a payload with HMAC-SHA256"""
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions"""
        return [s.to_dict() for s in self._subscriptions.values()]

    def get_stats(self) -> WebhookStats:
        """Get webhook statistics"""
        self._stats.active_subscriptions = len(self._subscriptions)
        return self._stats

    async def flush_now(self):
        """Force immediate flush of buffered events"""
        async with self._buffer_lock:
            await self._flush()


class MaxSubscriptionsError(Exception):
    """Raised when maximum subscriptions reached"""
    pass


# Global webhook manager
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get or create the global webhook manager"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


def handle_webhooks_stats_request() -> Dict[str, Any]:
    """Handle /webhooks/stats request"""
    manager = get_webhook_manager()
    stats = manager.get_stats()
    return {
        "enabled": manager.enabled,
        "max_subscriptions": manager.max_subscriptions,
        "batch_size": manager.batch_size,
        **stats.to_dict(),
    }


def handle_webhooks_list_request() -> Dict[str, Any]:
    """Handle /webhooks/list request"""
    manager = get_webhook_manager()
    subscriptions = manager.get_subscriptions()
    return {
        "count": len(subscriptions),
        "subscriptions": subscriptions,
    }


async def handle_webhooks_subscribe_request(
    url: str,
    events: List[str],
    secret: Optional[str] = None,
    user_ids: Optional[List[str]] = None,
    tiers: Optional[List[str]] = None,
    models: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Handle /webhooks/subscribe request"""
    manager = get_webhook_manager()
    subscription = await manager.subscribe(
        url=url,
        events=events,
        secret=secret,
        user_ids=user_ids,
        tiers=tiers,
        models=models,
    )
    return subscription.to_dict()


async def handle_webhooks_unsubscribe_request(subscription_id: str) -> Dict[str, Any]:
    """Handle /webhooks/unsubscribe request"""
    manager = get_webhook_manager()
    success = await manager.unsubscribe(subscription_id)
    return {
        "subscription_id": subscription_id,
        "unsubscribed": success,
    }
