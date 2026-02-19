"""
Billing middleware for FastAPI endpoints.

Provides dependencies for:
- Quota checking before request processing
- Usage recording after request completion
- Tier-based access control

Usage:
    from src.billing.middleware import require_quota, record_usage

    @router.post("/endpoint")
    async def my_endpoint(
        quota_check: QuotaCheckResult = Depends(require_quota(estimated_tokens=1000)),
    ):
        # Request is allowed, proceed
        ...
        # Record actual usage after completion
        await record_usage(quota_check, actual_tokens=500)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import Header, HTTPException

from src.billing.schemas import BillingTier, SubscriptionStatus
from src.billing.service import get_subscription_service

if TYPE_CHECKING:
    from src.billing.service import SubscriptionService

logger = logging.getLogger(__name__)


# ============================================================================
# Dependencies
# ============================================================================


def get_quota_manager():  # type: ignore[no-untyped-def]
    """Dependency to get QuotaManager."""
    from src.quotas import get_quota_manager as _get_quota_manager

    return _get_quota_manager()


def get_billing_service() -> SubscriptionService:
    """Dependency to get SubscriptionService."""
    return get_subscription_service()


# ============================================================================
# Quota Checking
# ============================================================================


class BillingContext:
    """Context object containing billing info for a request."""

    def __init__(
        self,
        org_id: str,
        tier: BillingTier,
        subscription_status: SubscriptionStatus,
        quota_allowed: bool,
        quota_warning: str | None = None,
        estimated_tokens: int = 0,
    ):
        self.org_id = org_id
        self.tier = tier
        self.subscription_status = subscription_status
        self.quota_allowed = quota_allowed
        self.quota_warning = quota_warning
        self.estimated_tokens = estimated_tokens

    @property
    def tier_name(self) -> str:
        """Get tier name for quota manager."""
        return self.tier.value


def require_quota(estimated_tokens: int = 1000) -> Callable:
    """
    Create a dependency that checks billing and quotas.

    Args:
        estimated_tokens: Estimated token usage for this request

    Returns:
        FastAPI dependency function

    Raises:
        HTTPException 402: Subscription inactive
        HTTPException 429: Quota exceeded
    """

    async def check_quota(
        x_org_id: str = Header(..., alias="X-Org-ID"),
    ) -> BillingContext:
        """Check billing status and quotas for org."""
        from src.quotas import get_quota_manager

        if not x_org_id or not x_org_id.strip():
            raise HTTPException(status_code=400, detail="X-Org-ID header is required")

        # Get billing info
        billing_service = get_subscription_service()
        billing = await billing_service.get_organization_billing(x_org_id)

        # Check subscription status
        if billing.subscription_status in (
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.UNPAID,
        ):
            logger.warning(f"[BILLING] Org {x_org_id} has past due subscription")
            raise HTTPException(
                status_code=402,
                detail="Subscription payment required. Please update payment method.",
            )

        if billing.subscription_status == SubscriptionStatus.CANCELED:
            # Allow if tier is still free (downgraded)
            if billing.tier != BillingTier.FREE:
                raise HTTPException(
                    status_code=402,
                    detail="Subscription canceled. Please resubscribe to continue.",
                )

        # Check quotas
        quota_manager = get_quota_manager()
        quota_result = await quota_manager.check_quota(
            user_id=x_org_id,
            organization_id=x_org_id,
            tier=billing.tier.value,
            tokens_requested=estimated_tokens,
        )

        if not quota_result.allowed:
            logger.warning(
                f"[BILLING] Quota exceeded for org {x_org_id}: {quota_result.reason}"
            )
            raise HTTPException(
                status_code=429,
                detail=quota_result.reason or "Quota exceeded",
                headers={
                    "Retry-After": str(quota_result.retry_after or 3600),
                    "X-Quota-Exceeded": "true",
                },
            )

        return BillingContext(
            org_id=x_org_id,
            tier=billing.tier,
            subscription_status=billing.subscription_status,
            quota_allowed=True,
            quota_warning=quota_result.warning,
            estimated_tokens=estimated_tokens,
        )

    return check_quota


async def record_usage(
    billing_context: BillingContext,
    actual_tokens: int,
) -> None:
    """
    Record actual token usage after request completion.

    Args:
        billing_context: Context from require_quota dependency
        actual_tokens: Actual tokens used
    """
    from src.quotas import get_quota_manager

    quota_manager = get_quota_manager()

    await quota_manager.record_usage(
        user_id=billing_context.org_id,
        organization_id=billing_context.org_id,
        tokens=actual_tokens,
    )

    logger.info(
        f"[BILLING] Recorded {actual_tokens} tokens for org {billing_context.org_id}"
    )


# ============================================================================
# Tier Access Control
# ============================================================================


def require_tier(minimum_tier: BillingTier) -> Callable:
    """
    Create a dependency that requires a minimum subscription tier.

    Args:
        minimum_tier: Minimum tier required for access

    Returns:
        FastAPI dependency function

    Raises:
        HTTPException 403: Tier too low
    """

    async def check_tier(
        x_org_id: str = Header(..., alias="X-Org-ID"),
    ) -> BillingContext:
        """Check if org has required tier."""
        if not x_org_id or not x_org_id.strip():
            raise HTTPException(status_code=400, detail="X-Org-ID header is required")

        billing_service = get_subscription_service()
        billing = await billing_service.get_organization_billing(x_org_id)

        if not billing.can_access_tier(minimum_tier):
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires {minimum_tier.value} tier or higher. "
                f"Current tier: {billing.tier.value}",
            )

        return BillingContext(
            org_id=x_org_id,
            tier=billing.tier,
            subscription_status=billing.subscription_status,
            quota_allowed=True,
        )

    return check_tier


# ============================================================================
# Combined Dependencies
# ============================================================================


def require_billing(
    minimum_tier: BillingTier | None = None,
    estimated_tokens: int = 1000,
) -> Callable:
    """
    Create a combined dependency for tier and quota checks.

    Args:
        minimum_tier: Minimum tier required (None = any tier)
        estimated_tokens: Estimated token usage

    Returns:
        FastAPI dependency function
    """

    async def check_billing(
        x_org_id: str = Header(..., alias="X-Org-ID"),
    ) -> BillingContext:
        """Check billing, tier, and quotas."""
        from src.quotas import get_quota_manager

        if not x_org_id or not x_org_id.strip():
            raise HTTPException(status_code=400, detail="X-Org-ID header is required")

        # Get billing info
        billing_service = get_subscription_service()
        billing = await billing_service.get_organization_billing(x_org_id)

        # Check tier if required
        if minimum_tier and not billing.can_access_tier(minimum_tier):
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires {minimum_tier.value} tier or higher. "
                f"Current tier: {billing.tier.value}",
            )

        # Check subscription status
        if billing.subscription_status in (
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.UNPAID,
        ):
            raise HTTPException(
                status_code=402,
                detail="Subscription payment required. Please update payment method.",
            )

        # Check quotas
        quota_manager = get_quota_manager()
        quota_result = await quota_manager.check_quota(
            user_id=x_org_id,
            organization_id=x_org_id,
            tier=billing.tier.value,
            tokens_requested=estimated_tokens,
        )

        if not quota_result.allowed:
            raise HTTPException(
                status_code=429,
                detail=quota_result.reason or "Quota exceeded",
                headers={
                    "Retry-After": str(quota_result.retry_after or 3600),
                    "X-Quota-Exceeded": "true",
                },
            )

        return BillingContext(
            org_id=x_org_id,
            tier=billing.tier,
            subscription_status=billing.subscription_status,
            quota_allowed=True,
            quota_warning=quota_result.warning,
            estimated_tokens=estimated_tokens,
        )

    return check_billing
