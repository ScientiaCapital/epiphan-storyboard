"""Demo router for interactive storyboard generation.

Endpoints:
- GET /demo/examples - List available example code files
- GET /demo/examples/{name} - Get code content for an example
- POST /demo/generate - Generate storyboard from image or code
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.tools.storyboard.unified_storyboard import UnifiedStoryboardTool
from src.tools.storyboard.storage import get_storage

logger = logging.getLogger(__name__)

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(prefix="/demo", tags=["demo"])

# ============================================================================
# Example Code Files
# ============================================================================

EXAMPLES = [
    {
        "name": "video_script_generator",
        "path": "src/tools/video/video_script_generator.py",
        "description": "AI-powered video script generation using DeepSeek V3",
    },
    {
        "name": "unified_storyboard",
        "path": "src/tools/storyboard/unified_storyboard.py",
        "description": "Convert any input to PNG storyboard via Gemini",
    },
    {
        "name": "video_scheduler",
        "path": "src/tools/video/video_scheduler.py",
        "description": "Optimal send time prediction for video prospecting",
    },
    {
        "name": "video_analytics",
        "path": "src/tools/video/video_analytics.py",
        "description": "Loom view tracking and engagement scoring",
    },
    {
        "name": "gemini_client",
        "path": "src/tools/storyboard/gemini_client.py",
        "description": "Gemini Vision + Image Generation client",
    },
    {
        "name": "video_generator",
        "path": "src/tools/video/video_generator.py",
        "description": "Multi-provider video generation (Kling/HaiLuo/Runway)",
    },
    {
        "name": "video_template_manager",
        "path": "src/tools/video/video_template_manager.py",
        "description": "Industry-specific video templates (solar, hvac, electrical)",
    },
]

# ============================================================================
# Request/Response Models
# ============================================================================


class ExampleInfo(BaseModel):
    """Example code file information."""

    name: str = Field(..., description="Example name")
    path: str = Field(..., description="Relative path to file")
    description: str = Field(..., description="Brief description")


class ExamplesResponse(BaseModel):
    """Response from GET /demo/examples."""

    examples: list[ExampleInfo]


class ExampleCodeResponse(BaseModel):
    """Response from GET /demo/examples/{name}."""

    name: str
    path: str
    description: str
    code: str = Field(..., description="File contents")
    line_count: int = Field(..., description="Number of lines")


class GenerateRequest(BaseModel):
    """Request for POST /demo/generate."""

    # input_type is now optional - auto-inferred from provided fields
    input_type: Literal["image", "code"] | None = Field(
        None,
        description="Type of input: 'image' or 'code'. Auto-inferred if not provided.",
    )
    image_base64: str | None = Field(
        None,
        description="Base64-encoded image (with or without data URL prefix). For single image.",
    )
    images_base64: list[str] | None = Field(
        None,
        description="Multiple base64-encoded images (up to 3). Use for combining CTO roadmap + Miro + campaigns.",
    )
    code: str | None = Field(
        None,
        description="Raw code string.",
    )
    icp_preset: str = Field(
        "coperniq_mep",
        description="ICP preset to use",
    )
    stage: Literal["preview", "demo", "shipped"] = Field(
        "demo",
        description="Storyboard stage for BDR cadence",
    )
    audience: Literal[
        "business_owner", "c_suite", "btl_champion", "top_tier_vc", "field_crew"
    ] = Field(
        "field_crew",
        description="Target audience persona",
    )
    output_format: Literal["infographic", "storyboard"] = Field(
        "infographic",
        description="Output format: 'infographic' (horizontal 16:9) or 'storyboard' (vertical 9:16)",
    )
    visual_style: Literal["clean", "polished", "photo_realistic", "minimalist", "isometric", "sketch", "data_viz", "bold"] = Field(
        "polished",
        description="Visual style: 'clean', 'polished', 'photo_realistic', 'minimalist', 'isometric' (3D Stripe/Linear), 'sketch' (whiteboard), 'data_viz' (charts), 'bold' (Bauhaus)",
    )
    artist_style: str | None = Field(
        None,
        description="Optional artist style: 'salvador_dali', 'monet', 'diego_rivera', 'warhol', 'van_gogh', 'picasso', 'giger' (biomechanical)",
    )


class GenerateResponse(BaseModel):
    """Response from POST /demo/generate."""

    success: bool
    storyboard_png: str | None = Field(
        None, description="Base64-encoded PNG storyboard"
    )
    understanding: dict[str, Any] | None = Field(
        None, description="Extracted business insights"
    )
    storage_url: str | None = Field(
        None, description="Public URL to stored storyboard (if auto-save enabled)"
    )
    input_type: str
    output_format: str
    visual_style: str
    artist_style: str | None = None
    image_count: int = 1
    stage: str
    audience: str
    icp_preset: str
    execution_time_ms: int
    error: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# ============================================================================
# Helper Functions
# ============================================================================


def get_project_root() -> Path:
    """Get the project root directory."""
    # Assumes this file is in src/demo/router.py
    return Path(__file__).parent.parent.parent


def get_example_by_name(name: str) -> dict[str, str] | None:
    """Get example metadata by name."""
    for example in EXAMPLES:
        if example["name"] == name:
            return example
    return None


def read_file_content(relative_path: str) -> str:
    """Read file content from project root."""
    project_root = get_project_root()
    file_path = project_root / relative_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    if not file_path.is_file():
        raise ValueError(f"Not a file: {relative_path}")

    # Security check: ensure file is within project
    try:
        file_path.resolve().relative_to(project_root.resolve())
    except ValueError as e:
        raise ValueError(f"File outside project root: {relative_path}") from e

    with open(file_path) as f:
        return f.read()


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/examples",
    response_model=ExamplesResponse,
    summary="List available example code files",
)
async def list_examples() -> ExamplesResponse:
    """
    List all available example code files.

    Returns metadata for each example including name, path, and description.
    """
    examples = [
        ExampleInfo(
            name=ex["name"],
            path=ex["path"],
            description=ex["description"],
        )
        for ex in EXAMPLES
    ]

    return ExamplesResponse(examples=examples)


@router.get(
    "/examples/{name}",
    response_model=ExampleCodeResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get code content for an example",
)
async def get_example_code(name: str) -> ExampleCodeResponse:
    """
    Get the code content for a specific example.

    Args:
        name: Example name (e.g., 'unified_storyboard')

    Returns:
        Example metadata plus full file contents.

    Raises:
        404: Example not found or file doesn't exist.
    """
    example = get_example_by_name(name)
    if example is None:
        raise HTTPException(status_code=404, detail=f"Example '{name}' not found")

    try:
        code = read_file_content(example["path"])
        line_count = len(code.splitlines())

        return ExampleCodeResponse(
            name=example["name"],
            path=example["path"],
            description=example["description"],
            code=code,
            line_count=line_count,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Generate storyboard from image or code",
)
async def generate_storyboard(request: GenerateRequest, response: Response) -> GenerateResponse:
    """
    Generate executive storyboard PNG from image or code.

    Accepts either:
    - Base64-encoded image (with or without data URL prefix)
    - Raw code string

    Uses UnifiedStoryboardTool with open_browser=False for server-side generation.

    Args:
        request: Generation request with input_type and corresponding data.
        response: FastAPI Response object for setting headers.

    Returns:
        Generated storyboard as base64 PNG with extracted business insights.

    Raises:
        400: Invalid input (missing required fields).
        422: Validation error.
    """
    # Prevent caching - each request must generate fresh content
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # Handle multiple images (up to 3)
    images_list: list[str] = []
    image_count = 0

    if request.images_base64 and len(request.images_base64) > 0:
        # Multiple images provided
        images_list = [img for img in request.images_base64 if img and img.strip()][:3]
        image_count = len(images_list)
    elif request.image_base64 and request.image_base64.strip():
        # Single image provided
        images_list = [request.image_base64]
        image_count = 1

    # Auto-infer input_type if not provided
    # NEW: When BOTH image AND text are provided, use image as primary with text as context
    input_type = request.input_type
    has_code = request.code and request.code.strip()
    supplementary_context = None  # Text context to combine with image

    if input_type is None:
        if image_count > 0 and has_code:
            # MIXED INPUT: Image + text/code together
            # Use image as primary, text as supplementary context
            input_type = "image"
            supplementary_context = request.code.strip()
            logger.info(f"[MIXED INPUT] Image ({image_count}) + text context ({len(supplementary_context)} chars)")
        elif image_count > 0:
            input_type = "image"
        elif has_code:
            input_type = "code"
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'image_base64', 'images_base64', or 'code' must be provided",
            )

    # Validate input based on type
    if input_type == "image":
        if image_count == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one image must be provided when input_type='image'",
            )
        # For multiple images, pass as list; for single, pass the string
        input_value = images_list if image_count > 1 else images_list[0]
    else:  # input_type == "code"
        if not has_code:
            raise HTTPException(
                status_code=400,
                detail="code cannot be empty when input_type='code'",
            )
        input_value = request.code

    # Run UnifiedStoryboardTool
    tool = UnifiedStoryboardTool()
    tool_args = {
        "input": input_value,
        "icp_preset": request.icp_preset,
        "stage": request.stage,
        "audience": request.audience,
        "output_format": request.output_format,
        "visual_style": request.visual_style,
        "open_browser": False,  # Server-side - don't open browser
    }

    # Add supplementary context if we have mixed input (image + text)
    if supplementary_context:
        tool_args["supplementary_context"] = supplementary_context

    # Add artist_style if provided
    if request.artist_style:
        tool_args["artist_style"] = request.artist_style

    result = await tool.run(tool_args)

    if result.success:
        storyboard_png = result.result.get("storyboard_png")
        understanding = result.result.get("understanding")
        storage_url = None

        # Auto-save to Supabase storage
        if storyboard_png:
            try:
                storage = get_storage()
                png_bytes = base64.b64decode(storyboard_png)
                storage_result = await storage.save_storyboard(
                    png_bytes=png_bytes,
                    audience=request.audience,
                    stage=request.stage,
                    input_type=result.result.get("input_type", input_type),
                    headline=understanding.get("headline") if understanding else None,
                    understanding=understanding,
                )
                if storage_result:
                    storage_url = storage_result.get("public_url")
                    logger.info(f"Storyboard saved to storage: {storage_url}")
            except Exception as e:
                logger.warning(f"Failed to save storyboard to storage: {e}")
                # Continue without storage - don't fail the request

        return GenerateResponse(
            success=True,
            storyboard_png=storyboard_png,
            understanding=understanding,
            storage_url=storage_url,
            input_type=result.result.get("input_type", input_type),
            output_format=request.output_format,
            visual_style=request.visual_style,
            artist_style=request.artist_style,
            image_count=image_count,
            stage=request.stage,
            audience=request.audience,
            icp_preset=request.icp_preset,
            execution_time_ms=result.execution_time_ms,
        )
    else:
        return GenerateResponse(
            success=False,
            input_type=input_type,
            output_format=request.output_format,
            visual_style=request.visual_style,
            artist_style=request.artist_style,
            image_count=image_count,
            stage=request.stage,
            audience=request.audience,
            icp_preset=request.icp_preset,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
        )
