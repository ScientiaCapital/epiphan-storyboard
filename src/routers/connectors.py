"""FastAPI router for Enterprise Data Connectors API.

Endpoints:
- GET /connectors - List available connector types
- GET /connectors/instances - List org's connector instances
- GET /connectors/instances/{instance_id} - Get instance details
- POST /connectors/{connector_type}/oauth/authorize - Start OAuth flow
- POST /connectors/{connector_type}/oauth/callback - Handle OAuth callback
- POST /connectors/{connector_type}/connect - Connect with API key
- POST /connectors/instances/{instance_id}/sync - Trigger sync
- GET /connectors/instances/{instance_id}/sync-history - Get sync history
- DELETE /connectors/instances/{instance_id} - Disconnect connector
- POST /connectors/instances/{instance_id}/upload - Manual upload (Loom/Miro)
- POST /connectors/linear/webhook - Linear webhook handler
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from supabase import Client, create_client
except ImportError:
    Client = None
    create_client = None

from src.connectors.base import (
    AuthType,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    OAuthTokens,
    SyncResult,
)
from src.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ConnectorInfo(BaseModel):
    """Connector metadata for listing available connectors."""

    type: str = Field(..., description="Connector type identifier")
    display_name: str = Field(..., description="Human-readable connector name")
    description: str = Field(..., description="Brief description")
    auth_type: str = Field(..., description="Authentication type: oauth2, api_key, manual")
    supports_webhook: bool = Field(..., description="Whether webhooks are supported")
    required_config_fields: list[str] = Field(
        ..., description="Required config field names"
    )


class ConnectorInstanceResponse(BaseModel):
    """Connector instance details."""

    id: str
    org_id: str
    connector_type: str
    status: str
    last_sync_at: str | None = None
    next_sync_at: str | None = None
    items_synced: int = 0
    error_message: str | None = None
    error_count: int = 0
    created_at: str
    updated_at: str


class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization URL response."""

    authorize_url: str = Field(..., description="OAuth authorization URL to redirect to")
    state: str = Field(..., description="State parameter for CSRF protection")


class ConnectAPIKeyRequest(BaseModel):
    """Request to connect a connector using API key."""

    api_key: str = Field(..., description="API key for authentication")
    config: dict = Field(default_factory=dict, description="Additional config")


class ManualUploadRequest(BaseModel):
    """Request for manual content upload (Loom/Miro)."""

    content: str = Field(..., description="Transcript text or base64 image data")
    url: str | None = Field(None, description="Source URL if available")
    title: str | None = Field(None, description="Content title")


class SyncResponse(BaseModel):
    """Sync operation result."""

    success: bool
    items_fetched: int = 0
    items_extracted: int = 0
    items_created: int = 0
    items_skipped: int = 0
    error_message: str | None = None


class SyncRunResponse(BaseModel):
    """Sync run history entry."""

    id: str
    started_at: str
    completed_at: str | None
    status: str
    items_fetched: int
    items_extracted: int
    items_created: int
    items_skipped: int
    error_log: dict | None = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request body."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter for verification")


# ============================================================================
# Dependencies
# ============================================================================


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client singleton."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set as environment variables"
        )

    if create_client is None:
        raise ImportError("supabase package is required. Install with: pip install supabase")

    return create_client(supabase_url, supabase_key)


@lru_cache()
def get_redis_client() -> aioredis.Redis:
    """Get Redis client singleton."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL must be set as environment variable")

    return aioredis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


def get_oauth_provider(connector_type: str):
    """Get OAuth provider for a connector type."""
    from src.connectors.oauth import (
        GongOAuthProvider,
        GoogleOAuthProvider,
        LinearOAuthProvider,
        NotionOAuthProvider,
    )

    provider_map = {
        ConnectorType.GONG.value: GongOAuthProvider,
        ConnectorType.LINEAR.value: LinearOAuthProvider,
        ConnectorType.NOTION.value: NotionOAuthProvider,
        ConnectorType.GOOGLE_DOCS.value: GoogleOAuthProvider,
    }

    provider_class = provider_map.get(connector_type)
    if not provider_class:
        raise ValueError(f"No OAuth provider for connector type: {connector_type}")

    return provider_class()


# ============================================================================
# Helper Functions
# ============================================================================


def _serialize_instance(row: dict) -> ConnectorInstanceResponse:
    """Convert Supabase row to ConnectorInstanceResponse."""
    return ConnectorInstanceResponse(
        id=str(row["id"]),
        org_id=row["org_id"],
        connector_type=row["connector_type"],
        status=row["status"],
        last_sync_at=row["last_sync_at"].isoformat() if row.get("last_sync_at") else None,
        next_sync_at=row["next_sync_at"].isoformat() if row.get("next_sync_at") else None,
        items_synced=row.get("items_synced", 0),
        error_message=row.get("error_message"),
        error_count=row.get("error_count", 0),
        created_at=row["created_at"].isoformat() if row.get("created_at") else datetime.now(timezone.utc).isoformat(),
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else datetime.now(timezone.utc).isoformat(),
    )


async def _run_sync_task(
    instance_id: str,
    org_id: str,
    full: bool,
    supabase: Client,
) -> None:
    """Background task to run connector sync."""
    from src.connectors.registry import ConnectorRegistry

    try:
        # Get instance from database
        response = (
            supabase.table("connector_instances")
            .select("*")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not response.data:
            logger.error(f"Instance {instance_id} not found for org {org_id}")
            return

        row = response.data

        # Convert to ConnectorInstance
        instance = ConnectorInstance(
            id=str(row["id"]),
            org_id=row["org_id"],
            connector_type=ConnectorType(row["connector_type"]),
            status=ConnectorStatus(row["status"]),
            oauth_tokens=OAuthTokens(**row["oauth_tokens"]) if row.get("oauth_tokens") else None,
            config=row.get("config", {}),
            last_sync_at=row.get("last_sync_at"),
            next_sync_at=row.get("next_sync_at"),
            sync_cursor=row.get("sync_cursor"),
            items_synced=row.get("items_synced", 0),
            error_message=row.get("error_message"),
            error_count=row.get("error_count", 0),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
            updated_at=row.get("updated_at", datetime.now(timezone.utc)),
        )

        # Update status to syncing
        supabase.table("connector_instances").update(
            {"status": ConnectorStatus.SYNCING.value, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", instance_id).execute()

        # Create sync run record
        sync_run_response = (
            supabase.table("sync_runs")
            .insert(
                {
                    "connector_instance_id": instance_id,
                    "status": "running",
                    "cursor_before": instance.sync_cursor,
                }
            )
            .execute()
        )
        sync_run_id = sync_run_response.data[0]["id"]

        # Get connector and run sync
        registry = ConnectorRegistry.get()
        connector = registry.get_connector(instance.connector_type)

        if full:
            result = await connector.full_sync(instance)
        else:
            result = await connector.sync(instance)

        # Update instance
        update_data = {
            "status": ConnectorStatus.CONNECTED.value if result.success else ConnectorStatus.ERROR.value,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "items_synced": instance.items_synced + result.items_created,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if result.success:
            update_data["error_count"] = 0
            update_data["error_message"] = None
            if result.cursor_after:
                update_data["sync_cursor"] = result.cursor_after
            # Schedule next sync in 1 hour
            update_data["next_sync_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        else:
            update_data["error_count"] = instance.error_count + 1
            update_data["error_message"] = result.error_message

        supabase.table("connector_instances").update(update_data).eq("id", instance_id).execute()

        # Update sync run
        supabase.table("sync_runs").update(
            {
                "status": "success" if result.success else "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "items_fetched": result.items_fetched,
                "items_extracted": result.items_extracted,
                "items_created": result.items_created,
                "items_skipped": result.items_skipped,
                "cursor_after": result.cursor_after,
                "error_log": {"message": result.error_message, "errors": result.errors} if not result.success else None,
            }
        ).eq("id", sync_run_id).execute()

        logger.info(f"Sync completed for instance {instance_id}: {result.items_created} items created")

    except Exception as e:
        logger.error(f"Sync task failed for instance {instance_id}: {e}")
        # Update instance status to error
        try:
            supabase.table("connector_instances").update(
                {
                    "status": ConnectorStatus.ERROR.value,
                    "error_message": str(e),
                    "error_count": instance.error_count + 1 if 'instance' in locals() else 1,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", instance_id).execute()
        except Exception as persist_error:
            logger.error(f"Failed to persist error for instance {instance_id}: {persist_error}")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[ConnectorInfo],
    summary="List available connectors",
    description="Get list of all available connector types with their metadata",
)
async def list_available_connectors() -> list[ConnectorInfo]:
    """List all available connector types."""
    registry = ConnectorRegistry.get()
    connectors = registry.list_available()

    return [
        ConnectorInfo(
            type=c["type"],
            display_name=c["display_name"],
            description=c["description"],
            auth_type=c["auth_type"],
            supports_webhook=c["supports_webhook"],
            required_config_fields=c["required_config_fields"],
        )
        for c in connectors
    ]


@router.get(
    "/instances",
    response_model=list[ConnectorInstanceResponse],
    summary="List organization's connectors",
    description="Get all connector instances for the requesting organization",
)
async def list_org_connectors(
    org_id: str = Header(..., alias="X-Org-ID"),
) -> list[ConnectorInstanceResponse]:
    """List all connector instances for this organization."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    response = (
        supabase.table("connector_instances")
        .select("*")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [_serialize_instance(row) for row in response.data]


@router.get(
    "/instances/{instance_id}",
    response_model=ConnectorInstanceResponse,
    summary="Get connector instance",
    description="Get details for a specific connector instance",
    responses={404: {"description": "Instance not found"}},
)
async def get_connector_instance(
    instance_id: str,
    org_id: str = Header(..., alias="X-Org-ID"),
) -> ConnectorInstanceResponse:
    """Get connector instance details."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("connector_instances")
            .select("*")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")

        return _serialize_instance(response.data)

    except Exception as e:
        if "PGRST116" in str(e):  # Supabase error code for no rows
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        raise


@router.post(
    "/{connector_type}/oauth/authorize",
    response_model=OAuthAuthorizeResponse,
    summary="Start OAuth flow",
    description="Get OAuth authorization URL to redirect user to",
    responses={400: {"description": "Invalid connector type or OAuth not supported"}},
)
async def start_oauth(
    connector_type: str,
    org_id: str = Header(..., alias="X-Org-ID"),
    redirect_uri: str | None = None,
) -> OAuthAuthorizeResponse:
    """Get OAuth authorization URL for a connector."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Validate connector type
    try:
        ConnectorType(connector_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid connector type: {connector_type}")

    # Get OAuth provider
    try:
        provider = get_oauth_provider(connector_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate state token
    state = secrets.token_urlsafe(32)

    # Store state in Redis with org_id for callback verification (1 hour TTL)
    redis = get_redis_client()
    await redis.setex(
        f"oauth:state:{state}",
        3600,
        f"{org_id}:{connector_type}",
    )

    # Build authorization URL
    default_redirect = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/connectors/oauth/callback")
    auth_url = provider.build_authorize_url(redirect_uri or default_redirect, state)

    logger.info(f"Started OAuth flow for {connector_type} (org={org_id})")

    return OAuthAuthorizeResponse(authorize_url=auth_url, state=state)


@router.post(
    "/{connector_type}/oauth/callback",
    response_model=ConnectorInstanceResponse,
    summary="Handle OAuth callback",
    description="Exchange authorization code for tokens and create connector instance",
    responses={
        400: {"description": "Invalid state or code"},
        409: {"description": "Connector already exists for this org"},
    },
)
async def oauth_callback(
    connector_type: str,
    request: OAuthCallbackRequest,
) -> ConnectorInstanceResponse:
    """Handle OAuth callback, exchange code for tokens, create instance."""
    redis = get_redis_client()

    # Verify state and get org_id
    state_data = await redis.get(f"oauth:state:{request.state}")
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    org_id, stored_connector_type = state_data.split(":", 1)

    if stored_connector_type != connector_type:
        raise HTTPException(status_code=400, detail="Connector type mismatch")

    # Delete state token (one-time use)
    await redis.delete(f"oauth:state:{request.state}")

    # Get OAuth provider and exchange code
    try:
        provider = get_oauth_provider(connector_type)
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/connectors/oauth/callback")
        token_response = await provider.exchange_code(request.code, redirect_uri)
    except Exception as e:
        logger.error(f"OAuth code exchange failed for {connector_type}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to exchange authorization code: {e}")

    # Create connector instance
    supabase = get_supabase_client()

    # Check if instance already exists
    existing = (
        supabase.table("connector_instances")
        .select("id")
        .eq("org_id", org_id)
        .eq("connector_type", connector_type)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=f"Connector '{connector_type}' already exists for this organization",
        )

    # Create new instance
    instance_data = {
        "org_id": org_id,
        "connector_type": connector_type,
        "status": ConnectorStatus.CONNECTED.value,
        "oauth_tokens": {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "expires_at": token_response.expires_at.isoformat() if token_response.expires_at else None,
            "token_type": token_response.token_type,
            "scope": token_response.scope,
        },
        "config": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    response = supabase.table("connector_instances").insert(instance_data).execute()

    logger.info(f"Created connector instance for {connector_type} (org={org_id})")

    return _serialize_instance(response.data[0])


@router.post(
    "/{connector_type}/connect",
    response_model=ConnectorInstanceResponse,
    summary="Connect with API key",
    description="Connect a connector using API key authentication",
    responses={
        400: {"description": "Invalid credentials or config"},
        409: {"description": "Connector already exists for this org"},
    },
)
async def connect_api_key(
    connector_type: str,
    request: ConnectAPIKeyRequest,
    org_id: str = Header(..., alias="X-Org-ID"),
) -> ConnectorInstanceResponse:
    """Connect a connector using API key authentication."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Validate connector type
    try:
        ct = ConnectorType(connector_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid connector type: {connector_type}")

    # Get connector and validate auth type
    registry = ConnectorRegistry.get()
    connector = registry.get_connector(ct)

    if connector.auth_type != AuthType.API_KEY:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_type}' does not support API key authentication",
        )

    # Store API key in config
    config = request.config.copy()
    config["api_key"] = request.api_key

    # Validate config
    valid, error = connector.validate_config(config)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    # Create instance
    instance = ConnectorInstance.create_new(
        org_id=org_id,
        connector_type=ct,
        config=config,
    )

    # Test connection
    try:
        connection_ok = await connector.test_connection(instance)
        if not connection_ok:
            raise HTTPException(status_code=400, detail="Connection test failed - invalid credentials")
    except Exception as e:
        logger.error(f"Connection test failed for {connector_type}: {e}")
        raise HTTPException(status_code=400, detail=f"Connection test failed: {e}")

    # Save to database
    supabase = get_supabase_client()

    # Check if instance already exists
    existing = (
        supabase.table("connector_instances")
        .select("id")
        .eq("org_id", org_id)
        .eq("connector_type", connector_type)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=f"Connector '{connector_type}' already exists for this organization",
        )

    instance_data = {
        "org_id": org_id,
        "connector_type": connector_type,
        "status": ConnectorStatus.CONNECTED.value,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    response = supabase.table("connector_instances").insert(instance_data).execute()

    logger.info(f"Connected {connector_type} with API key (org={org_id})")

    return _serialize_instance(response.data[0])


@router.post(
    "/instances/{instance_id}/sync",
    response_model=dict,
    summary="Trigger sync",
    description="Manually trigger a sync for a connector instance",
    responses={
        404: {"description": "Instance not found"},
        409: {"description": "Sync already in progress"},
    },
)
async def trigger_sync(
    instance_id: str,
    background_tasks: BackgroundTasks,
    org_id: str = Header(..., alias="X-Org-ID"),
    full: bool = False,
) -> dict:
    """Trigger a sync for a connector instance."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    # Get instance and verify org_id
    try:
        response = (
            supabase.table("connector_instances")
            .select("*")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")

        row = response.data

        # Check if already syncing
        if row["status"] == ConnectorStatus.SYNCING.value:
            raise HTTPException(status_code=409, detail="Sync already in progress")

    except HTTPException:
        raise
    except Exception as e:
        if "PGRST116" in str(e):
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        raise

    # Add sync task to background
    background_tasks.add_task(
        _run_sync_task,
        instance_id=instance_id,
        org_id=org_id,
        full=full,
        supabase=supabase,
    )

    logger.info(f"Triggered {'full' if full else 'incremental'} sync for instance {instance_id}")

    return {
        "message": "Sync started",
        "instance_id": instance_id,
        "sync_type": "full" if full else "incremental",
    }


@router.get(
    "/instances/{instance_id}/sync-history",
    response_model=list[SyncRunResponse],
    summary="Get sync history",
    description="Get sync run history for a connector instance",
    responses={404: {"description": "Instance not found"}},
)
async def get_sync_history(
    instance_id: str,
    org_id: str = Header(..., alias="X-Org-ID"),
    limit: int = 10,
) -> list[SyncRunResponse]:
    """Get sync run history for a connector."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    # Verify instance exists and belongs to org
    try:
        instance_response = (
            supabase.table("connector_instances")
            .select("id")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not instance_response.data:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        if "PGRST116" in str(e):
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        raise

    # Get sync runs
    response = (
        supabase.table("sync_runs")
        .select("*")
        .eq("connector_instance_id", instance_id)
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [
        SyncRunResponse(
            id=str(row["id"]),
            started_at=row["started_at"],
            completed_at=row.get("completed_at"),
            status=row["status"],
            items_fetched=row.get("items_fetched", 0),
            items_extracted=row.get("items_extracted", 0),
            items_created=row.get("items_created", 0),
            items_skipped=row.get("items_skipped", 0),
            error_log=row.get("error_log"),
        )
        for row in response.data
    ]


@router.delete(
    "/instances/{instance_id}",
    response_model=dict,
    summary="Disconnect connector",
    description="Disconnect and delete a connector instance",
    responses={404: {"description": "Instance not found"}},
)
async def disconnect(
    instance_id: str,
    org_id: str = Header(..., alias="X-Org-ID"),
) -> dict:
    """Disconnect and delete a connector instance."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    # Verify instance exists and belongs to org
    try:
        response = (
            supabase.table("connector_instances")
            .select("id")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        if "PGRST116" in str(e):
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        raise

    # Delete instance (cascade deletes sync_runs)
    supabase.table("connector_instances").delete().eq("id", instance_id).execute()

    logger.info(f"Deleted connector instance {instance_id} (org={org_id})")

    return {"message": "Connector disconnected", "instance_id": instance_id}


@router.post(
    "/instances/{instance_id}/upload",
    response_model=SyncResponse,
    summary="Manual upload",
    description="Upload content for manual connectors (Loom/Miro)",
    responses={
        400: {"description": "Invalid connector type or content"},
        404: {"description": "Instance not found"},
    },
)
async def manual_upload(
    instance_id: str,
    request: ManualUploadRequest,
    org_id: str = Header(..., alias="X-Org-ID"),
) -> SyncResponse:
    """Upload content for manual connectors (Loom/Miro)."""
    if not org_id or not org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    supabase = get_supabase_client()

    # Get instance and verify it's a manual connector
    try:
        response = (
            supabase.table("connector_instances")
            .select("*")
            .eq("id", instance_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")

        row = response.data
        connector_type = ConnectorType(row["connector_type"])

        if connector_type not in [ConnectorType.LOOM, ConnectorType.MIRO]:
            raise HTTPException(
                status_code=400,
                detail=f"Manual upload not supported for connector type: {connector_type.value}",
            )

    except HTTPException:
        raise
    except Exception as e:
        if "PGRST116" in str(e):
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        raise

    # TODO: Implement manual upload logic with connectors
    # This would call the appropriate connector's upload method
    # For now, return a placeholder response

    logger.info(f"Manual upload to instance {instance_id} (type={connector_type.value})")

    return SyncResponse(
        success=True,
        items_fetched=1,
        items_extracted=1,
        items_created=1,
        items_skipped=0,
    )


@router.post(
    "/linear/webhook",
    response_model=dict,
    summary="Linear webhook handler",
    description="Handle Linear webhook events for real-time syncing",
)
async def linear_webhook(request: Request) -> dict:
    """Handle Linear webhook events."""
    # Get signature from headers
    signature = request.headers.get("Linear-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Linear-Signature header")

    # Get payload
    payload = await request.body()

    # TODO: Verify signature
    # webhook_secret = os.getenv("LINEAR_WEBHOOK_SECRET")
    # if not verify_linear_signature(payload, signature, webhook_secret):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    # TODO: Process webhook event
    # This would trigger a sync for the affected connector instance

    logger.info(f"Received Linear webhook: {data.get('action', 'unknown')}")

    return {"message": "Webhook received", "action": data.get("action")}
