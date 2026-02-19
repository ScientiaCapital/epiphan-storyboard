"""
Usage Quotas & Spending Limits Module

Enables tiered pricing with per-user/organization quotas.
Prevents abuse and enables monetization controls.
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logging.basicConfig(level=logging.INFO)


class QuotaPeriod(Enum):
    """Time periods for quota tracking"""
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class QuotaAction(Enum):
    """Actions to take when quota exceeded"""
    BLOCK = "block"      # Block the request
    WARN = "warn"        # Allow but warn
    THROTTLE = "throttle"  # Slow down requests


@dataclass
class QuotaLimit:
    """A single quota limit"""
    tokens: int                    # Token limit
    period: QuotaPeriod           # Time period
    action: QuotaAction = QuotaAction.BLOCK  # Action when exceeded
    warning_threshold: float = 0.8  # Warn at this percentage


@dataclass
class QuotaUsage:
    """Current usage for a quota"""
    used: int = 0
    limit: int = 0
    period: str = "daily"
    reset_at: Optional[str] = None
    percentage: float = 0.0
    exceeded: bool = False
    warning: bool = False


@dataclass
class UserQuota:
    """Quota configuration for a user/organization"""
    user_id: str
    organization_id: Optional[str] = None
    tier: str = "free"

    # Token limits
    hourly_tokens: int = 0
    daily_tokens: int = 0
    monthly_tokens: int = 0

    # Spending limits (in cents)
    daily_spend_limit: int = 0
    monthly_spend_limit: int = 0

    # Current usage
    hourly_used: int = 0
    daily_used: int = 0
    monthly_used: int = 0
    daily_spend: int = 0
    monthly_spend: int = 0

    # Reset timestamps
    hourly_reset: float = 0
    daily_reset: float = 0
    monthly_reset: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "tier": self.tier,
            "limits": {
                "hourly_tokens": self.hourly_tokens,
                "daily_tokens": self.daily_tokens,
                "monthly_tokens": self.monthly_tokens,
                "daily_spend_limit": self.daily_spend_limit,
                "monthly_spend_limit": self.monthly_spend_limit,
            },
            "usage": {
                "hourly_used": self.hourly_used,
                "daily_used": self.daily_used,
                "monthly_used": self.monthly_used,
                "daily_spend": self.daily_spend,
                "monthly_spend": self.monthly_spend,
            },
        }


@dataclass
class QuotaCheckResult:
    """Result of a quota check"""
    allowed: bool
    reason: Optional[str] = None
    warning: Optional[str] = None
    usage: Optional[Dict[str, QuotaUsage]] = None
    retry_after: Optional[int] = None  # Seconds until quota resets


@dataclass
class QuotaStats:
    """Quota manager statistics"""
    total_checks: int = 0
    total_blocked: int = 0
    total_warnings: int = 0
    active_users: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "total_blocked": self.total_blocked,
            "total_warnings": self.total_warnings,
            "active_users": self.active_users,
        }


class QuotaManager:
    """
    Manages usage quotas and spending limits.

    Configure via environment variables:
    - QUOTA_ENABLED: Enable quota enforcement (default: true)
    - QUOTA_DEFAULT_HOURLY: Default hourly token limit (default: 10000)
    - QUOTA_DEFAULT_DAILY: Default daily token limit (default: 100000)
    - QUOTA_DEFAULT_MONTHLY: Default monthly token limit (default: 1000000)
    - QUOTA_FREE_HOURLY: Free tier hourly limit (default: 1000)
    - QUOTA_FREE_DAILY: Free tier daily limit (default: 10000)
    - QUOTA_BASIC_HOURLY: Basic tier hourly limit (default: 5000)
    - QUOTA_BASIC_DAILY: Basic tier daily limit (default: 50000)
    - QUOTA_PRO_HOURLY: Pro tier hourly limit (default: 50000)
    - QUOTA_PRO_DAILY: Pro tier daily limit (default: 500000)
    - QUOTA_ENTERPRISE_HOURLY: Enterprise tier hourly limit (default: 0 = unlimited)
    - QUOTA_ENTERPRISE_DAILY: Enterprise tier daily limit (default: 0 = unlimited)
    """

    def __init__(self):
        self.enabled = os.getenv("QUOTA_ENABLED", "true").lower() == "true"

        # Default limits
        self.default_hourly = int(os.getenv("QUOTA_DEFAULT_HOURLY", "10000"))
        self.default_daily = int(os.getenv("QUOTA_DEFAULT_DAILY", "100000"))
        self.default_monthly = int(os.getenv("QUOTA_DEFAULT_MONTHLY", "1000000"))

        # Tier-specific limits
        self.tier_limits = {
            "free": {
                "hourly": int(os.getenv("QUOTA_FREE_HOURLY", "1000")),
                "daily": int(os.getenv("QUOTA_FREE_DAILY", "10000")),
                "monthly": int(os.getenv("QUOTA_FREE_MONTHLY", "100000")),
            },
            "basic": {
                "hourly": int(os.getenv("QUOTA_BASIC_HOURLY", "5000")),
                "daily": int(os.getenv("QUOTA_BASIC_DAILY", "50000")),
                "monthly": int(os.getenv("QUOTA_BASIC_MONTHLY", "500000")),
            },
            "pro": {
                "hourly": int(os.getenv("QUOTA_PRO_HOURLY", "50000")),
                "daily": int(os.getenv("QUOTA_PRO_DAILY", "500000")),
                "monthly": int(os.getenv("QUOTA_PRO_MONTHLY", "5000000")),
            },
            "enterprise": {
                "hourly": int(os.getenv("QUOTA_ENTERPRISE_HOURLY", "0")),
                "daily": int(os.getenv("QUOTA_ENTERPRISE_DAILY", "0")),
                "monthly": int(os.getenv("QUOTA_ENTERPRISE_MONTHLY", "0")),
            },
        }

        # User quotas storage
        self._quotas: Dict[str, UserQuota] = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = QuotaStats()

        if self.enabled:
            logging.info(f"[QUOTA] Quota management enabled")

    def _get_tier_limits(self, tier: str) -> Dict[str, int]:
        """Get limits for a tier"""
        return self.tier_limits.get(tier.lower(), self.tier_limits["free"])

    async def get_or_create_quota(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        tier: str = "free"
    ) -> UserQuota:
        """Get or create a user's quota"""
        async with self._lock:
            key = f"{user_id}:{organization_id or 'default'}"

            if key not in self._quotas:
                limits = self._get_tier_limits(tier)
                self._quotas[key] = UserQuota(
                    user_id=user_id,
                    organization_id=organization_id,
                    tier=tier,
                    hourly_tokens=limits["hourly"],
                    daily_tokens=limits["daily"],
                    monthly_tokens=limits["monthly"],
                )
                self._stats.active_users = len(self._quotas)

            return self._quotas[key]

    async def check_quota(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        tier: str = "free",
        tokens_requested: int = 0
    ) -> QuotaCheckResult:
        """
        Check if a request is within quota limits.

        Args:
            user_id: User identifier
            organization_id: Organization identifier
            tier: User tier
            tokens_requested: Estimated tokens for this request

        Returns:
            QuotaCheckResult with allowed status and details
        """
        if not self.enabled:
            return QuotaCheckResult(allowed=True)

        self._stats.total_checks += 1
        quota = await self.get_or_create_quota(user_id, organization_id, tier)

        # Reset expired periods
        await self._reset_if_expired(quota)

        # Check each period
        warnings = []
        usage = {}

        # Check hourly
        if quota.hourly_tokens > 0:
            hourly_usage = self._check_period(
                quota.hourly_used + tokens_requested,
                quota.hourly_tokens,
                "hourly",
                quota.hourly_reset
            )
            usage["hourly"] = hourly_usage

            if hourly_usage.exceeded:
                self._stats.total_blocked += 1
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Hourly token quota exceeded ({quota.hourly_used}/{quota.hourly_tokens})",
                    usage=usage,
                    retry_after=int(quota.hourly_reset - time.time()) if quota.hourly_reset > time.time() else 3600
                )
            if hourly_usage.warning:
                warnings.append(f"Hourly quota at {hourly_usage.percentage:.0f}%")

        # Check daily
        if quota.daily_tokens > 0:
            daily_usage = self._check_period(
                quota.daily_used + tokens_requested,
                quota.daily_tokens,
                "daily",
                quota.daily_reset
            )
            usage["daily"] = daily_usage

            if daily_usage.exceeded:
                self._stats.total_blocked += 1
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Daily token quota exceeded ({quota.daily_used}/{quota.daily_tokens})",
                    usage=usage,
                    retry_after=int(quota.daily_reset - time.time()) if quota.daily_reset > time.time() else 86400
                )
            if daily_usage.warning:
                warnings.append(f"Daily quota at {daily_usage.percentage:.0f}%")

        # Check monthly
        if quota.monthly_tokens > 0:
            monthly_usage = self._check_period(
                quota.monthly_used + tokens_requested,
                quota.monthly_tokens,
                "monthly",
                quota.monthly_reset
            )
            usage["monthly"] = monthly_usage

            if monthly_usage.exceeded:
                self._stats.total_blocked += 1
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Monthly token quota exceeded ({quota.monthly_used}/{quota.monthly_tokens})",
                    usage=usage,
                    retry_after=int(quota.monthly_reset - time.time()) if quota.monthly_reset > time.time() else 2592000
                )
            if monthly_usage.warning:
                warnings.append(f"Monthly quota at {monthly_usage.percentage:.0f}%")

        warning_msg = None
        if warnings:
            self._stats.total_warnings += 1
            warning_msg = "; ".join(warnings)

        return QuotaCheckResult(
            allowed=True,
            warning=warning_msg,
            usage=usage
        )

    def _check_period(
        self,
        used: int,
        limit: int,
        period: str,
        reset_at: float
    ) -> QuotaUsage:
        """Check usage for a single period"""
        percentage = (used / limit * 100) if limit > 0 else 0

        return QuotaUsage(
            used=used,
            limit=limit,
            period=period,
            reset_at=datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat() if reset_at else None,
            percentage=percentage,
            exceeded=used > limit,
            warning=percentage >= 80 and not used > limit
        )

    async def _reset_if_expired(self, quota: UserQuota):
        """Reset quota periods if expired"""
        now = time.time()

        # Hourly reset
        if now >= quota.hourly_reset:
            quota.hourly_used = 0
            quota.hourly_reset = now + 3600

        # Daily reset
        if now >= quota.daily_reset:
            quota.daily_used = 0
            quota.daily_spend = 0
            quota.daily_reset = now + 86400

        # Monthly reset
        if now >= quota.monthly_reset:
            quota.monthly_used = 0
            quota.monthly_spend = 0
            quota.monthly_reset = now + 2592000  # ~30 days

    async def record_usage(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        tokens: int = 0,
        cost_cents: int = 0
    ):
        """
        Record token usage for a user.

        Args:
            user_id: User identifier
            organization_id: Organization identifier
            tokens: Number of tokens used
            cost_cents: Cost in cents
        """
        if not self.enabled:
            return

        quota = await self.get_or_create_quota(user_id, organization_id)

        async with self._lock:
            quota.hourly_used += tokens
            quota.daily_used += tokens
            quota.monthly_used += tokens
            quota.daily_spend += cost_cents
            quota.monthly_spend += cost_cents

    async def get_usage(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get usage information for a user"""
        key = f"{user_id}:{organization_id or 'default'}"

        if key in self._quotas:
            quota = self._quotas[key]
            await self._reset_if_expired(quota)
            return quota.to_dict()

        return None

    async def set_limits(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        hourly: Optional[int] = None,
        daily: Optional[int] = None,
        monthly: Optional[int] = None,
        daily_spend: Optional[int] = None,
        monthly_spend: Optional[int] = None
    ):
        """Set custom limits for a user"""
        quota = await self.get_or_create_quota(user_id, organization_id)

        async with self._lock:
            if hourly is not None:
                quota.hourly_tokens = hourly
            if daily is not None:
                quota.daily_tokens = daily
            if monthly is not None:
                quota.monthly_tokens = monthly
            if daily_spend is not None:
                quota.daily_spend_limit = daily_spend
            if monthly_spend is not None:
                quota.monthly_spend_limit = monthly_spend

    def get_stats(self) -> QuotaStats:
        """Get quota manager statistics"""
        self._stats.active_users = len(self._quotas)
        return self._stats


# Global quota manager
_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    """Get or create the global quota manager"""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


def handle_quota_stats_request() -> Dict[str, Any]:
    """Handle /quota/stats request"""
    manager = get_quota_manager()
    stats = manager.get_stats()
    return {
        "enabled": manager.enabled,
        "tier_limits": manager.tier_limits,
        **stats.to_dict(),
    }


async def handle_quota_usage_request(
    user_id: str,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """Handle /quota/usage request"""
    manager = get_quota_manager()
    usage = await manager.get_usage(user_id, organization_id)

    if usage:
        return usage
    else:
        return {"error": "User not found", "user_id": user_id}
