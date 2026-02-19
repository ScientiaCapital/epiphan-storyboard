"""Tests for Stripe client wrapper."""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("stripe")

from src.billing.schemas import BillingTier, SubscriptionStatus
from src.billing.stripe_client import (
    StripeClient,
    StripeClientError,
    StripeConfigError,
    get_stripe_client,
)


class TestStripeClientInit:
    """Tests for StripeClient initialization."""

    def test_init_with_secret_key(self):
        """Should initialize with provided secret key."""
        client = StripeClient(secret_key="sk_test_123")
        assert client.is_configured

    def test_init_from_env(self):
        """Should initialize from environment variable."""
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_env"}):
            client = StripeClient()
            assert client.is_configured

    def test_init_not_configured(self):
        """Should report not configured when no key provided."""
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}, clear=True):
            client = StripeClient(secret_key="")
            assert not client.is_configured


class TestStripeClientCheckout:
    """Tests for checkout session creation."""

    @pytest.fixture
    def client(self):
        """Create configured Stripe client."""
        return StripeClient(secret_key="sk_test_123")

    @pytest.fixture
    def mock_session(self):
        """Create mock Stripe session."""
        session = MagicMock()
        session.url = "https://checkout.stripe.com/c/pay/cs_test_123"
        session.id = "cs_test_123"
        return session

    async def test_create_checkout_session_success(self, client, mock_session):
        """Should create checkout session successfully."""
        with (
            patch.dict(os.environ, {"STRIPE_PRICE_ID_PRO": "price_pro_123"}),
            patch("stripe.checkout.Session.create", return_value=mock_session),
        ):
            response = await client.create_checkout_session(
                org_id="org_123",
                tier=BillingTier.PRO,
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel",
            )

            assert response.checkout_url == mock_session.url
            assert response.session_id == "cs_test_123"

    async def test_create_checkout_session_not_configured(self):
        """Should raise when Stripe is not configured."""
        client = StripeClient(secret_key="")

        with pytest.raises(StripeConfigError, match="not configured"):
            await client.create_checkout_session(
                org_id="org_123",
                tier=BillingTier.PRO,
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel",
            )

    async def test_create_checkout_session_no_price_id(self, client):
        """Should raise when price ID is not configured."""
        with patch.dict(os.environ, {"STRIPE_PRICE_ID_PRO": ""}, clear=True):
            with pytest.raises(StripeConfigError, match="Price ID not configured"):
                await client.create_checkout_session(
                    org_id="org_123",
                    tier=BillingTier.PRO,
                    success_url="https://app.example.com/success",
                    cancel_url="https://app.example.com/cancel",
                )

    async def test_create_checkout_session_with_customer_id(self, client, mock_session):
        """Should pass customer ID when provided."""
        with (
            patch.dict(os.environ, {"STRIPE_PRICE_ID_BASIC": "price_basic_123"}),
            patch("stripe.checkout.Session.create", return_value=mock_session) as mock_create,
        ):
            await client.create_checkout_session(
                org_id="org_123",
                tier=BillingTier.BASIC,
                success_url="https://app.example.com/success",
                cancel_url="https://app.example.com/cancel",
                customer_id="cus_existing",
            )

            call_args = mock_create.call_args
            assert call_args.kwargs["customer"] == "cus_existing"


class TestStripeClientPortal:
    """Tests for customer portal session creation."""

    @pytest.fixture
    def client(self):
        """Create configured Stripe client."""
        return StripeClient(secret_key="sk_test_123")

    @pytest.fixture
    def mock_portal_session(self):
        """Create mock Stripe portal session."""
        session = MagicMock()
        session.url = "https://billing.stripe.com/p/session/test_123"
        return session

    async def test_create_portal_session_success(self, client, mock_portal_session):
        """Should create portal session successfully."""
        with patch(
            "stripe.billing_portal.Session.create",
            return_value=mock_portal_session,
        ):
            response = await client.create_portal_session(
                customer_id="cus_123",
                return_url="https://app.example.com/settings",
            )

            assert response.portal_url == mock_portal_session.url

    async def test_create_portal_session_not_configured(self):
        """Should raise when Stripe is not configured."""
        client = StripeClient(secret_key="")

        with pytest.raises(StripeConfigError, match="not configured"):
            await client.create_portal_session(
                customer_id="cus_123",
                return_url="https://app.example.com/settings",
            )


class TestStripeClientSubscription:
    """Tests for subscription management."""

    @pytest.fixture
    def client(self):
        """Create configured Stripe client."""
        return StripeClient(secret_key="sk_test_123")

    @pytest.fixture
    def mock_subscription(self):
        """Create mock Stripe subscription."""
        sub = MagicMock()
        sub.id = "sub_123"
        sub.status = "active"
        sub.current_period_end = 1735084800  # 2024-12-25
        sub.cancel_at_period_end = False
        sub.customer = "cus_123"
        sub.metadata = {"org_id": "org_123", "tier": "pro"}
        return sub

    async def test_get_subscription_success(self, client, mock_subscription):
        """Should get subscription successfully."""
        with patch("stripe.Subscription.retrieve", return_value=mock_subscription):
            result = await client.get_subscription("sub_123")

            assert result["id"] == "sub_123"
            assert result["status"] == "active"
            assert result["cancel_at_period_end"] is False
            assert result["customer"] == "cus_123"

    async def test_cancel_subscription_at_period_end(self, client, mock_subscription):
        """Should cancel subscription at period end."""
        mock_subscription.cancel_at_period_end = True

        with patch("stripe.Subscription.modify", return_value=mock_subscription):
            result = await client.cancel_subscription("sub_123", at_period_end=True)

            assert result["cancel_at_period_end"] is True

    async def test_cancel_subscription_immediately(self, client, mock_subscription):
        """Should cancel subscription immediately."""
        mock_subscription.status = "canceled"

        with patch("stripe.Subscription.cancel", return_value=mock_subscription):
            result = await client.cancel_subscription("sub_123", at_period_end=False)

            assert result["status"] == "canceled"


class TestStripeClientWebhook:
    """Tests for webhook verification."""

    @pytest.fixture
    def client(self):
        """Create configured Stripe client with webhook secret."""
        return StripeClient(
            secret_key="sk_test_123",
            webhook_secret="whsec_test_123",
        )

    @pytest.fixture
    def mock_event(self):
        """Create mock Stripe webhook event."""
        event = MagicMock()
        event.id = "evt_123"
        event.type = "checkout.session.completed"
        event.data.object = {
            "customer": "cus_abc",
            "subscription": "sub_xyz",
        }
        event.created = 1735084800
        return event

    def test_verify_webhook_success(self, client, mock_event):
        """Should verify and parse webhook successfully."""
        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            result = client.verify_webhook_signature(
                payload=b'{"type": "checkout.session.completed"}',
                signature="t=123,v1=abc",
            )

            assert result.event_id == "evt_123"
            assert result.event_type == "checkout.session.completed"
            assert result.data["customer"] == "cus_abc"

    def test_verify_webhook_no_secret(self):
        """Should raise when webhook secret is not configured."""
        client = StripeClient(secret_key="sk_test_123", webhook_secret="")

        with pytest.raises(StripeConfigError, match="Webhook secret not configured"):
            client.verify_webhook_signature(
                payload=b"{}",
                signature="t=123,v1=abc",
            )


class TestStripeStatusMapping:
    """Tests for Stripe status mapping."""

    def test_map_active_status(self):
        """Should map active status correctly."""
        assert StripeClient.map_stripe_status("active") == SubscriptionStatus.ACTIVE

    def test_map_canceled_status(self):
        """Should map canceled status correctly."""
        assert StripeClient.map_stripe_status("canceled") == SubscriptionStatus.CANCELED

    def test_map_past_due_status(self):
        """Should map past_due status correctly."""
        assert StripeClient.map_stripe_status("past_due") == SubscriptionStatus.PAST_DUE

    def test_map_trialing_status(self):
        """Should map trialing status correctly."""
        assert StripeClient.map_stripe_status("trialing") == SubscriptionStatus.TRIALING

    def test_map_unknown_status_to_free(self):
        """Should map unknown status to FREE."""
        assert StripeClient.map_stripe_status("unknown") == SubscriptionStatus.FREE


class TestGetStripeClient:
    """Tests for global client accessor."""

    def test_get_stripe_client_singleton(self):
        """Should return same client instance."""
        # Reset global client for test isolation
        import src.billing.stripe_client as module
        module._stripe_client = None

        client1 = get_stripe_client()
        client2 = get_stripe_client()

        assert client1 is client2

        # Cleanup
        module._stripe_client = None
