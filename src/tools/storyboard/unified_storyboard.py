"""
UnifiedStoryboardTool - The All-in-One Storyboard Generator
============================================================

Generates executive storyboard PNGs from ANY input source:
- Miro board URLs (prompts for screenshot if auth needed)
- Image URLs (.png, .jpg, .jpeg, .webp)
- Base64 image data (data:image/... or raw base64)
- File paths (code files or image files)
- Raw code strings

Auto-detects input type and routes to appropriate handler.
Opens result in browser by default.

NO OpenAI - Gemini only.
"""

import base64
import logging
import os
import tempfile
import webbrowser
from datetime import datetime
from time import perf_counter
from typing import Literal

import httpx

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.storyboard.epiphan_presets import (
    get_audience_persona,
    get_icp_preset,
    sanitize_content,
)
from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    StoryboardUnderstanding,
)
from src.tools.storyboard.quality_gate import (
    find_hero_competitors,
    find_tech_accuracy_violations,
    run_quality_gate,
)

logger = logging.getLogger(__name__)

# Image file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


InputType = Literal["miro_url", "image_url", "image_data", "file_path", "code"]


class UnifiedStoryboardTool(BaseTool):
    """
    Unified storyboard generator that accepts ANY input.

    Automatically detects input type and generates executive-ready PNG storyboards.
    Opens result in default browser for immediate viewing.

    Supported inputs:
    - Miro board URLs: https://miro.com/app/board/...
    - Image URLs: https://example.com/image.png
    - Base64 images: data:image/png;base64,... or raw base64
    - File paths: /path/to/file.py or /path/to/screenshot.png
    - Raw code: def calculate_roi(): return revenue - costs

    Example:
        tool = UnifiedStoryboardTool()

        # From code
        result = await tool.run({
            "input": "def calculate_roi(): return revenue - costs",
            "audience": "av_director",
        })

        # From screenshot
        result = await tool.run({
            "input": "data:image/png;base64,iVBORw0KGgo...",
            "stage": "demo",
        })

        # Result opens in browser automatically
    """

    DEFAULT_TIMEOUT = 90  # seconds

    def __init__(self, gemini_client: GeminiStoryboardClient | None = None):
        """
        Initialize UnifiedStoryboardTool.

        Args:
            gemini_client: Optional pre-configured Gemini client
        """
        self._gemini_client = gemini_client

    @property
    def gemini_client(self) -> GeminiStoryboardClient:
        """Lazy initialization of Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = GeminiStoryboardClient()
        return self._gemini_client

    @property
    def definition(self) -> ToolDefinition:
        """Tool definition for LLM function calling."""
        return ToolDefinition(
            name="unified_storyboard",
            description=(
                "Generate executive storyboard from ANY input source and open in browser. "
                "Accepts Miro URLs, image URLs, base64 images, file paths, or raw code. "
                "Auto-detects input type. Creates beautiful one-page PNG storyboards "
                "showing business value, benefits, and differentiators. "
                "Perfect for sales demos, cold outreach, and stakeholder presentations."
            ),
            category=ToolCategory.DATA,
            parameters={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": (
                            "Any input: Miro URL, image URL, base64 image, "
                            "file path, or raw code string"
                        ),
                    },
                    "icp_preset": {
                        "type": "string",
                        "description": "ICP preset to use (default: epiphan_av)",
                        "default": "epiphan_av",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["preview", "demo", "shipped"],
                        "description": "Storyboard stage for BDR cadence",
                        "default": "preview",
                    },
                    "audience": {
                        "type": "string",
                        "enum": [
                            "av_director",
                            "ld_director",
                            "sim_center_director",
                            "court_admin",
                            "corp_comms",
                            "ehs_manager",
                            "law_firm_it",
                            "provost",
                            "university_president",
                            "university_finance",
                            "edtech_manager",
                            "venue_manager",
                            "production_director",
                            "technical_director",
                            "dealer_dave",
                            "system_engineer",
                        ],
                        "description": "Target audience persona",
                        "default": "av_director",
                    },
                    "vertical": {
                        "type": "string",
                        "enum": [
                            "higher_ed",
                            "corporate",
                            "live_events",
                            "government",
                            "houses_of_worship",
                            "healthcare",
                            "industrial",
                            "legal",
                            "ux_research",
                            "k12",
                        ],
                        "description": "Target vertical/industry for context-aware generation",
                        "default": None,
                    },
                    "open_browser": {
                        "type": "boolean",
                        "description": "Auto-open result in browser (default: true)",
                        "default": True,
                    },
                    "supplementary_context": {
                        "type": "string",
                        "description": "Additional text context (transcript, notes) to combine with image input",
                        "default": None,
                    },
                },
                "required": ["input"],
            },
            requires_approval=False,
        )

    def detect_input_type(self, input_value: str) -> InputType:
        """
        Detect the type of input provided.

        Args:
            input_value: The raw input string

        Returns:
            One of: "miro_url", "image_url", "image_data", "file_path", "code"
        """
        input_value = input_value.strip()

        # Miro board URL
        if input_value.startswith("https://miro.com"):
            return "miro_url"

        # Base64 image data (data URL or raw base64)
        if input_value.startswith("data:image"):
            return "image_data"

        # Image URL (check before generic URL check)
        if input_value.startswith("http"):
            lower = input_value.lower()
            if any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
                return "image_url"

        # File path (only if file actually exists)
        if os.path.isfile(input_value):
            return "file_path"

        # Default: treat as code
        return "code"

    def is_image_file(self, file_path: str) -> bool:
        """Check if a file path points to an image file."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in IMAGE_EXTENSIONS

    def is_transcript(self, content: str) -> bool:
        """
        Detect if text content is a transcript vs code.

        Transcripts have:
        - Natural language sentences
        - Speaker patterns (Name:, Speaker 1:)
        - Conversational markers
        - Few code syntax patterns

        Code has:
        - Syntax keywords (def, class, function, import, etc.)
        - Brackets and indentation patterns
        - Variable declarations
        """
        # Code indicators (more = likely code)
        code_patterns = [
            "def ",
            "class ",
            "function ",
            "import ",
            "from ",
            "const ",
            "let ",
            "var ",
            "async ",
            "await ",
            "return ",
            "if (",
            "for (",
            "while (",
            "->",
            "=>",
            "self.",
            "this.",
            "#!/",
            "# coding:",
            "# -*- coding",
        ]

        # Transcript indicators (more = likely transcript)
        # NOTE: bare ": " removed — it false-positives on Python type annotations
        transcript_patterns = [
            "Speaker",
            "said",
            "talked about",
            "we discussed",
            "they mentioned",
            "the call",
            "meeting",
            "demo",
            "presentation",
            "thank you",
            "thanks for",
            "let me",
            "I think",
            "we can",
            "going to",
            ". And ",
            ". So ",
            ". But ",
        ]

        content_lower = content.lower()
        first_2000 = content_lower[:2000]  # Check start of content

        code_score = sum(1 for p in code_patterns if p.lower() in first_2000)
        transcript_score = sum(
            1 for p in transcript_patterns if p.lower() in first_2000
        )

        # Check for speaker patterns like "Name:" at line starts
        # Exclude lines that look like code (type annotations, dicts, imports)
        code_line_markers = (
            "def ",
            "class ",
            "import ",
            "from ",
            "->",
            "=>",
            "= ",
            "]: ",
            '": ',
        )
        lines = content[:2000].split("\n")
        speaker_lines = sum(
            1
            for line in lines
            if ":" in line[:30]
            and line.strip()
            and not any(m in line for m in code_line_markers)
        )
        if speaker_lines > 3:
            transcript_score += 3

        # Long content with few code patterns is likely a transcript
        if len(content) > 3000 and code_score < 3:
            transcript_score += 2

        logger.info(
            f"[INPUT DETECT] code_score={code_score}, transcript_score={transcript_score}"
        )

        return transcript_score > code_score

    def save_and_open_browser(
        self,
        png_bytes: bytes,
        filename: str | None = None,
        open_browser: bool = True,
    ) -> str:
        """
        Save PNG to temp file and optionally open in browser.

        Args:
            png_bytes: Raw PNG image bytes
            filename: Optional filename (auto-generated if None)
            open_browser: Whether to open in browser

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"storyboard_{timestamp}.png"

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, "wb") as f:
            f.write(png_bytes)

        logger.info(f"Saved storyboard to: {file_path}")

        if open_browser:
            url = f"file://{file_path}"
            webbrowser.open(url)
            logger.info(f"Opened in browser: {url}")

        return file_path

    async def fetch_image_url(self, url: str) -> bytes:
        """
        Fetch image from URL.

        Args:
            url: Image URL

        Returns:
            Image bytes

        Raises:
            ValueError: If fetch fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the unified storyboard pipeline.

        Args:
            arguments: Tool arguments containing:
                - input: Required. Any input type.
                - icp_preset: Optional. ICP preset (default: epiphan_av)
                - stage: Optional. Storyboard stage (default: preview)
                - audience: Optional. Target audience (default: av_director)
                - output_format: Optional. "infographic" (horizontal) or "storyboard" (vertical)
                - open_browser: Optional. Open in browser (default: true)

        Returns:
            ToolResult with:
            - storyboard_png: Base64-encoded PNG image
            - understanding: Extracted business insights
            - file_path: Path to saved PNG file
            - input_type: Detected input type
            - output_format: Format used for generation
        """
        start_time = perf_counter()

        # Extract arguments
        input_value = arguments.get("input")
        if not input_value:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result={},
                error="Missing required 'input' parameter",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        icp_preset = arguments.get("icp_preset", "epiphan_av")
        stage = arguments.get("stage", "preview")
        audience = arguments.get("audience", "av_director")
        vertical = arguments.get("vertical")  # Optional vertical for industry context
        output_format = arguments.get("output_format", "infographic")
        visual_style = arguments.get("visual_style", "polished")
        artist_style = arguments.get(
            "artist_style"
        )  # Optional: salvador_dali, monet, etc.
        open_browser = arguments.get("open_browser", True)
        supplementary_context = arguments.get(
            "supplementary_context"
        )  # Optional text context for mixed input

        # Handle multiple images (input can be a list of base64 strings)
        is_multi_image = isinstance(input_value, list)

        try:
            # Detect input type (use first item if list)
            if is_multi_image:
                input_type = self.detect_input_type(input_value[0])
                logger.info(
                    f"Detected input type: {input_type} (multi-image: {len(input_value)} images)"
                )
            else:
                input_type = self.detect_input_type(input_value)
                logger.info(f"Detected input type: {input_type}")

            # Get content based on input type
            is_image = False
            is_image_file_flag = False
            content: bytes | str

            if input_type == "miro_url":
                # Miro requires authentication - prompt user for screenshot
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    result={"input_type": input_type},
                    error=(
                        "Miro boards require authentication. Please: "
                        "1. Open the Miro board in your browser "
                        "2. Take a screenshot (Cmd+Shift+4 on Mac) "
                        "3. Copy the image to clipboard "
                        "4. Paste here as base64 data URL"
                    ),
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            elif input_type == "image_url":
                # Fetch image from URL
                logger.info(f"Fetching image from URL: {input_value}")
                content = await self.fetch_image_url(input_value)
                is_image = True

            elif input_type == "image_data":
                # Decode base64 image(s)
                if is_multi_image:
                    # Multiple images - decode each one
                    content = []
                    for img_data in input_value:
                        if "," in img_data:
                            content.append(base64.b64decode(img_data.split(",")[1]))
                        else:
                            content.append(base64.b64decode(img_data))
                    logger.info(
                        f"Decoded {len(content)} images for multi-image processing"
                    )
                else:
                    if "," in input_value:
                        # Data URL format: data:image/png;base64,XXXX
                        content = base64.b64decode(input_value.split(",")[1])
                    else:
                        # Raw base64
                        content = base64.b64decode(input_value)
                is_image = True

            elif input_type == "file_path":
                # Read file
                if self.is_image_file(input_value):
                    with open(input_value, "rb") as f:
                        content = f.read()
                    is_image = True
                    is_image_file_flag = True
                else:
                    with open(input_value) as text_file:
                        content = text_file.read()

            else:  # code
                content = input_value

            # Get ICP preset and audience persona
            icp = get_icp_preset(icp_preset)
            persona = get_audience_persona(audience)

            # Stage 1: Understand the content
            context_msg = (
                f" with supplementary context ({len(supplementary_context)} chars)"
                if supplementary_context
                else ""
            )
            logger.info(f"Stage 1: Understanding content...{context_msg}")

            async def extract(
                corrective_instruction: str | None = None,
            ) -> StoryboardUnderstanding:
                """Run stage-1 extraction; re-callable for the reframe retry."""
                if is_image:
                    if isinstance(content, list):
                        # Multiple images - understand all of them together
                        logger.info(
                            f"Understanding {len(content)} images together{context_msg}..."
                        )
                        return await self.gemini_client.understand_multiple_images(
                            images_data=content,
                            icp_preset=icp,
                            audience=audience,
                            vertical=vertical,
                            supplementary_context=supplementary_context,
                            corrective_instruction=corrective_instruction,
                        )
                    assert isinstance(content, bytes)
                    return await self.gemini_client.understand_image(
                        image_data=content,
                        icp_preset=icp,
                        audience=audience,
                        vertical=vertical,
                        supplementary_context=supplementary_context,
                        corrective_instruction=corrective_instruction,
                    )
                assert isinstance(content, str)
                # Auto-detect: is this code or a transcript?
                if self.is_transcript(content):
                    logger.info(
                        "Detected TRANSCRIPT input - using transcript understanding"
                    )
                    return await self.gemini_client.understand_transcript(
                        transcript=content,
                        icp_preset=icp,
                        audience=audience,
                        vertical=vertical,
                        corrective_instruction=corrective_instruction,
                    )
                logger.info("Detected CODE input - using code understanding")
                # Sanitize code content
                sanitized = sanitize_content(content, icp)
                return await self.gemini_client.understand_code(
                    code_content=sanitized,
                    icp_preset=icp,
                    audience=audience,
                    vertical=vertical,
                    corrective_instruction=corrective_instruction,
                )

            understanding = await extract()

            # Stage 1.5: quality gate. A competitor positioned as the hero
            # (e.g. a Sony-focused source becoming a Sony-branded card) gets
            # ONE corrective reframe retry; remaining issues ship in the
            # `quality` payload so the UI can badge the card. The gate must
            # never break generation — on any gate error we render without a
            # quality report.
            quality: dict | None = None
            try:
                report = run_quality_gate(
                    understanding.model_dump(), audience, vertical=vertical
                )
                reframe_applied = False
                tech_reframe_applied = False
                hero_hits = find_hero_competitors(understanding.model_dump())
                if hero_hits:
                    vendors = sorted({v for vs in hero_hits.values() for v in vs})
                    logger.warning(
                        "Quality gate: competitor-as-hero %s — corrective reframe retry",
                        vendors,
                    )
                    corrective = (
                        "PREVIOUS ATTEMPT REJECTED by the brand quality gate: "
                        f"it positioned the competitor(s) {', '.join(vendors)} "
                        "as the solution. Rewrite so headline, tagline, "
                        "what_it_does, business_value, and differentiator sell "
                        "EPIPHAN products only. The competitor workflow may "
                        "appear ONLY as the current/'before' state in "
                        "pain_point_addressed, frankenstack, or "
                        "forces_of_progress.push."
                    )
                    understanding = await extract(corrective_instruction=corrective)
                    report = run_quality_gate(
                        understanding.model_dump(), audience, vertical=vertical
                    )
                    reframe_applied = True

                # Technical-accuracy reframe. Copy that makes a technically
                # false product claim (e.g. "EC20 needs a separate encoder")
                # gets ONE corrective retry — but the reframe budget is SHARED
                # with the competitor gate, so we only fire if no reframe has
                # run yet. Remaining tech issues still surface in the report.
                tech_hits = find_tech_accuracy_violations(understanding.model_dump())
                if tech_hits and not reframe_applied:
                    bad_fields = sorted(tech_hits)
                    bad_claims = sorted(
                        {p for ps in tech_hits.values() for p in ps}
                    )
                    logger.warning(
                        "Quality gate: technically false claim in %s — "
                        "corrective reframe retry",
                        bad_fields,
                    )
                    corrective = (
                        "PREVIOUS ATTEMPT REJECTED by the technical-accuracy "
                        "gate: the copy made false claims about the Epiphan "
                        f"product in {', '.join(bad_fields)}. Specifically it "
                        f"asserted: {'; '.join(bad_claims)}. Rewrite the hero "
                        "fields to respect the real product facts — for "
                        "example, the EC20 PTZ records DIRECT to the CMS/LMS "
                        "with NO separate encoder; never claim it needs one. "
                        "State only capabilities the product actually has."
                    )
                    understanding = await extract(corrective_instruction=corrective)
                    report = run_quality_gate(
                        understanding.model_dump(), audience, vertical=vertical
                    )
                    reframe_applied = True
                    tech_reframe_applied = True
                elif tech_hits:
                    # Budget already spent on the competitor reframe; the false
                    # claim ships flagged in the report but un-retried. Log it so
                    # the skip isn't silent.
                    logger.warning(
                        "Quality gate: technically false claim in %s but reframe "
                        "budget already used by competitor gate — issue surfaced, "
                        "not retried",
                        sorted(tech_hits),
                    )
                quality = {
                    "passed": report.passed,
                    "score": report.score,
                    "reframe_applied": reframe_applied,
                    "tech_accuracy_reframe_applied": tech_reframe_applied,
                    "issues": [
                        {
                            "category": i.category,
                            "severity": i.severity,
                            "message": i.message,
                        }
                        for i in report.issues
                    ],
                }
            except Exception:
                logger.exception(
                    "Quality gate failed — rendering without a quality report"
                )

            # Stage 2: Generate storyboard
            artist_msg = f", artist_style={artist_style}" if artist_style else ""
            logger.info(
                f"Stage 2: Generating {output_format} ({visual_style}{artist_msg}) for audience={audience}..."
            )
            # Forward the user's uploaded reference photo(s) into generation as
            # image-to-image conditioning so the result depicts THEIR scene.
            # Only for image inputs (text/code → None = text-to-image); cap 3.
            reference_images: list[bytes] | None = None
            if is_image:
                if isinstance(content, list):
                    reference_images = [c for c in content if isinstance(c, bytes)][:3]
                elif isinstance(content, bytes):
                    reference_images = [content]
            png_bytes = await self.gemini_client.generate_storyboard(
                understanding=understanding,
                icp_preset=icp,
                stage=stage,
                audience=audience,
                vertical=vertical,
                output_format=output_format,
                visual_style=visual_style,
                artist_style=artist_style,
                reference_images=reference_images,
            )

            # Save and optionally open in browser
            file_path = self.save_and_open_browser(
                png_bytes=png_bytes,
                open_browser=open_browser,
            )

            # Encode result as base64
            storyboard_b64 = base64.b64encode(png_bytes).decode("utf-8")

            execution_time_ms = int((perf_counter() - start_time) * 1000)

            result = {
                "storyboard_png": storyboard_b64,
                "understanding": {
                    "headline": understanding.headline,
                    "tagline": understanding.tagline,
                    "what_it_does": understanding.what_it_does,
                    "business_value": understanding.business_value,
                    "who_benefits": understanding.who_benefits,
                    "differentiator": understanding.differentiator,
                    "pain_point_addressed": understanding.pain_point_addressed,
                    "suggested_icon": understanding.suggested_icon,
                    # DEBUG/VERIFICATION fields - for CEO/CTO to verify extraction is correct
                    "raw_extracted_text": understanding.raw_extracted_text,
                    "extraction_confidence": understanding.extraction_confidence,
                },
                "quality": quality,
                "file_path": file_path,
                "input_type": input_type,
                "output_format": output_format,
                "visual_style": visual_style,
                "stage": stage,
                "audience": audience,
                "vertical": vertical,
                "icp_preset": icp_preset,
            }

            if is_image_file_flag:
                result["is_image_file"] = True

            logger.info(f"Storyboard generated in {execution_time_ms}ms")

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.exception(f"Failed to generate storyboard: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result={"input_type": locals().get("input_type", "unknown")},
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
