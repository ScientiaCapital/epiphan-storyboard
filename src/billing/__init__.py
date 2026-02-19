"""
Billing module for Epiphan Storyboard.

Provides Stripe integration for subscriptions, checkout, and payment management.

Usage:
    from src.billing import BillingTier, get_stripe_client, billing_router

    # Check subscription
    from src.billing import get_subscription_service
    service = get_subscription_service()
    billing = await service.get_organization_billing("org_123")

    # Include router in FastAPI app
    app.include_router(billing_router)

    # Use billing middleware in endpoints
    from src.billing import require_billing, record_usage, BillingContext

    @router.post("/endpoint")
    async def my_endpoint(
        billing: BillingContext = Depends(require_billing(estimated_tokens=1000)),
    ):
        # Process request...
        await record_usage(billing, actual_tokens=500)
"""

from src.billing.middleware import (
    BillingContext,
    record_usage,
    require_billing,
    require_quota,
    require_tier,
)
from src.billing.router import router as billing_router
from src.billing.schemas import (
    BillingTier,
    CheckoutRequest,
    CheckoutResponse,
    OrganizationBilling,
    PortalRequest,
    PortalResponse,
    SubscriptionResponse,
    SubscriptionStatus,
    WebhookEvent,
)
from src.billing.service import SubscriptionService, get_subscription_service
from src.billing.stripe_client import (
    StripeClient,
    StripeClientError,
    StripeConfigError,
    get_stripe_client,
)

__all__ = [
    # Router
    "billing_router",
    # Middleware
    "BillingContext",
    "record_usage",
    "require_billing",
    "require_quota",
    "require_tier",
    # Schemas
    "BillingTier",
    "CheckoutRequest",
    "CheckoutResponse",
    "OrganizationBilling",
    "PortalRequest",
    "PortalResponse",
    "SubscriptionResponse",
    "SubscriptionStatus",
    "WebhookEvent",
    # Stripe client
    "StripeClient",
    "StripeClientError",
    "StripeConfigError",
    "get_stripe_client",
    # Service
    "SubscriptionService",
    "get_subscription_service",
]
