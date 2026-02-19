"""FastAPI application for agent orchestration.

Endpoints:
- POST /agents/run - Start agent execution
- GET /agents/{session_id} - Poll session status
- POST /agents/{session_id}/cancel - Cancel running session
- POST /agents/route - Auto-classify and route task to chain
- GET /agents/route/{job_id} - Poll router job status and results
- GET /agents/route/chains - List available chains
- POST /billing/checkout - Create Stripe Checkout session
- GET /billing/subscription - Get subscription status
- POST /billing/portal - Create Customer Portal session
- POST /billing/webhooks/stripe - Handle Stripe webhooks
- GET /tools - List available tools
- GET /health - Health check
"""

from __future__ import annotations

# Load environment variables before any other imports
from dotenv import load_dotenv

load_dotenv()

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agents.runner import AgentRunner
from src.agents.schemas import (
    AgentRunRequest,
    SessionStatus,
)
from src.agents.state import StateManager
from src.billing import billing_router
from src.demo.router import router as demo_router
from src.knowledge.cache import KnowledgeCache
from src.router.api import router as agent_router
from src.routers.connectors import router as connectors_router
from src.storyboard.router import router as storyboard_router
from src.tools.registry import ToolRegistry
from src.tools.video.demo_pipeline_router import router as demo_pipeline_router

logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan: Startup/Shutdown Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for the application."""
    # Startup: Load knowledge cache
    cache = KnowledgeCache.get()
    try:
        await cache.load()
        logger.info(f"Knowledge cache loaded: {cache.stats()}")
    except Exception as e:
        logger.warning(f"Knowledge cache failed to load (non-fatal): {e}")
        # Non-fatal - storyboards still work with static presets

    yield

    # Shutdown: Nothing to clean up (cache is just memory)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Epiphan Storyboard API",
    description="AI-powered storyboard generator for Epiphan Video",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(storyboard_router)
app.include_router(demo_router)
app.include_router(agent_router)
app.include_router(billing_router)
app.include_router(connectors_router)
app.include_router(demo_pipeline_router)

# Serve static files (demo web UI)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Redirect root to demo UI."""
    return FileResponse("static/demo.html")


# ============================================================================
# Dependencies
# ============================================================================


def get_state_manager() -> StateManager:
    """Dependency to get StateManager instance."""
    return StateManager(
        redis_url=os.getenv("REDIS_URL"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
    )


def get_tool_registry() -> ToolRegistry:
    """Dependency to get ToolRegistry instance."""
    return ToolRegistry()


def get_anthropic_client() -> Any:
    """Dependency to get Anthropic client."""
    try:
        import anthropic

        return anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    except ImportError:
        return None


def get_openrouter_client() -> httpx.AsyncClient:
    """Dependency to get OpenRouter HTTP client."""
    return httpx.AsyncClient(timeout=60.0)


# ============================================================================
# Response Models
# ============================================================================


class RunResponse(BaseModel):
    """Response from POST /agents/run."""

    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(..., description="Initial session status")
    poll_url: str = Field(..., description="URL to poll for updates")


class SessionResponse(BaseModel):
    """Response from GET /agents/{session_id}."""

    session_id: str
    status: str
    steps: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    total_cost_usd: float


class CancelResponse(BaseModel):
    """Response from POST /agents/{session_id}/cancel."""

    session_id: str
    status: str
    message: str


class ToolInfo(BaseModel):
    """Tool information in list response."""

    name: str
    description: str
    category: str
    parameters: dict[str, Any]
    requires_approval: bool


class ToolsResponse(BaseModel):
    """Response from GET /tools."""

    tools: list[ToolInfo]


class HealthResponse(BaseModel):
    """Response from GET /health."""

    status: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# ============================================================================
# Background Task
# ============================================================================


async def run_agent_task(
    request: AgentRunRequest,
    org_id: str,
    state_manager: StateManager,
    tool_registry: ToolRegistry,
    anthropic_client: Any,
    openrouter_client: httpx.AsyncClient,
) -> None:
    """Background task to run agent execution."""
    runner = AgentRunner(
        state_manager=state_manager,
        tool_registry=tool_registry,
        anthropic_client=anthropic_client,
        openrouter_client=openrouter_client,
    )
    await runner.run(request, org_id=org_id)


# ============================================================================
# Endpoints
# ============================================================================


@app.post(
    "/agents/run",
    response_model=RunResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def run_agent(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    x_org_id: str | None = Header(None, alias="X-Org-ID"),
    state_manager: StateManager = Depends(get_state_manager),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    anthropic_client: Any = Depends(get_anthropic_client),
    openrouter_client: httpx.AsyncClient = Depends(get_openrouter_client),
) -> RunResponse:
    """
    Start agent execution.

    Returns immediately with session ID and poll URL.
    Actual execution runs in background.
    """
    # Validate org_id
    if not x_org_id:
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")

    # Validate tools exist if specified
    if request.tools:
        for tool_name in request.tools:
            if not tool_registry.has(tool_name):
                raise HTTPException(
                    status_code=400, detail=f"Tool '{tool_name}' not found in registry"
                )

    # Create session
    session = await state_manager.create_session(
        org_id=x_org_id,
        model=request.model,
    )

    # Start background execution
    background_tasks.add_task(
        run_agent_task,
        request=request,
        org_id=x_org_id,
        state_manager=state_manager,
        tool_registry=tool_registry,
        anthropic_client=anthropic_client,
        openrouter_client=openrouter_client,
    )

    return RunResponse(
        session_id=session.session_id,
        status=session.status.value,
        poll_url=f"/agents/{session.session_id}",
    )


@app.get(
    "/agents/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_session(
    session_id: str,
    state_manager: StateManager = Depends(get_state_manager),
) -> SessionResponse:
    """
    Get session status and steps.

    Use this to poll for completion.
    """
    session = await state_manager.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Convert steps to dicts
    steps = [step.model_dump() for step in session.steps]

    return SessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        steps=steps,
        input_tokens=session.input_tokens,
        output_tokens=session.output_tokens,
        total_cost_usd=session.total_cost_usd,
    )


@app.post(
    "/agents/{session_id}/cancel",
    response_model=CancelResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def cancel_session(
    session_id: str,
    state_manager: StateManager = Depends(get_state_manager),
) -> CancelResponse:
    """
    Cancel a running session.

    Idempotent for already cancelled sessions.
    Returns 409 for completed or failed sessions.
    """
    session = await state_manager.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Check if already cancelled (idempotent)
    if session.status == SessionStatus.CANCELLED:
        return CancelResponse(
            session_id=session_id,
            status="cancelled",
            message="Session was already cancelled",
        )

    # Cannot cancel completed or failed sessions
    if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel session with status '{session.status.value}'",
        )

    # Cancel the session
    session.status = SessionStatus.CANCELLED
    await state_manager.update_session(session)

    return CancelResponse(
        session_id=session_id,
        status="cancelled",
        message="Session cancelled successfully",
    )


@app.get(
    "/tools",
    response_model=ToolsResponse,
)
async def list_tools(
    category: str | None = Query(None, description="Filter by category"),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
) -> ToolsResponse:
    """
    List available tools.

    Optionally filter by category.
    """
    all_tools = tool_registry.list_tools()

    # Filter by category if specified
    if category:
        all_tools = [t for t in all_tools if t.category.value == category]

    tools = [
        ToolInfo(
            name=t.name,
            description=t.description,
            category=t.category.value,
            parameters=t.parameters,
            requires_approval=t.requires_approval,
        )
        for t in all_tools
    ]

    return ToolsResponse(tools=tools)


@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns healthy status if API is running.
    """
    return HealthResponse(status="healthy")
