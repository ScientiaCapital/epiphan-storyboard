"""Tests for billing API router."""

import pytest

pytest.importorskip("stripe")

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.billing.router import router
from src.billing.schemas import (
    BillingTier,
    CheckoutResponse,
    OrganizationBilling,
    PortalResponse,
    SubscriptionStatus,
    WebhookEvent,
)
from src.billing.stripe_client import StripeClientError, StripeConfigError


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestCheckoutEndpoint:
    """Tests for POST /billing/checkout."""

    def test_create_checkout_success(self, client):
        """Should create checkout session successfully."""
        mock_response = CheckoutResponse(
            checkout_url="https://checkout.stripe.com/test",
            session_id="cs_test_123",
        )
        mock_billing = OrganizationBilling(org_id="org_123")

        with (
            patch(
                "src.billing.router.get_stripe_client"
            ) as mock_get_stripe,
            patch(
                "src.billing.router.get_subscription_service"
            ) as mock_get_service,
        ):
            mock_stripe = MagicMock()
            mock_stripe.create_checkout_session = AsyncMock(return_value=mock_response)
            mock_get_stripe.return_value = mock_stripe

            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/billing/checkout",
                json={
                    "tier": "pro",
                    "success_url": "https://app.example.com/success",
                    "cancel_url": "https://app.example.com/cancel",
                },
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["checkout_url"] == "https://checkout.stripe.com/test"
            assert data["session_id"] == "cs_test_123"

    def test_create_checkout_missing_org_id(self, client):
        """Should return 422 when X-Org-ID header is missing."""
        response = client.post(
            "/billing/checkout",
            json={
                "tier": "pro",
                "success_url": "https://app.example.com/success",
                "cancel_url": "https://app.example.com/cancel",
            },
        )

        assert response.status_code == 422

    def test_create_checkout_invalid_tier(self, client):
        """Should return 400 for free tier checkout."""
        with (
            patch("src.billing.router.get_stripe_client"),
            patch("src.billing.router.get_subscription_service"),
        ):
            response = client.post(
                "/billing/checkout",
                json={
                    "tier": "free",
                    "success_url": "https://app.example.com/success",
                    "cancel_url": "https://app.example.com/cancel",
                },
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 400
            assert "Cannot checkout for tier" in response.json()["detail"]

    def test_create_checkout_stripe_not_configured(self, client):
        """Should return 503 when Stripe is not configured."""
        mock_billing = OrganizationBilling(org_id="org_123")

        with (
            patch("src.billing.router.get_stripe_client") as mock_get_stripe,
            patch("src.billing.router.get_subscription_service") as mock_get_service,
        ):
            mock_stripe = MagicMock()
            mock_stripe.create_checkout_session = AsyncMock(
                side_effect=StripeConfigError("Not configured")
            )
            mock_get_stripe.return_value = mock_stripe

            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/billing/checkout",
                json={
                    "tier": "basic",
                    "success_url": "https://app.example.com/success",
                    "cancel_url": "https://app.example.com/cancel",
                },
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 503


class TestSubscriptionEndpoint:
    """Tests for GET /billing/subscription."""

    def test_get_subscription_free_tier(self, client):
        """Should return free tier for new org."""
        mock_billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.FREE,
            subscription_status=SubscriptionStatus.FREE,
        )

        with patch("src.billing.router.get_subscription_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.get(
                "/billing/subscription",
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tier"] == "free"
            assert data["status"] == "free"

    def test_get_subscription_active(self, client):
        """Should return active subscription details."""
        mock_billing = OrganizationBilling(
            org_id="org_123",
            tier=BillingTier.PRO,
            subscription_status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_abc",
            stripe_subscription_id="sub_xyz",
            current_period_end=datetime(2025, 1, 24, tzinfo=timezone.utc),
        )

        with patch("src.billing.router.get_subscription_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.get(
                "/billing/subscription",
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tier"] == "pro"
            assert data["status"] == "active"
            assert data["stripe_customer_id"] == "cus_abc"


class TestPortalEndpoint:
    """Tests for POST /billing/portal."""

    def test_create_portal_success(self, client):
        """Should create portal session successfully."""
        mock_response = PortalResponse(
            portal_url="https://billing.stripe.com/portal/test"
        )
        mock_billing = OrganizationBilling(
            org_id="org_123",
            stripe_customer_id="cus_abc",
        )

        with (
            patch("src.billing.router.get_stripe_client") as mock_get_stripe,
            patch("src.billing.router.get_subscription_service") as mock_get_service,
        ):
            mock_stripe = MagicMock()
            mock_stripe.create_portal_session = AsyncMock(return_value=mock_response)
            mock_get_stripe.return_value = mock_stripe

            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/billing/portal",
                json={"return_url": "https://app.example.com/settings"},
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["portal_url"] == "https://billing.stripe.com/portal/test"

    def test_create_portal_no_subscription(self, client):
        """Should return 400 when no subscription exists."""
        mock_billing = OrganizationBilling(
            org_id="org_123",
            stripe_customer_id=None,  # No customer
        )

        with (
            patch("src.billing.router.get_stripe_client"),
            patch("src.billing.router.get_subscription_service") as mock_get_service,
        ):
            mock_service = MagicMock()
            mock_service.get_organization_billing = AsyncMock(return_value=mock_billing)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/billing/portal",
                json={"return_url": "https://app.example.com/settings"},
                headers={"X-Org-ID": "org_123"},
            )

            assert response.status_code == 400
            assert "No subscription found" in response.json()["detail"]


class TestWebhookEndpoint:
    """Tests for POST /billing/webhooks/stripe."""

    def test_webhook_success(self, client):
        """Should process valid webhook successfully."""
        mock_event = WebhookEvent(
            event_id="evt_123",
            event_type="checkout.session.completed",
            data={"customer": "cus_abc"},
            created_at=datetime.now(timezone.utc),
        )

        with (
            patch("src.billing.router.get_stripe_client") as mock_get_stripe,
            patch("src.billing.router.get_subscription_service") as mock_get_service,
        ):
            mock_stripe = MagicMock()
            mock_stripe.verify_webhook_signature = MagicMock(return_value=mock_event)
            mock_get_stripe.return_value = mock_stripe

            mock_service = MagicMock()
            mock_service.handle_webhook_event = AsyncMock(
                return_value={"handled": True, "event_type": "checkout.session.completed"}
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/billing/webhooks/stripe",
                content=b'{"type": "checkout.session.completed"}',
                headers={
                    "Stripe-Signature": "t=123,v1=abc",
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["handled"] is True

    def test_webhook_invalid_signature(self, client):
        """Should return 400 for invalid signature."""
        with patch("src.billing.router.get_stripe_client") as mock_get_stripe:
            mock_stripe = MagicMock()
            mock_stripe.verify_webhook_signature = MagicMock(
                side_effect=StripeClientError("Invalid signature")
            )
            mock_get_stripe.return_value = mock_stripe

            response = client.post(
                "/billing/webhooks/stripe",
                content=b"{}",
                headers={
                    "Stripe-Signature": "invalid",
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 400


class TestHealthEndpoint:
    """Tests for GET /billing/health."""

    def test_health_configured(self, client):
        """Should return ok when Stripe is configured."""
        with patch("src.billing.router.get_stripe_client") as mock_get_stripe:
            mock_stripe = MagicMock()
            mock_stripe.is_configured = True
            mock_get_stripe.return_value = mock_stripe

            response = client.get("/billing/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["stripe_configured"] is True

    def test_health_not_configured(self, client):
        """Should return not_configured when Stripe is not set up."""
        with patch("src.billing.router.get_stripe_client") as mock_get_stripe:
            mock_stripe = MagicMock()
            mock_stripe.is_configured = False
            mock_get_stripe.return_value = mock_stripe

            response = client.get("/billing/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_configured"
            assert data["stripe_configured"] is False
