"""Tests for billing schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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
    TIER_PRICE_ENV_MAP,
)


class TestBillingTier:
    """Tests for BillingTier enum."""

    def test_tier_values(self):
        """All tiers should have correct values."""
        assert BillingTier.FREE.value == "free"
        assert BillingTier.BASIC.value == "basic"
        assert BillingTier.PRO.value == "pro"
        assert BillingTier.ENTERPRISE.value == "enterprise"

    def test_tier_count(self):
        """Should have exactly 4 tiers."""
        assert len(BillingTier) == 4


class TestSubscriptionStatus:
    """Tests for SubscriptionStatus enum."""

    def test_status_values(self):
        """Should have all Stripe subscription statuses plus FREE."""
        statuses = [s.value for s in SubscriptionStatus]
        assert "free" in statuses
        assert "active" in statuses
        assert "canceled" in statuses
        assert "past_due" in statuses
        assert "trialing" in statuses


class TestCheckoutRequest:
    """Tests for CheckoutRequest schema."""

    def test_valid_request(self):
        """Should accept valid checkout request."""
        request = CheckoutRequest(
            tier=BillingTier.PRO,
            success_url="https://app.example.com/success",
            cancel_url="https://app.example.com/cancel",
        )
        assert request.tier == BillingTier.PRO
        assert request.success_url == "https://app.example.com/success"

    def test_missing_tier_raises(self):
        """Should raise on missing tier."""
        with pytest.raises(ValidationError):
            CheckoutRequest(
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel",
            )

    def test_invalid_tier_raises(self):
        """Should raise on invalid tier."""
        with pytest.raises(ValidationError):
            CheckoutRequest(
                tier="invalid_tier",
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel",
            )

    def test_missing_urls_raises(self):
        """Should raise on missing URLs."""
        with pytest.raises(ValidationError):
            CheckoutRequest(tier=BillingTier.BASIC)


class TestCheckoutResponse:
    """Tests for CheckoutResponse schema."""

    def test_valid_response(self):
        """Should accept valid checkout response."""
        response = CheckoutResponse(
            checkout_url="https://checkout.stripe.com/c/pay/cs_test_123",
            session_id="cs_test_123",
        )
        assert response.checkout_url.startswith("https://")
        assert response.session_id == "cs_test_123"


class TestSubscriptionResponse:
    """Tests for SubscriptionResponse schema."""

    def test_free_tier_response(self):
        """Should represent free tier correctly."""
        response = SubscriptionResponse(
            org_id="org_123",
            tier=BillingTier.FREE,
            status=SubscriptionStatus.FREE,
        )
        assert response.tier == BillingTier.FREE
        assert response.stripe_customer_id is None
        assert response.stripe_subscription_id is None
        assert response.cancel_at_period_end is False

    def test_active_subscription_response(self):
        """Should represent active subscription correctly."""
        period_end = datetime(2025, 1, 24, tzinfo=timezone.utc)
        response = SubscriptionResponse(
            org_id="org_123",
            tier=BillingTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_abc123",
            stripe_subscription_id="sub_xyz789",
            current_period_end=period_end,
            cancel_at_period_end=False,
        )
        assert response.tier == BillingTier.PRO
        assert response.status == SubscriptionStatus.ACTIVE
        assert response.stripe_customer_id == "cus_abc123"
        assert response.current_period_end == period_end


class TestPortalRequest:
    """Tests for PortalRequest schema."""

    def test_valid_request(self):
        """Should accept valid portal request."""
        request = PortalRequest(return_url="https://app.example.com/settings")
        assert request.return_url == "https://app.example.com/settings"

    def test_missing_return_url_raises(self):
        """Should raise on missing return URL."""
        with pytest.raises(ValidationError):
            PortalRequest()


class TestPortalResponse:
    """Tests for PortalResponse schema."""

    def test_valid_response(self):
        """Should accept valid portal response."""
        response = PortalResponse(
            portal_url="https://billing.stripe.com/p/session/test_123"
        )
        assert response.portal_url.startswith("https://")


class TestWebhookEvent:
    """Tests for WebhookEvent schema."""

    def test_valid_event(self):
        """Should parse valid webhook event."""
        event = WebhookEvent(
            event_id="evt_123",
            event_type="checkout.session.completed",
            data={"customer": "cus_abc", "subscription": "sub_xyz"},
            created_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert event.event_id == "evt_123"
        assert event.event_type == "checkout.session.completed"
        assert event.data["customer"] == "cus_abc"

    def test_missing_fields_raises(self):
        """Should raise on missing required fields."""
        with pytest.raises(ValidationError):
            WebhookEvent(
                event_id="evt_123",
                # Missing event_type, data, created_at
            )


class TestOrganizationBilling:
    """Tests for OrganizationBilling internal model."""

    def test_free_org_not_paying(self):
        """Free tier org should not be considered paying."""
        org = OrganizationBilling(org_id="org_123")
        assert not org.is_paying()

    def test_active_pro_is_paying(self):
        """Active Pro subscription should be paying."""
        org = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
            subscription_status=SubscriptionStatus.ACTIVE,
        )
        assert org.is_paying()

    def test_canceled_pro_not_paying(self):
        """Canceled subscription should not be paying."""
        org = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
            subscription_status=SubscriptionStatus.CANCELED,
        )
        assert not org.is_paying()

    def test_can_access_tier_same_tier(self):
        """Org should access own tier features."""
        org = OrganizationBilling(org_id="org_123", tier=BillingTier.BASIC)
        assert org.can_access_tier(BillingTier.BASIC)

    def test_can_access_tier_lower_tier(self):
        """Higher tier should access lower tier features."""
        org = OrganizationBilling(org_id="org_123", tier=BillingTier.PRO)
        assert org.can_access_tier(BillingTier.FREE)
        assert org.can_access_tier(BillingTier.BASIC)

    def test_cannot_access_higher_tier(self):
        """Lower tier should not access higher tier features."""
        org = OrganizationBilling(org_id="org_123", tier=BillingTier.BASIC)
        assert not org.can_access_tier(BillingTier.PRO)
        assert not org.can_access_tier(BillingTier.ENTERPRISE)

    def test_enterprise_accesses_all(self):
        """Enterprise should access all tiers."""
        org = OrganizationBilling(org_id="org_123", tier=BillingTier.ENTERPRISE)
        assert org.can_access_tier(BillingTier.FREE)
        assert org.can_access_tier(BillingTier.BASIC)
        assert org.can_access_tier(BillingTier.PRO)
        assert org.can_access_tier(BillingTier.ENTERPRISE)


class TestTierPriceEnvMap:
    """Tests for TIER_PRICE_ENV_MAP constant."""

    def test_basic_price_env(self):
        """Basic tier should map to correct env var."""
        assert TIER_PRICE_ENV_MAP[BillingTier.BASIC] == "STRIPE_PRICE_ID_BASIC"

    def test_pro_price_env(self):
        """Pro tier should map to correct env var."""
        assert TIER_PRICE_ENV_MAP[BillingTier.PRO] == "STRIPE_PRICE_ID_PRO"

    def test_free_not_in_map(self):
        """Free tier should not have a price ID."""
        assert BillingTier.FREE not in TIER_PRICE_ENV_MAP
