"""
Subscription Service - Handles subscription lifecycle and quota updates.

This module bridges Stripe events with internal organization state,
ensuring quota limits are synced with subscription tiers.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.billing.schemas import (
    BillingTier,
    OrganizationBilling,
    SubscriptionStatus,
    WebhookEvent,
)
from src.billing.stripe_client import StripeClient, get_stripe_client

if TYPE_CHECKING:
    from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Manages subscription state and syncs with quotas.

    Responsibilities:
    - Handle Stripe webhook events
    - Update organization tier on subscription changes
    - Sync quota limits with tier changes
    - Provide subscription status queries

    Example:
        service = SubscriptionService(supabase_client)

        # Handle checkout completion
        await service.handle_checkout_completed(
            customer_id="cus_123",
            subscription_id="sub_xyz",
            metadata={"org_id": "org_123", "tier": "pro"},
        )

        # Get subscription status
        billing = await service.get_organization_billing("org_123")
    """

    def __init__(
        self,
        supabase: SupabaseClient | None = None,
        stripe_client: StripeClient | None = None,
    ):
        """
        Initialize subscription service.

        Args:
            supabase: Supabase client for database operations
            stripe_client: Stripe client for API calls
        """
        self._supabase = supabase
        self._stripe_client = stripe_client or get_stripe_client()

    # ========================================================================
    # Webhook Event Handlers
    # ========================================================================

    async def handle_webhook_event(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Route webhook event to appropriate handler.

        Args:
            event: Parsed Stripe webhook event

        Returns:
            Result dict with handled status
        """
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.paid": self._handle_invoice_paid,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
            logger.info(f"[BILLING] Handled event: {event.event_type}")
            return {"handled": True, "event_type": event.event_type}

        logger.debug(f"[BILLING] Unhandled event type: {event.event_type}")
        return {"handled": False, "event_type": event.event_type}

    async def _handle_checkout_completed(self, event: WebhookEvent) -> None:
        """Handle successful checkout - create/update subscription."""
        data = event.data

        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        metadata_raw = data.get("metadata", {})
        metadata: dict[str, Any] = (
            dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
        )

        org_id = metadata.get("org_id")
        tier_str = str(metadata.get("tier", "basic"))

        if not org_id or not customer_id or not subscription_id:
            logger.warning("[BILLING] Checkout completed but missing required data")
            return

        try:
            tier = BillingTier(tier_str)
        except ValueError:
            tier = BillingTier.BASIC

        await self.handle_checkout_completed(
            customer_id=str(customer_id),
            subscription_id=str(subscription_id),
            org_id=str(org_id),
            tier=tier,
        )

    async def _handle_invoice_paid(self, event: WebhookEvent) -> None:
        """Handle successful payment - extend subscription."""
        data = event.data

        subscription_id = data.get("subscription")
        if subscription_id:
            await self.handle_invoice_paid(subscription_id=subscription_id)

    async def _handle_subscription_updated(self, event: WebhookEvent) -> None:
        """Handle subscription update (plan change, status change)."""
        data = event.data

        subscription_id = data.get("id")
        status = data.get("status")
        metadata = data.get("metadata", {})
        tier_str = metadata.get("tier")

        if subscription_id and status:
            try:
                tier = BillingTier(tier_str) if tier_str else None
            except ValueError:
                tier = None

            await self.handle_subscription_updated(
                subscription_id=subscription_id,
                new_status=status,
                new_tier=tier,
            )

    async def _handle_subscription_deleted(self, event: WebhookEvent) -> None:
        """Handle subscription cancellation/deletion."""
        data = event.data

        subscription_id = data.get("id")
        if subscription_id:
            await self.handle_subscription_deleted(subscription_id=subscription_id)

    # ========================================================================
    # Business Logic
    # ========================================================================

    async def handle_checkout_completed(
        self,
        customer_id: str,
        subscription_id: str,
        org_id: str,
        tier: BillingTier,
    ) -> None:
        """
        Handle successful checkout - update org tier and quotas.

        Args:
            customer_id: Stripe customer ID
            subscription_id: Stripe subscription ID
            org_id: Organization ID
            tier: New subscription tier
        """
        logger.info(
            f"[BILLING] Checkout completed: org={org_id} tier={tier.value} "
            f"customer={customer_id}"
        )

        # Update organization in database
        await self._update_organization(
            org_id=org_id,
            tier=tier,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_status=SubscriptionStatus.ACTIVE,
        )

        # Record billing event
        await self._record_billing_event(
            org_id=org_id,
            event_type="checkout_completed",
            payload={
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "tier": tier.value,
            },
        )

    async def handle_invoice_paid(self, subscription_id: str) -> None:
        """
        Handle successful payment - extend subscription.

        Args:
            subscription_id: Stripe subscription ID
        """
        logger.info(f"[BILLING] Invoice paid for subscription={subscription_id}")

        # Get subscription details from Stripe
        if self._stripe_client.is_configured:
            try:
                sub_data = await self._stripe_client.get_subscription(subscription_id)
                org_id = sub_data.get("metadata", {}).get("org_id")

                if org_id:
                    await self._update_organization(
                        org_id=org_id,
                        subscription_status=SubscriptionStatus.ACTIVE,
                        current_period_end=sub_data.get("current_period_end"),
                    )
            except Exception as e:
                logger.error(f"[BILLING] Failed to process invoice.paid: {e}")

    async def handle_subscription_updated(
        self,
        subscription_id: str,
        new_status: str,
        new_tier: BillingTier | None = None,
    ) -> None:
        """
        Handle plan changes or status changes.

        Args:
            subscription_id: Stripe subscription ID
            new_status: New subscription status from Stripe
            new_tier: New tier if changed
        """
        logger.info(
            f"[BILLING] Subscription updated: {subscription_id} "
            f"status={new_status} tier={new_tier}"
        )

        status = StripeClient.map_stripe_status(new_status)

        # Look up org by subscription ID
        org_billing = await self._get_org_by_subscription(subscription_id)
        if not org_billing:
            logger.warning(f"[BILLING] No org found for subscription {subscription_id}")
            return

        update_data: dict[str, Any] = {"subscription_status": status}
        if new_tier:
            update_data["tier"] = new_tier

        await self._update_organization(org_id=org_billing.org_id, **update_data)

    async def handle_subscription_deleted(self, subscription_id: str) -> None:
        """
        Handle subscription cancellation - downgrade to free tier.

        Args:
            subscription_id: Stripe subscription ID
        """
        logger.info(f"[BILLING] Subscription deleted: {subscription_id}")

        # Look up org by subscription ID
        org_billing = await self._get_org_by_subscription(subscription_id)
        if not org_billing:
            logger.warning(f"[BILLING] No org found for subscription {subscription_id}")
            return

        await self._update_organization(
            org_id=org_billing.org_id,
            tier=BillingTier.FREE,
            subscription_status=SubscriptionStatus.CANCELED,
            stripe_subscription_id=None,  # Clear subscription
        )

        await self._record_billing_event(
            org_id=org_billing.org_id,
            event_type="subscription_deleted",
            payload={"subscription_id": subscription_id},
        )

    # ========================================================================
    # Query Methods
    # ========================================================================

    async def get_organization_billing(self, org_id: str) -> OrganizationBilling:
        """
        Get billing status for an organization.

        Args:
            org_id: Organization ID

        Returns:
            OrganizationBilling with current status
        """
        if not self._supabase:
            # Return default free tier if no database
            return OrganizationBilling(org_id=org_id)

        try:
            result = (
                self._supabase.table("organizations")
                .select(
                    "id, tier, stripe_customer_id, stripe_subscription_id, "
                    "subscription_status, current_period_end, cancel_at_period_end"
                )
                .eq("id", org_id)
                .single()
                .execute()
            )

            if result.data:
                data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
                return OrganizationBilling(
                    org_id=org_id,
                    tier=BillingTier(str(data.get("tier", "free"))),
                    stripe_customer_id=data.get("stripe_customer_id"),
                    stripe_subscription_id=data.get("stripe_subscription_id"),
                    subscription_status=SubscriptionStatus(
                        str(data.get("subscription_status", "free"))
                    ),
                    current_period_end=data.get("current_period_end"),
                    cancel_at_period_end=bool(data.get("cancel_at_period_end", False)),
                )

        except Exception as e:
            logger.error(f"[BILLING] Failed to get org billing: {e}")

        return OrganizationBilling(org_id=org_id)

    # ========================================================================
    # Database Operations
    # ========================================================================

    async def _update_organization(
        self,
        org_id: str,
        tier: BillingTier | None = None,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        subscription_status: SubscriptionStatus | None = None,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool | None = None,
    ) -> None:
        """Update organization billing fields in database."""
        if not self._supabase:
            logger.debug("[BILLING] No database, skipping org update")
            return

        update_data: dict[str, Any] = {}

        if tier is not None:
            update_data["tier"] = tier.value
        if stripe_customer_id is not None:
            update_data["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id is not None:
            update_data["stripe_subscription_id"] = stripe_subscription_id
        if subscription_status is not None:
            update_data["subscription_status"] = subscription_status.value
        if current_period_end is not None:
            update_data["current_period_end"] = current_period_end.isoformat()
        if cancel_at_period_end is not None:
            update_data["cancel_at_period_end"] = cancel_at_period_end

        if not update_data:
            return

        try:
            self._supabase.table("organizations").update(update_data).eq(
                "id", org_id
            ).execute()

            logger.info(f"[BILLING] Updated org {org_id}: {list(update_data.keys())}")

        except Exception as e:
            logger.error(f"[BILLING] Failed to update org: {e}")

    async def _get_org_by_subscription(
        self, subscription_id: str
    ) -> OrganizationBilling | None:
        """Look up organization by Stripe subscription ID."""
        if not self._supabase:
            return None

        try:
            result = (
                self._supabase.table("organizations")
                .select("id, tier, subscription_status")
                .eq("stripe_subscription_id", subscription_id)
                .single()
                .execute()
            )

            if result.data:
                data: dict[str, Any] = dict(result.data)  # type: ignore[arg-type]
                return OrganizationBilling(
                    org_id=str(data["id"]),
                    tier=BillingTier(str(data.get("tier", "free"))),
                    stripe_subscription_id=subscription_id,
                )

        except Exception as e:
            logger.error(f"[BILLING] Failed to lookup org by subscription: {e}")

        return None

    async def _record_billing_event(
        self,
        org_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Record billing event for audit trail."""
        if not self._supabase:
            return

        try:
            self._supabase.table("billing_events").insert(
                {
                    "organization_id": org_id,
                    "stripe_event_id": f"internal_{event_type}_{org_id}",
                    "event_type": event_type,
                    "payload": payload,
                }
            ).execute()

        except Exception as e:
            logger.error(f"[BILLING] Failed to record billing event: {e}")


# ============================================================================
# Global service
# ============================================================================

_subscription_service: SubscriptionService | None = None


def get_subscription_service(
    supabase: SupabaseClient | None = None,
) -> SubscriptionService:
    """Get or create the global subscription service."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService(supabase=supabase)
    return _subscription_service
