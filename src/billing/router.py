"""
FastAPI router for Billing API.

Endpoints:
- POST /billing/checkout - Create Stripe Checkout session
- GET /billing/subscription - Get current subscription status
- POST /billing/portal - Create Customer Portal session
- POST /billing/webhooks/stripe - Handle Stripe webhook events
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from src.billing.schemas import (
    BillingTier,
    CheckoutRequest,
    CheckoutResponse,
    PortalRequest,
    PortalResponse,
    SubscriptionResponse,
)
from src.billing.service import SubscriptionService, get_subscription_service
from src.billing.stripe_client import (
    StripeClient,
    StripeClientError,
    StripeConfigError,
    get_stripe_client,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ============================================================================
# Dependencies
# ============================================================================


def get_stripe() -> StripeClient:
    """Dependency to get Stripe client."""
    return get_stripe_client()


def get_service() -> SubscriptionService:
    """Dependency to get subscription service."""
    return get_subscription_service()


# ============================================================================
# Checkout Endpoints
# ============================================================================


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create Stripe Checkout session",
    description=(
        "Create a Stripe Checkout session for subscription upgrade. "
        "Returns a URL to redirect the user to Stripe's hosted checkout page."
    ),
    responses={
        400: {"description": "Invalid tier or missing required fields"},
        503: {"description": "Stripe not configured"},
    },
)
async def create_checkout(
    request: CheckoutRequest,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    stripe_client: StripeClient = Depends(get_stripe),
    service: SubscriptionService = Depends(get_service),
) -> CheckoutResponse:
    """Create Stripe Checkout session for subscription upgrade."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Validate tier (can't checkout for free or enterprise)
    if request.tier in (BillingTier.FREE, BillingTier.ENTERPRISE):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot checkout for tier: {request.tier.value}. "
            "Use basic or pro tier.",
        )

    # Check if already subscribed
    current_billing = await service.get_organization_billing(x_org_id)
    customer_id = current_billing.stripe_customer_id

    try:
        response = await stripe_client.create_checkout_session(
            org_id=x_org_id,
            tier=request.tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_id=customer_id,  # Pass existing customer if any
        )

        logger.info(f"[BILLING_API] Created checkout for org={x_org_id}")
        return response

    except StripeConfigError as e:
        logger.error(f"[BILLING_API] Stripe not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail="Billing service not configured. Contact support.",
        ) from e

    except StripeClientError as e:
        logger.error(f"[BILLING_API] Checkout failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create checkout session. Try again later.",
        ) from e


# ============================================================================
# Subscription Endpoints
# ============================================================================


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get current subscription status",
    description=(
        "Get the current subscription status for the organization. "
        "Returns tier, status, and billing period information."
    ),
)
async def get_subscription(
    x_org_id: str = Header(..., alias="X-Org-ID"),
    service: SubscriptionService = Depends(get_service),
) -> SubscriptionResponse:
    """Get current subscription status for organization."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    billing = await service.get_organization_billing(x_org_id)

    return SubscriptionResponse(
        org_id=x_org_id,
        tier=billing.tier,
        status=billing.subscription_status,
        stripe_customer_id=billing.stripe_customer_id,
        stripe_subscription_id=billing.stripe_subscription_id,
        current_period_end=billing.current_period_end,
        cancel_at_period_end=billing.cancel_at_period_end,
    )


# ============================================================================
# Portal Endpoints
# ============================================================================


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Create Customer Portal session",
    description=(
        "Create a Stripe Customer Portal session for managing subscription, "
        "payment methods, and billing history. Requires an active subscription."
    ),
    responses={
        400: {"description": "No subscription to manage"},
        503: {"description": "Stripe not configured"},
    },
)
async def create_portal(
    request: PortalRequest,
    x_org_id: str = Header(..., alias="X-Org-ID"),
    stripe_client: StripeClient = Depends(get_stripe),
    service: SubscriptionService = Depends(get_service),
) -> PortalResponse:
    """Create Stripe Customer Portal session."""
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Get current billing to find customer ID
    billing = await service.get_organization_billing(x_org_id)

    if not billing.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription found. Subscribe first to manage billing.",
        )

    try:
        response = await stripe_client.create_portal_session(
            customer_id=billing.stripe_customer_id,
            return_url=request.return_url,
        )

        logger.info(f"[BILLING_API] Created portal for org={x_org_id}")
        return response

    except StripeConfigError as e:
        logger.error(f"[BILLING_API] Stripe not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail="Billing service not configured. Contact support.",
        ) from e

    except StripeClientError as e:
        logger.error(f"[BILLING_API] Portal failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create portal session. Try again later.",
        ) from e


# ============================================================================
# Webhook Endpoints
# ============================================================================


@router.post(
    "/webhooks/stripe",
    summary="Handle Stripe webhook events",
    description=(
        "Receive and process Stripe webhook events. "
        "Verifies signature and updates subscription state."
    ),
    responses={
        400: {"description": "Invalid signature or payload"},
    },
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    stripe_client: StripeClient = Depends(get_stripe),
    service: SubscriptionService = Depends(get_service),
) -> dict:
    """Handle Stripe webhook events."""
    # Get raw request body for signature verification
    payload = await request.body()

    try:
        event = stripe_client.verify_webhook_signature(
            payload=payload,
            signature=stripe_signature,
        )

        logger.info(f"[BILLING_API] Received webhook: {event.event_type}")

        # Handle the event
        result = await service.handle_webhook_event(event)

        return {"status": "ok", **result}

    except StripeConfigError as e:
        logger.error(f"[BILLING_API] Webhook secret not configured: {e}")
        raise HTTPException(
            status_code=500,
            detail="Webhook handler not configured.",
        ) from e

    except StripeClientError as e:
        logger.error(f"[BILLING_API] Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature.",
        ) from e


# ============================================================================
# Health Check
# ============================================================================


@router.get(
    "/health",
    summary="Billing service health check",
    description="Check if billing service is properly configured.",
)
async def billing_health(
    stripe_client: StripeClient = Depends(get_stripe),
) -> dict:
    """Check billing service health."""
    return {
        "status": "ok" if stripe_client.is_configured else "not_configured",
        "stripe_configured": stripe_client.is_configured,
    }
