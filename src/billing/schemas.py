"""
Pydantic schemas for Billing API.

Defines request/response models for Stripe integration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BillingTier(str, Enum):
    """Subscription tiers matching quotas.py."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Stripe subscription statuses."""

    FREE = "free"  # No subscription, free tier
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"
    UNPAID = "unpaid"


# ============================================================================
# Checkout
# ============================================================================


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    tier: BillingTier = Field(
        ...,
        description="Target subscription tier (basic or pro)",
    )
    success_url: str = Field(
        ...,
        description="URL to redirect after successful checkout",
    )
    cancel_url: str = Field(
        ...,
        description="URL to redirect if checkout is cancelled",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tier": "pro",
                "success_url": "https://app.example.com/billing/success",
                "cancel_url": "https://app.example.com/billing/cancel",
            }
        }
    }


class CheckoutResponse(BaseModel):
    """Response from checkout session creation."""

    checkout_url: str = Field(
        ...,
        description="Stripe Checkout URL to redirect user to",
    )
    session_id: str = Field(
        ...,
        description="Stripe Checkout session ID",
    )


# ============================================================================
# Subscription
# ============================================================================


class SubscriptionResponse(BaseModel):
    """Current subscription status for an organization."""

    org_id: str = Field(..., description="Organization ID")
    tier: BillingTier = Field(..., description="Current subscription tier")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    stripe_customer_id: str | None = Field(
        None,
        description="Stripe customer ID (if subscribed)",
    )
    stripe_subscription_id: str | None = Field(
        None,
        description="Stripe subscription ID (if subscribed)",
    )
    current_period_end: datetime | None = Field(
        None,
        description="When current billing period ends",
    )
    cancel_at_period_end: bool = Field(
        False,
        description="Whether subscription will cancel at period end",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "org_id": "org_123",
                "tier": "pro",
                "status": "active",
                "stripe_customer_id": "cus_abc123",
                "stripe_subscription_id": "sub_xyz789",
                "current_period_end": "2025-01-24T00:00:00Z",
                "cancel_at_period_end": False,
            }
        }
    }


# ============================================================================
# Customer Portal
# ============================================================================


class PortalRequest(BaseModel):
    """Request to create a Stripe Customer Portal session."""

    return_url: str = Field(
        ...,
        description="URL to redirect after leaving portal",
    )


class PortalResponse(BaseModel):
    """Response from portal session creation."""

    portal_url: str = Field(
        ...,
        description="Stripe Customer Portal URL",
    )


# ============================================================================
# Webhooks
# ============================================================================


class WebhookEvent(BaseModel):
    """Parsed Stripe webhook event."""

    event_id: str = Field(..., description="Stripe event ID")
    event_type: str = Field(
        ..., description="Event type (e.g., checkout.session.completed)"
    )
    data: dict[str, Any] = Field(..., description="Event data payload")
    created_at: datetime = Field(..., description="Event creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "evt_123",
                "event_type": "checkout.session.completed",
                "data": {"customer": "cus_abc", "subscription": "sub_xyz"},
                "created_at": "2025-12-24T12:00:00Z",
            }
        }
    }


# ============================================================================
# Internal Models
# ============================================================================


class OrganizationBilling(BaseModel):
    """Organization billing state (for internal use)."""

    org_id: str
    tier: BillingTier = BillingTier.FREE
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.FREE
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False

    def is_paying(self) -> bool:
        """Check if org is on a paid tier with active subscription."""
        return (
            self.tier in (BillingTier.BASIC, BillingTier.PRO, BillingTier.ENTERPRISE)
            and self.subscription_status == SubscriptionStatus.ACTIVE
        )

    def can_access_tier(self, required_tier: BillingTier) -> bool:
        """Check if org can access features for a tier."""
        tier_order = {
            BillingTier.FREE: 0,
            BillingTier.BASIC: 1,
            BillingTier.PRO: 2,
            BillingTier.ENTERPRISE: 3,
        }
        return tier_order.get(self.tier, 0) >= tier_order.get(required_tier, 0)


# ============================================================================
# Price IDs
# ============================================================================


TIER_PRICE_ENV_MAP = {
    BillingTier.BASIC: "STRIPE_PRICE_ID_BASIC",
    BillingTier.PRO: "STRIPE_PRICE_ID_PRO",
}
"""Maps tiers to environment variable names for Stripe Price IDs."""
