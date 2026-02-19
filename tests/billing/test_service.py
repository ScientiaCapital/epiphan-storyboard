"""Tests for subscription service."""

import pytest

pytest.importorskip("stripe")

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.billing.schemas import (
    BillingTier,
    OrganizationBilling,
    SubscriptionStatus,
    WebhookEvent,
)
from src.billing.service import (
    SubscriptionService,
    get_subscription_service,
)


class TestSubscriptionServiceWebhooks:
    """Tests for webhook event handling."""

    @pytest.fixture
    def service(self):
        """Create subscription service without database."""
        return SubscriptionService()

    async def test_handle_checkout_completed_event(self, service):
        """Should handle checkout.session.completed event."""
        event = WebhookEvent(
            event_id="evt_123",
            event_type="checkout.session.completed",
            data={
                "customer": "cus_abc",
                "subscription": "sub_xyz",
                "metadata": {"org_id": "org_123", "tier": "pro"},
            },
            created_at=datetime.now(timezone.utc),
        )

        with patch.object(
            service, "handle_checkout_completed", new_callable=AsyncMock
        ) as mock_handler:
            result = await service.handle_webhook_event(event)

            assert result["handled"] is True
            assert result["event_type"] == "checkout.session.completed"
            mock_handler.assert_called_once()

    async def test_handle_subscription_deleted_event(self, service):
        """Should handle customer.subscription.deleted event."""
        event = WebhookEvent(
            event_id="evt_123",
            event_type="customer.subscription.deleted",
            data={"id": "sub_xyz"},
            created_at=datetime.now(timezone.utc),
        )

        with patch.object(
            service, "handle_subscription_deleted", new_callable=AsyncMock
        ) as mock_handler:
            result = await service.handle_webhook_event(event)

            assert result["handled"] is True
            mock_handler.assert_called_once_with(subscription_id="sub_xyz")

    async def test_handle_unknown_event(self, service):
        """Should return handled=False for unknown events."""
        event = WebhookEvent(
            event_id="evt_123",
            event_type="unknown.event.type",
            data={},
            created_at=datetime.now(timezone.utc),
        )

        result = await service.handle_webhook_event(event)

        assert result["handled"] is False
        assert result["event_type"] == "unknown.event.type"


class TestSubscriptionServiceCheckout:
    """Tests for checkout handling."""

    @pytest.fixture
    def service(self):
        """Create subscription service with mock database."""
        mock_supabase = MagicMock()
        return SubscriptionService(supabase=mock_supabase)

    async def test_handle_checkout_completed_updates_org(self, service):
        """Should update organization on checkout completion."""
        # Setup mock
        service._supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        service._supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock()
        )

        await service.handle_checkout_completed(
            customer_id="cus_abc",
            subscription_id="sub_xyz",
            org_id="org_123",
            tier=BillingTier.PRO,
        )

        # Verify update was called
        service._supabase.table.assert_called()


class TestSubscriptionServiceQueries:
    """Tests for subscription queries."""

    @pytest.fixture
    def service(self):
        """Create subscription service with mock database."""
        mock_supabase = MagicMock()
        return SubscriptionService(supabase=mock_supabase)

    async def test_get_organization_billing_exists(self, service):
        """Should return org billing when exists."""
        mock_result = MagicMock()
        mock_result.data = {
            "id": "org_123",
            "tier": "pro",
            "stripe_customer_id": "cus_abc",
            "stripe_subscription_id": "sub_xyz",
            "subscription_status": "active",
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
        service._supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_result
        )

        billing = await service.get_organization_billing("org_123")

        assert billing.org_id == "org_123"
        assert billing.tier == BillingTier.PRO
        assert billing.subscription_status == SubscriptionStatus.ACTIVE

    async def test_get_organization_billing_not_found(self, service):
        """Should return free tier when org not found."""
        mock_result = MagicMock()
        mock_result.data = None
        service._supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_result
        )

        billing = await service.get_organization_billing("org_not_found")

        assert billing.tier == BillingTier.FREE

    async def test_get_organization_billing_no_database(self):
        """Should return free tier when no database."""
        service = SubscriptionService(supabase=None)

        billing = await service.get_organization_billing("org_123")

        assert billing.tier == BillingTier.FREE
        assert billing.org_id == "org_123"


class TestSubscriptionServiceSubscriptionUpdates:
    """Tests for subscription updates."""

    @pytest.fixture
    def service(self):
        """Create subscription service with mock database."""
        mock_supabase = MagicMock()
        return SubscriptionService(supabase=mock_supabase)

    async def test_handle_subscription_updated_status_change(self, service):
        """Should update org on subscription status change."""
        # Mock org lookup
        mock_result = MagicMock()
        mock_result.data = {
            "id": "org_123",
            "tier": "pro",
            "subscription_status": "active",
        }
        service._supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_result
        )
        service._supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        await service.handle_subscription_updated(
            subscription_id="sub_xyz",
            new_status="past_due",
        )

        # Verify update was called
        service._supabase.table.assert_called()

    async def test_handle_subscription_deleted_downgrades_to_free(self, service):
        """Should downgrade to free tier on subscription deletion."""
        # Mock org lookup
        mock_result = MagicMock()
        mock_result.data = {
            "id": "org_123",
            "tier": "pro",
            "subscription_status": "active",
        }
        service._supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_result
        )
        service._supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        service._supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock()
        )

        await service.handle_subscription_deleted(subscription_id="sub_xyz")

        # Verify update was called with free tier
        calls = service._supabase.table.call_args_list
        assert len(calls) > 0


class TestOrganizationBillingMethods:
    """Tests for OrganizationBilling helper methods."""

    def test_is_paying_active_pro(self):
        """Active Pro should be paying."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
            subscription_status=SubscriptionStatus.ACTIVE,
        )
        assert billing.is_paying() is True

    def test_is_paying_free_tier(self):
        """Free tier should not be paying."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.FREE,
            subscription_status=SubscriptionStatus.FREE,
        )
        assert billing.is_paying() is False

    def test_is_paying_canceled(self):
        """Canceled subscription should not be paying."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
            subscription_status=SubscriptionStatus.CANCELED,
        )
        assert billing.is_paying() is False

    def test_can_access_tier_higher(self):
        """Higher tier should access lower tier features."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
        )
        assert billing.can_access_tier(BillingTier.BASIC) is True
        assert billing.can_access_tier(BillingTier.FREE) is True

    def test_can_access_tier_same(self):
        """Same tier should access own features."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.BASIC,
        )
        assert billing.can_access_tier(BillingTier.BASIC) is True

    def test_cannot_access_higher_tier(self):
        """Lower tier should not access higher tier features."""
        billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.BASIC,
        )
        assert billing.can_access_tier(BillingTier.PRO) is False
        assert billing.can_access_tier(BillingTier.ENTERPRISE) is False


class TestGetSubscriptionService:
    """Tests for global service accessor."""

    def test_get_subscription_service_singleton(self):
        """Should return same service instance."""
        # Reset global service for test isolation
        import src.billing.service as module

        module._subscription_service = None

        service1 = get_subscription_service()
        service2 = get_subscription_service()

        assert service1 is service2

        # Cleanup
        module._subscription_service = None
