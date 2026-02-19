"""
Stripe SDK wrapper for Epiphan Storyboard billing.

Provides async-friendly interface to Stripe API for:
- Checkout session creation
- Customer portal sessions
- Subscription management
- Webhook verification

Environment Variables:
- STRIPE_SECRET_KEY: Stripe secret key (sk_live_... or sk_test_...)
- STRIPE_WEBHOOK_SECRET: Stripe webhook signing secret (whsec_...)
- STRIPE_PRICE_ID_BASIC: Price ID for Basic tier ($49/mo)
- STRIPE_PRICE_ID_PRO: Price ID for Pro tier ($199/mo)
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

try:
    import stripe
    from stripe import error as stripe_error

    _STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore[assignment]
    stripe_error = None  # type: ignore[assignment]
    _STRIPE_AVAILABLE = False

from src.billing.schemas import (
    TIER_PRICE_ENV_MAP,
    BillingTier,
    CheckoutResponse,
    PortalResponse,
    SubscriptionStatus,
    WebhookEvent,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StripeClientError(Exception):
    """Base exception for Stripe client errors."""

    pass


class StripeConfigError(StripeClientError):
    """Raised when Stripe is not properly configured."""

    pass


class StripeClient:
    """
    Wrapper for Stripe SDK operations.

    Handles authentication, checkout sessions, subscriptions,
    and webhook verification.

    Example:
        client = StripeClient()

        # Create checkout session
        session = await client.create_checkout_session(
            org_id="org_123",
            tier=BillingTier.PRO,
            success_url="https://app.example.com/success",
            cancel_url="https://app.example.com/cancel",
        )

        # Create portal session
        portal = await client.create_portal_session(
            customer_id="cus_abc123",
            return_url="https://app.example.com/settings",
        )
    """

    def __init__(
        self,
        secret_key: str | None = None,
        webhook_secret: str | None = None,
    ):
        """
        Initialize Stripe client.

        Args:
            secret_key: Stripe secret key (defaults to STRIPE_SECRET_KEY env var)
            webhook_secret: Webhook signing secret (defaults to STRIPE_WEBHOOK_SECRET env var)
        """
        self._secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY", "")
        self._webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")

        # Configure stripe module
        if self._secret_key and _STRIPE_AVAILABLE:
            stripe.api_key = self._secret_key

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self._secret_key) and _STRIPE_AVAILABLE

    def _ensure_configured(self) -> None:
        """Raise error if Stripe is not configured."""
        if not _STRIPE_AVAILABLE:
            raise StripeConfigError(
                "stripe package is not installed. Run: pip install stripe"
            )
        if not self.is_configured:
            raise StripeConfigError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable."
            )

    def _get_price_id(self, tier: BillingTier) -> str:
        """Get Stripe Price ID for a tier."""
        env_var = TIER_PRICE_ENV_MAP.get(tier)
        if not env_var:
            raise ValueError(f"No price ID configured for tier: {tier}")

        price_id = os.getenv(env_var, "")
        if not price_id:
            raise StripeConfigError(
                f"Price ID not configured. Set {env_var} environment variable."
            )

        return price_id

    async def create_checkout_session(
        self,
        org_id: str,
        tier: BillingTier,
        success_url: str,
        cancel_url: str,
        customer_email: str | None = None,
        customer_id: str | None = None,
    ) -> CheckoutResponse:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            org_id: Organization ID to associate with subscription
            tier: Target subscription tier (basic or pro)
            success_url: URL to redirect after successful checkout
            cancel_url: URL to redirect if checkout is cancelled
            customer_email: Pre-fill customer email
            customer_id: Existing Stripe customer ID (for upgrades)

        Returns:
            CheckoutResponse with checkout URL and session ID

        Raises:
            StripeConfigError: If Stripe is not configured
            StripeClientError: On Stripe API errors
        """
        self._ensure_configured()

        try:
            price_id = self._get_price_id(tier)

            session_params: dict[str, Any] = {
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "org_id": org_id,
                    "tier": tier.value,
                },
                "subscription_data": {
                    "metadata": {
                        "org_id": org_id,
                        "tier": tier.value,
                    },
                },
            }

            if customer_id:
                session_params["customer"] = customer_id
            elif customer_email:
                session_params["customer_email"] = customer_email

            session = stripe.checkout.Session.create(**session_params)

            logger.info(
                f"[STRIPE] Created checkout session for org={org_id} tier={tier.value}"
            )

            if not session.url:
                raise StripeClientError("Checkout session created but no URL returned")

            return CheckoutResponse(
                checkout_url=session.url,
                session_id=session.id,
            )

        except stripe_error.StripeError as e:
            logger.error(f"[STRIPE] Checkout session failed: {e}")
            raise StripeClientError(f"Failed to create checkout session: {e}") from e

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> PortalResponse:
        """
        Create a Stripe Customer Portal session.

        Allows customers to manage their subscription, payment methods,
        and billing history.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to redirect after leaving portal

        Returns:
            PortalResponse with portal URL

        Raises:
            StripeConfigError: If Stripe is not configured
            StripeClientError: On Stripe API errors
        """
        self._ensure_configured()

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

            logger.info(f"[STRIPE] Created portal session for customer={customer_id}")

            return PortalResponse(portal_url=session.url)

        except stripe_error.StripeError as e:
            logger.error(f"[STRIPE] Portal session failed: {e}")
            raise StripeClientError(f"Failed to create portal session: {e}") from e

    async def get_subscription(
        self,
        subscription_id: str,
    ) -> dict[str, Any]:
        """
        Get subscription details from Stripe.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription data dict with status, current_period_end, etc.

        Raises:
            StripeConfigError: If Stripe is not configured
            StripeClientError: On Stripe API errors
        """
        self._ensure_configured()

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Access attributes via getattr to handle Stripe SDK type issues
            period_end = getattr(subscription, "current_period_end", 0)

            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": datetime.fromtimestamp(period_end, tz=UTC),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "customer": subscription.customer,
                "metadata": dict(subscription.metadata)
                if subscription.metadata
                else {},
            }

        except stripe_error.StripeError as e:
            logger.error(f"[STRIPE] Get subscription failed: {e}")
            raise StripeClientError(f"Failed to get subscription: {e}") from e

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period (default).
                           If False, cancel immediately.

        Returns:
            Updated subscription data

        Raises:
            StripeConfigError: If Stripe is not configured
            StripeClientError: On Stripe API errors
        """
        self._ensure_configured()

        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                subscription = stripe.Subscription.cancel(subscription_id)

            logger.info(
                f"[STRIPE] Cancelled subscription {subscription_id} "
                f"(at_period_end={at_period_end})"
            )

            return {
                "id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            }

        except stripe_error.StripeError as e:
            logger.error(f"[STRIPE] Cancel subscription failed: {e}")
            raise StripeClientError(f"Failed to cancel subscription: {e}") from e

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> WebhookEvent:
        """
        Verify and parse a Stripe webhook event.

        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value

        Returns:
            Parsed WebhookEvent

        Raises:
            StripeConfigError: If webhook secret is not configured
            StripeClientError: If signature is invalid
        """
        if not self._webhook_secret:
            raise StripeConfigError(
                "Webhook secret not configured. Set STRIPE_WEBHOOK_SECRET."
            )

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self._webhook_secret,
            )

            return WebhookEvent(
                event_id=event.id,
                event_type=event.type,
                data=dict(event.data.object) if event.data.object else {},
                created_at=datetime.fromtimestamp(event.created, tz=UTC),
            )

        except stripe_error.SignatureVerificationError as e:
            logger.error(f"[STRIPE] Webhook signature verification failed: {e}")
            raise StripeClientError(f"Invalid webhook signature: {e}") from e

    @staticmethod
    def map_stripe_status(stripe_status: str) -> SubscriptionStatus:
        """
        Map Stripe subscription status to our SubscriptionStatus enum.

        Args:
            stripe_status: Stripe subscription status string

        Returns:
            Corresponding SubscriptionStatus
        """
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "canceled": SubscriptionStatus.CANCELED,
            "past_due": SubscriptionStatus.PAST_DUE,
            "trialing": SubscriptionStatus.TRIALING,
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
            "paused": SubscriptionStatus.PAUSED,
            "unpaid": SubscriptionStatus.UNPAID,
        }
        return status_map.get(stripe_status, SubscriptionStatus.FREE)


# ============================================================================
# Global client
# ============================================================================

_stripe_client: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    """Get or create the global Stripe client."""
    global _stripe_client
    if _stripe_client is None:
        _stripe_client = StripeClient()
    return _stripe_client
