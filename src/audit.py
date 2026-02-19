"""
Audit Logging Module

Provides immutable audit trails for compliance (SOC2, HIPAA, GDPR).
Tracks authentication, data access, and configuration changes.
"""

import os
import json
import time
import hashlib
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from collections import deque

logging.basicConfig(level=logging.INFO)


class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_RATE_LIMITED = "auth.rate_limited"

    # Data access events
    REQUEST_START = "request.start"
    REQUEST_COMPLETE = "request.complete"
    REQUEST_ERROR = "request.error"

    # Cache events
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"

    # Configuration events
    CONFIG_CHANGE = "config.change"
    CONFIG_VALIDATION = "config.validation"

    # System events
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK = "health.check"

    # Admin events
    ADMIN_ACTION = "admin.action"
    DLQ_RETRY = "dlq.retry"
    QUEUE_CANCEL = "queue.cancel"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """An immutable audit event"""
    event_id: str
    event_type: str
    severity: str
    timestamp: str

    # Actor information
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    organization_id: Optional[str] = None
    ip_address: Optional[str] = None

    # Request context
    request_id: Optional[str] = None
    model: Optional[str] = None
    route: Optional[str] = None

    # Event details
    details: Dict[str, Any] = field(default_factory=dict)

    # Integrity
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass
class AuditStats:
    """Audit logging statistics"""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_severity: Dict[str, int] = field(default_factory=dict)
    buffer_size: int = 0
    last_flush_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "events_by_severity": self.events_by_severity,
            "buffer_size": self.buffer_size,
            "last_flush_at": self.last_flush_at,
        }


class AuditLogger:
    """
    Audit logger for compliance and security tracking.

    Configure via environment variables:
    - AUDIT_ENABLED: Enable audit logging (default: true)
    - AUDIT_BUFFER_SIZE: Buffer size before flush (default: 100)
    - AUDIT_FLUSH_INTERVAL: Flush interval in seconds (default: 60)
    - AUDIT_LOG_FILE: File path for audit logs (default: none)
    - AUDIT_WEBHOOK_URL: Webhook URL for SIEM integration (default: none)
    - AUDIT_INCLUDE_HASH: Include integrity hashes (default: true)
    - AUDIT_RETENTION_COUNT: Number of events to keep in memory (default: 10000)
    """

    def __init__(self):
        self.enabled = os.getenv("AUDIT_ENABLED", "true").lower() == "true"
        self.buffer_size = int(os.getenv("AUDIT_BUFFER_SIZE", "100"))
        self.flush_interval = int(os.getenv("AUDIT_FLUSH_INTERVAL", "60"))
        self.log_file = os.getenv("AUDIT_LOG_FILE")
        self.webhook_url = os.getenv("AUDIT_WEBHOOK_URL")
        self.include_hash = os.getenv("AUDIT_INCLUDE_HASH", "true").lower() == "true"
        self.retention_count = int(os.getenv("AUDIT_RETENTION_COUNT", "10000"))

        # Event storage
        self._buffer: List[AuditEvent] = []
        self._events: deque[AuditEvent] = deque(maxlen=self.retention_count)
        self._lock = asyncio.Lock()

        # Hash chain for integrity
        self._last_hash = "genesis"

        # Statistics
        self._stats = AuditStats()

        # Background flush task
        self._flush_task: Optional[asyncio.Task] = None

        if self.enabled:
            logging.info(f"[AUDIT] Audit logging enabled "
                        f"(buffer={self.buffer_size}, flush={self.flush_interval}s)")
            if self.log_file:
                logging.info(f"[AUDIT] Writing to file: {self.log_file}")
            if self.webhook_url:
                logging.info(f"[AUDIT] Webhook configured: {self.webhook_url[:50]}...")

    async def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        model: Optional[str] = None,
        route: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of audit event
            severity: Event severity level
            user_id: User who triggered the event
            api_key_id: API key used
            organization_id: Organization ID
            ip_address: Client IP address
            request_id: Request identifier
            model: Model being used
            route: API route
            details: Additional event details
        """
        if not self.enabled:
            return

        async with self._lock:
            # Generate event ID
            event_id = f"audit_{int(time.time() * 1000000)}"

            # Create event
            event = AuditEvent(
                event_id=event_id,
                event_type=event_type.value,
                severity=severity.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
                user_id=user_id,
                api_key_id=api_key_id,
                organization_id=organization_id,
                ip_address=ip_address,
                request_id=request_id,
                model=model,
                route=route,
                details=details or {},
            )

            # Add integrity hash
            if self.include_hash:
                event.previous_hash = self._last_hash
                event.event_hash = self._compute_hash(event)
                self._last_hash = event.event_hash

            # Add to buffer and storage
            self._buffer.append(event)
            self._events.append(event)

            # Update statistics
            self._stats.total_events += 1
            self._stats.events_by_type[event_type.value] = \
                self._stats.events_by_type.get(event_type.value, 0) + 1
            self._stats.events_by_severity[severity.value] = \
                self._stats.events_by_severity.get(severity.value, 0) + 1
            self._stats.buffer_size = len(self._buffer)

            # Check if we need to flush
            if len(self._buffer) >= self.buffer_size:
                await self._flush()

            # Start background flush task if not running
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._background_flush())

    def _compute_hash(self, event: AuditEvent) -> str:
        """Compute integrity hash for an event"""
        # Create hash input (exclude the hash fields themselves)
        hash_input = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "severity": event.severity,
            "timestamp": event.timestamp,
            "user_id": event.user_id,
            "request_id": event.request_id,
            "details": event.details,
            "previous_hash": event.previous_hash,
        }

        hash_string = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]

    async def _background_flush(self):
        """Background task to periodically flush events"""
        while True:
            await asyncio.sleep(self.flush_interval)
            async with self._lock:
                if self._buffer:
                    await self._flush()

    async def _flush(self):
        """Flush buffered events to storage"""
        if not self._buffer:
            return

        events_to_flush = self._buffer.copy()
        self._buffer = []
        self._stats.buffer_size = 0
        self._stats.last_flush_at = datetime.now(timezone.utc).isoformat()

        # Write to file
        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    for event in events_to_flush:
                        f.write(event.to_json() + "\n")
            except Exception as e:
                logging.error(f"[AUDIT] Failed to write to file: {e}")

        # Send to webhook
        if self.webhook_url:
            try:
                import aiohttp
                payload = {
                    "events": [e.to_dict() for e in events_to_flush],
                    "count": len(events_to_flush),
                    "flushed_at": datetime.now(timezone.utc).isoformat(),
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status >= 400:
                            logging.warning(f"[AUDIT] Webhook failed: {response.status}")
            except Exception as e:
                logging.error(f"[AUDIT] Failed to send to webhook: {e}")

        logging.debug(f"[AUDIT] Flushed {len(events_to_flush)} events")

    async def flush_now(self):
        """Force immediate flush of buffered events"""
        async with self._lock:
            await self._flush()

    # Convenience methods for common events

    async def log_auth_success(
        self,
        user_id: str,
        api_key_id: str,
        organization_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Log successful authentication"""
        await self.log(
            event_type=AuditEventType.AUTH_SUCCESS,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            api_key_id=api_key_id,
            organization_id=organization_id,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_auth_failure(
        self,
        reason: str,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Log failed authentication"""
        await self.log(
            event_type=AuditEventType.AUTH_FAILURE,
            severity=AuditSeverity.WARNING,
            api_key_id=api_key_id,
            ip_address=ip_address,
            request_id=request_id,
            details={"reason": reason},
        )

    async def log_request_start(
        self,
        request_id: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        model: Optional[str] = None,
        route: Optional[str] = None,
        input_tokens: Optional[int] = None,
    ):
        """Log request start"""
        await self.log(
            event_type=AuditEventType.REQUEST_START,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            model=model,
            route=route,
            details={"input_tokens": input_tokens} if input_tokens else {},
        )

    async def log_request_complete(
        self,
        request_id: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        model: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0,
        success: bool = True,
    ):
        """Log request completion"""
        await self.log(
            event_type=AuditEventType.REQUEST_COMPLETE,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            model=model,
            details={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "latency_ms": latency_ms,
                "success": success,
            },
        )

    async def log_request_error(
        self,
        request_id: str,
        error_code: str,
        error_message: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Log request error"""
        await self.log(
            event_type=AuditEventType.REQUEST_ERROR,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            model=model,
            details={
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    async def log_system_start(self, model: str, config: Dict[str, Any]):
        """Log system startup"""
        await self.log(
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.INFO,
            model=model,
            details={"config": config},
        )

    async def log_system_shutdown(self, reason: str, pending_requests: int = 0):
        """Log system shutdown"""
        await self.log(
            event_type=AuditEventType.SYSTEM_SHUTDOWN,
            severity=AuditSeverity.INFO,
            details={
                "reason": reason,
                "pending_requests": pending_requests,
            },
        )
        # Flush immediately on shutdown
        await self.flush_now()

    async def log_admin_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log administrative action"""
        await self.log(
            event_type=AuditEventType.ADMIN_ACTION,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            details={"action": action, **(details or {})},
        )

    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get audit events with optional filtering.

        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            severity: Filter by severity
            user_id: Filter by user ID
            request_id: Filter by request ID

        Returns:
            List of audit events
        """
        events = list(self._events)

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if request_id:
            events = [e for e in events if e.request_id == request_id]

        # Return most recent events
        return [e.to_dict() for e in events[-limit:]]

    def get_stats(self) -> AuditStats:
        """Get audit logging statistics"""
        self._stats.buffer_size = len(self._buffer)
        return self._stats

    def verify_chain(self, events: Optional[List[AuditEvent]] = None) -> bool:
        """
        Verify the integrity of the audit chain.

        Returns:
            True if chain is valid, False if tampered
        """
        if not self.include_hash:
            return True

        events = events or list(self._events)
        if not events:
            return True

        # Verify each event's hash
        for i, event in enumerate(events):
            if i == 0:
                if event.previous_hash != "genesis":
                    logging.error(f"[AUDIT] Chain broken at genesis")
                    return False
            else:
                if event.previous_hash != events[i-1].event_hash:
                    logging.error(f"[AUDIT] Chain broken at event {event.event_id}")
                    return False

            # Verify event hash
            computed_hash = self._compute_hash(event)
            if computed_hash != event.event_hash:
                logging.error(f"[AUDIT] Hash mismatch for event {event.event_id}")
                return False

        return True


# Global audit logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def handle_audit_stats_request() -> Dict[str, Any]:
    """Handle /audit/stats request"""
    logger = get_audit_logger()
    stats = logger.get_stats()
    return {
        "enabled": logger.enabled,
        "buffer_size": logger.buffer_size,
        "flush_interval": logger.flush_interval,
        "include_hash": logger.include_hash,
        **stats.to_dict(),
    }


def handle_audit_events_request(
    limit: int = 100,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle /audit/events request"""
    logger = get_audit_logger()
    events = logger.get_events(
        limit=limit,
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        request_id=request_id,
    )
    return {
        "count": len(events),
        "events": events,
    }


def handle_audit_verify_request() -> Dict[str, Any]:
    """Handle /audit/verify request"""
    logger = get_audit_logger()
    is_valid = logger.verify_chain()
    return {
        "valid": is_valid,
        "total_events": logger.get_stats().total_events,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
