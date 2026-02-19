"""Tests for Enterprise Data Connectors API endpoints.

Tests cover:
- Listing available connectors
- OAuth flow (authorize + callback)
- API key connection
- Sync triggering
- Sync history retrieval
- Connector disconnection
- Manual upload (Loom/Miro)
- Linear webhook handling
- Multi-tenant isolation
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.connectors.base import (
    AuthType,
    ConnectorStatus,
    ConnectorType,
    SyncResult,
)
from src.connectors.oauth.base import OAuthTokenResponse


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("src.routers.connectors.get_supabase_client") as mock:
        supabase = MagicMock()
        mock.return_value = supabase
        yield supabase


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("src.routers.connectors.get_redis_client") as mock:
        redis = AsyncMock()
        mock.return_value = redis
        yield redis


@pytest.fixture
def org_id():
    """Test organization ID."""
    return "test-org-123"


@pytest.fixture
def instance_id():
    """Test connector instance ID."""
    return str(uuid4())


# ============================================================================
# Test: List Available Connectors
# ============================================================================


def test_list_available_connectors(client):
    """Test listing all available connector types."""
    response = client.get("/connectors")

    assert response.status_code == 200
    data = response.json()

    # Should return a list
    assert isinstance(data, list)

    # Should have 8 connectors
    assert len(data) == 8

    # Check structure of first connector
    connector = data[0]
    assert "type" in connector
    assert "display_name" in connector
    assert "description" in connector
    assert "auth_type" in connector
    assert "supports_webhook" in connector
    assert "required_config_fields" in connector

    # Verify all connector types are present
    connector_types = {c["type"] for c in data}
    expected_types = {
        "gong",
        "fireflies",
        "linear",
        "notion",
        "google_docs",
        "loom",
        "miro",
        "close",
    }
    assert connector_types == expected_types


def test_list_available_connectors_structure(client):
    """Test that connector info has correct structure."""
    response = client.get("/connectors")
    data = response.json()

    for connector in data:
        # Verify auth_type is valid
        assert connector["auth_type"] in ["oauth2", "api_key", "manual"]

        # Verify boolean field
        assert isinstance(connector["supports_webhook"], bool)

        # Verify list field
        assert isinstance(connector["required_config_fields"], list)


# ============================================================================
# Test: List Organization Connectors
# ============================================================================


def test_list_org_connectors_empty(client, mock_supabase, org_id):
    """Test listing connectors when org has none."""
    # Mock empty response
    mock_response = MagicMock()
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_response
    )

    response = client.get("/connectors/instances", headers={"X-Org-ID": org_id})

    assert response.status_code == 200
    assert response.json() == []


def test_list_org_connectors_with_instances(client, mock_supabase, org_id, instance_id):
    """Test listing connectors when org has instances."""
    # Mock response with instances
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": instance_id,
            "org_id": org_id,
            "connector_type": "gong",
            "status": "connected",
            "last_sync_at": now,
            "next_sync_at": now + timedelta(hours=1),
            "items_synced": 42,
            "error_message": None,
            "error_count": 0,
            "created_at": now,
            "updated_at": now,
        }
    ]
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_response
    )

    response = client.get("/connectors/instances", headers={"X-Org-ID": org_id})

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == instance_id
    assert data[0]["org_id"] == org_id
    assert data[0]["connector_type"] == "gong"
    assert data[0]["status"] == "connected"
    assert data[0]["items_synced"] == 42


def test_list_org_connectors_missing_org_id(client):
    """Test listing connectors without X-Org-ID header."""
    response = client.get("/connectors/instances")

    assert response.status_code == 422  # Validation error


def test_list_org_connectors_empty_org_id(client):
    """Test listing connectors with empty X-Org-ID header."""
    response = client.get("/connectors/instances", headers={"X-Org-ID": "  "})

    assert response.status_code == 400
    assert "X-Org-ID header is required" in response.json()["detail"]


# ============================================================================
# Test: Get Connector Instance
# ============================================================================


def test_get_connector_instance_success(client, mock_supabase, org_id, instance_id):
    """Test getting a specific connector instance."""
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "linear",
        "status": "connected",
        "last_sync_at": now,
        "next_sync_at": None,
        "items_synced": 100,
        "error_message": None,
        "error_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.get(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == instance_id
    assert data["connector_type"] == "linear"
    assert data["items_synced"] == 100


def test_get_connector_instance_not_found(client, mock_supabase, org_id, instance_id):
    """Test getting non-existent connector instance."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.get(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_connector_instance_wrong_org(client, mock_supabase, instance_id):
    """Test getting instance with wrong org_id."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.get(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": "wrong-org"},
    )

    assert response.status_code == 404


# ============================================================================
# Test: OAuth Flow - Authorize
# ============================================================================


@patch("src.routers.connectors.get_oauth_provider")
def test_start_oauth_success(mock_get_provider, client, mock_redis, org_id):
    """Test starting OAuth flow."""
    # Mock OAuth provider
    provider = MagicMock()
    provider.build_authorize_url.return_value = "https://gong.io/oauth/authorize?state=abc123"
    mock_get_provider.return_value = provider

    response = client.post(
        "/connectors/gong/oauth/authorize",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert "authorize_url" in data
    assert "state" in data
    assert data["authorize_url"].startswith("https://gong.io/oauth/authorize")

    # Verify state was stored in Redis
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 3600  # 1 hour TTL
    assert f"{org_id}:gong" == call_args[0][2]


def test_start_oauth_invalid_connector_type(client, org_id):
    """Test starting OAuth with invalid connector type."""
    response = client.post(
        "/connectors/invalid_type/oauth/authorize",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 400
    assert "Invalid connector type" in response.json()["detail"]


def test_start_oauth_non_oauth_connector(client, org_id):
    """Test starting OAuth with non-OAuth connector."""
    response = client.post(
        "/connectors/fireflies/oauth/authorize",  # Fireflies uses API key
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 400
    assert "No OAuth provider" in response.json()["detail"]


def test_start_oauth_missing_org_id(client):
    """Test starting OAuth without org_id."""
    response = client.post("/connectors/gong/oauth/authorize")

    assert response.status_code == 422


# ============================================================================
# Test: OAuth Flow - Callback
# ============================================================================


@patch("src.routers.connectors.get_oauth_provider")
def test_oauth_callback_success(
    mock_get_provider, client, mock_supabase, mock_redis, org_id, instance_id
):
    """Test OAuth callback with successful token exchange."""
    # Mock Redis state retrieval
    mock_redis.get.return_value = f"{org_id}:gong"

    # Mock OAuth provider token exchange
    provider = MagicMock()
    token_response = OAuthTokenResponse(
        access_token="access_token_123",
        refresh_token="refresh_token_456",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        token_type="Bearer",
        scope="read_calls",
    )
    provider.exchange_code = AsyncMock(return_value=token_response)
    mock_get_provider.return_value = provider

    # Mock Supabase: no existing instance
    mock_existing = MagicMock()
    mock_existing.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
        mock_existing
    )

    # Mock Supabase: insert new instance
    now = datetime.now(timezone.utc)
    mock_insert = MagicMock()
    mock_insert.data = [
        {
            "id": instance_id,
            "org_id": org_id,
            "connector_type": "gong",
            "status": "connected",
            "last_sync_at": None,
            "next_sync_at": None,
            "items_synced": 0,
            "error_message": None,
            "error_count": 0,
            "created_at": now,
            "updated_at": now,
        }
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

    response = client.post(
        "/connectors/gong/oauth/callback",
        json={"code": "auth_code_789", "state": "state_token_xyz"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == instance_id
    assert data["org_id"] == org_id
    assert data["connector_type"] == "gong"
    assert data["status"] == "connected"

    # Verify state was deleted (one-time use)
    mock_redis.delete.assert_called_once_with("oauth:state:state_token_xyz")


def test_oauth_callback_invalid_state(client, mock_redis):
    """Test OAuth callback with invalid state."""
    mock_redis.get.return_value = None

    response = client.post(
        "/connectors/gong/oauth/callback",
        json={"code": "auth_code", "state": "invalid_state"},
    )

    assert response.status_code == 400
    assert "Invalid or expired state" in response.json()["detail"]


def test_oauth_callback_connector_type_mismatch(client, mock_redis):
    """Test OAuth callback with mismatched connector type."""
    mock_redis.get.return_value = "test-org:linear"  # State says linear

    response = client.post(
        "/connectors/gong/oauth/callback",  # But request is for gong
        json={"code": "auth_code", "state": "state_token"},
    )

    assert response.status_code == 400
    assert "Connector type mismatch" in response.json()["detail"]


@patch("src.routers.connectors.get_oauth_provider")
def test_oauth_callback_already_exists(mock_get_provider, client, mock_supabase, mock_redis, org_id):
    """Test OAuth callback when connector already exists."""
    mock_redis.get.return_value = f"{org_id}:gong"

    # Mock OAuth provider
    provider = MagicMock()
    token_response = OAuthTokenResponse(access_token="token")
    provider.exchange_code = AsyncMock(return_value=token_response)
    mock_get_provider.return_value = provider

    # Mock Supabase: instance already exists
    mock_existing = MagicMock()
    mock_existing.data = [{"id": "existing_id"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
        mock_existing
    )

    response = client.post(
        "/connectors/gong/oauth/callback",
        json={"code": "auth_code", "state": "state_token"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# ============================================================================
# Test: API Key Connection
# ============================================================================


@patch("src.connectors.registry.ConnectorRegistry.get")
def test_connect_api_key_success(mock_registry, client, mock_supabase, org_id, instance_id):
    """Test connecting a connector with API key."""
    # Mock connector
    connector = MagicMock()
    connector.auth_type = AuthType.API_KEY
    connector.validate_config.return_value = (True, None)
    connector.test_connection = AsyncMock(return_value=True)

    mock_registry.return_value.get_connector.return_value = connector

    # Mock Supabase: no existing instance
    mock_existing = MagicMock()
    mock_existing.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
        mock_existing
    )

    # Mock Supabase: insert new instance
    now = datetime.now(timezone.utc)
    mock_insert = MagicMock()
    mock_insert.data = [
        {
            "id": instance_id,
            "org_id": org_id,
            "connector_type": "fireflies",
            "status": "connected",
            "last_sync_at": None,
            "next_sync_at": None,
            "items_synced": 0,
            "error_message": None,
            "error_count": 0,
            "created_at": now,
            "updated_at": now,
        }
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

    response = client.post(
        "/connectors/fireflies/connect",
        headers={"X-Org-ID": org_id},
        json={"api_key": "fireflies_api_key_123", "config": {}},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["connector_type"] == "fireflies"
    assert data["status"] == "connected"


def test_connect_api_key_wrong_auth_type(client, org_id):
    """Test connecting with API key when connector requires OAuth."""
    response = client.post(
        "/connectors/gong/connect",  # Gong uses OAuth
        headers={"X-Org-ID": org_id},
        json={"api_key": "invalid", "config": {}},
    )

    assert response.status_code == 400
    assert "does not support API key" in response.json()["detail"]


@patch("src.connectors.registry.ConnectorRegistry.get")
def test_connect_api_key_connection_test_fails(mock_registry, client, org_id):
    """Test connecting with invalid API key."""
    # Mock connector with failed connection test
    connector = MagicMock()
    connector.auth_type = AuthType.API_KEY
    connector.validate_config.return_value = (True, None)
    connector.test_connection = AsyncMock(return_value=False)

    mock_registry.return_value.get_connector.return_value = connector

    response = client.post(
        "/connectors/fireflies/connect",
        headers={"X-Org-ID": org_id},
        json={"api_key": "invalid_key", "config": {}},
    )

    assert response.status_code == 400
    assert "Connection test failed" in response.json()["detail"]


# ============================================================================
# Test: Trigger Sync
# ============================================================================


def test_trigger_sync_success(client, mock_supabase, org_id, instance_id):
    """Test triggering a sync."""
    # Mock instance retrieval
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "gong",
        "status": "connected",
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.post(
        f"/connectors/instances/{instance_id}/sync",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Sync started"
    assert data["instance_id"] == instance_id
    assert data["sync_type"] == "incremental"


def test_trigger_sync_full_mode(client, mock_supabase, org_id, instance_id):
    """Test triggering a full sync."""
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "gong",
        "status": "connected",
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.post(
        f"/connectors/instances/{instance_id}/sync?full=true",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["sync_type"] == "full"


def test_trigger_sync_already_syncing(client, mock_supabase, org_id, instance_id):
    """Test triggering sync when already in progress."""
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "gong",
        "status": "syncing",  # Already syncing
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.post(
        f"/connectors/instances/{instance_id}/sync",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 409
    assert "already in progress" in response.json()["detail"]


def test_trigger_sync_not_found(client, mock_supabase, org_id, instance_id):
    """Test triggering sync for non-existent instance."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.post(
        f"/connectors/instances/{instance_id}/sync",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 404


# ============================================================================
# Test: Sync History
# ============================================================================


def test_get_sync_history_success(client, mock_supabase, org_id, instance_id):
    """Test getting sync history."""
    # Mock instance exists
    mock_instance = MagicMock()
    mock_instance.data = {"id": instance_id}
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_instance
    )

    # Mock sync runs
    now = datetime.now(timezone.utc)
    mock_runs = MagicMock()
    mock_runs.data = [
        {
            "id": str(uuid4()),
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(minutes=5)).isoformat(),
            "status": "success",
            "items_fetched": 50,
            "items_extracted": 50,
            "items_created": 45,
            "items_skipped": 5,
            "error_log": None,
        },
        {
            "id": str(uuid4()),
            "started_at": (now - timedelta(hours=1)).isoformat(),
            "completed_at": (now - timedelta(hours=1) + timedelta(minutes=3)).isoformat(),
            "status": "success",
            "items_fetched": 30,
            "items_extracted": 30,
            "items_created": 28,
            "items_skipped": 2,
            "error_log": None,
        },
    ]
    # Need to mock the full chain for sync_runs query
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
        mock_runs
    )

    response = client.get(
        f"/connectors/instances/{instance_id}/sync-history",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["status"] == "success"
    assert data[0]["items_created"] == 45


def test_get_sync_history_with_limit(client, mock_supabase, org_id, instance_id):
    """Test getting sync history with custom limit."""
    mock_instance = MagicMock()
    mock_instance.data = {"id": instance_id}
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_instance
    )

    mock_runs = MagicMock()
    mock_runs.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
        mock_runs
    )

    response = client.get(
        f"/connectors/instances/{instance_id}/sync-history?limit=5",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200


def test_get_sync_history_instance_not_found(client, mock_supabase, org_id, instance_id):
    """Test getting sync history for non-existent instance."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.get(
        f"/connectors/instances/{instance_id}/sync-history",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 404


# ============================================================================
# Test: Disconnect
# ============================================================================


def test_disconnect_success(client, mock_supabase, org_id, instance_id):
    """Test disconnecting a connector."""
    # Mock instance exists
    mock_instance = MagicMock()
    mock_instance.data = {"id": instance_id}
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_instance
    )

    # Mock delete
    mock_delete = MagicMock()
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
        mock_delete
    )

    response = client.delete(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Connector disconnected"
    assert data["instance_id"] == instance_id


def test_disconnect_not_found(client, mock_supabase, org_id, instance_id):
    """Test disconnecting non-existent connector."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.delete(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": org_id},
    )

    assert response.status_code == 404


# ============================================================================
# Test: Manual Upload
# ============================================================================


def test_manual_upload_loom(client, mock_supabase, org_id, instance_id):
    """Test manual upload for Loom connector."""
    from src.connectors.base import SyncResult

    # Mock Loom instance
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "loom",
        "status": "connected",
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    mock_result = SyncResult(success=True, items_fetched=1, items_extracted=1, items_created=1)
    with patch("src.connectors.loom.connector.LoomConnector.upload_transcript", new=AsyncMock(return_value=mock_result)):
        response = client.post(
            f"/connectors/instances/{instance_id}/upload",
            headers={"X-Org-ID": org_id},
            json={
                "content": "This is a Loom transcript...",
                "url": "https://loom.com/share/xyz",
                "title": "Product Demo",
            },
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["items_created"] >= 0


def test_manual_upload_miro(client, mock_supabase, org_id, instance_id):
    """Test manual upload for Miro connector."""
    import base64
    from src.connectors.base import SyncResult

    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "miro",
        "status": "connected",
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    mock_result = SyncResult(success=True, items_fetched=1, items_extracted=1, items_created=1)
    with patch("src.connectors.miro.connector.MiroConnector.upload_screenshot", new=AsyncMock(return_value=mock_result)):
        response = client.post(
            f"/connectors/instances/{instance_id}/upload",
            headers={"X-Org-ID": org_id},
            json={
                "content": base64.b64encode(b"fake png data").decode(),
                "url": "https://miro.com/board/xyz",
            },
        )

    assert response.status_code == 200


def test_manual_upload_wrong_connector_type(client, mock_supabase, org_id, instance_id):
    """Test manual upload for non-manual connector."""
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.data = {
        "id": instance_id,
        "org_id": org_id,
        "connector_type": "gong",  # Not a manual connector
        "status": "connected",
        "created_at": now,
        "updated_at": now,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.post(
        f"/connectors/instances/{instance_id}/upload",
        headers={"X-Org-ID": org_id},
        json={"content": "test"},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]




# ============================================================================
# Test: Multi-Tenant Isolation
# ============================================================================


def test_multi_tenant_isolation_list(client, mock_supabase):
    """Test that org1 cannot see org2's connectors."""
    org1 = "org-1"
    org2 = "org-2"

    # Mock response for org1
    mock_response = MagicMock()
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_response
    )

    # Org1 requests
    response = client.get("/connectors/instances", headers={"X-Org-ID": org1})
    assert response.status_code == 200

    # Verify Supabase query filtered by org1
    mock_supabase.table.return_value.select.return_value.eq.assert_called_with("org_id", org1)


def test_multi_tenant_isolation_get(client, mock_supabase, instance_id):
    """Test that org cannot access another org's instance."""
    mock_response = MagicMock()
    mock_response.data = None  # No data because org_id doesn't match
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.get(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": "wrong-org"},
    )

    assert response.status_code == 404


def test_multi_tenant_isolation_delete(client, mock_supabase, instance_id):
    """Test that org cannot delete another org's instance."""
    mock_response = MagicMock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = (
        mock_response
    )

    response = client.delete(
        f"/connectors/instances/{instance_id}",
        headers={"X-Org-ID": "wrong-org"},
    )

    assert response.status_code == 404
