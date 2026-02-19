# Storyboard Demo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI + Web UI demo for the UnifiedStoryboardTool that lets users upload images or paste code to generate executive infographics via Gemini 2.0 Flash.

**Architecture:** FastAPI demo router with 3 endpoints, CLI script that calls the tool directly, static HTML page with drag/drop/paste/browse. All reuse existing UnifiedStoryboardTool.

**Tech Stack:** FastAPI, Python 3.11+, vanilla HTML/JS (no build step), Gemini 2.0 Flash

---

## Task Overview

| Task | Component | Files | Test |
|------|-----------|-------|------|
| 1 | Demo Router | `src/demo/router.py` | `tests/demo/test_router.py` |
| 2 | CLI Script | `demo_cli.py` | Manual testing |
| 3 | Web UI | `static/demo.html` | Manual browser test |
| 4 | Wire Router | `src/api.py` | Existing tests |
| 5 | Vercel Config | `vercel.json` | Deploy verification |

---

## Task 1: Demo Router

**Files:**
- Create: `src/demo/__init__.py`
- Create: `src/demo/router.py`
- Create: `tests/demo/__init__.py`
- Create: `tests/demo/test_router.py`

**Step 1: Create demo directory structure**

```bash
mkdir -p src/demo tests/demo
touch src/demo/__init__.py tests/demo/__init__.py
```

**Step 2: Write the failing test**

Create `tests/demo/test_router.py`:

```python
"""Tests for demo router."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.demo.router import router


@pytest.fixture
def client():
    """Test client with demo router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestDemoExamples:
    """Tests for GET /demo/examples."""

    def test_list_examples_returns_list(self, client):
        """Should return list of example code files."""
        response = client.get("/demo/examples")
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert isinstance(data["examples"], list)
        assert len(data["examples"]) > 0

    def test_examples_have_required_fields(self, client):
        """Each example should have name, path, description."""
        response = client.get("/demo/examples")
        data = response.json()
        for example in data["examples"]:
            assert "name" in example
            assert "path" in example
            assert "description" in example


class TestDemoExampleByName:
    """Tests for GET /demo/examples/{name}."""

    def test_get_example_by_name(self, client):
        """Should return code content for valid example."""
        # First get list to find a valid name
        list_response = client.get("/demo/examples")
        examples = list_response.json()["examples"]
        if not examples:
            pytest.skip("No examples available")

        name = examples[0]["name"]
        response = client.get(f"/demo/examples/{name}")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "code" in data
        assert len(data["code"]) > 0

    def test_get_nonexistent_example_returns_404(self, client):
        """Should return 404 for unknown example name."""
        response = client.get("/demo/examples/nonexistent_example_xyz")
        assert response.status_code == 404


class TestDemoGenerate:
    """Tests for POST /demo/generate."""

    def test_generate_requires_input(self, client):
        """Should reject request without input."""
        response = client.post("/demo/generate", json={})
        assert response.status_code == 422

    def test_generate_accepts_code_input(self, client):
        """Should accept code input and return expected structure."""
        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def hello(): return 'world'",
            },
        )
        # May fail without GOOGLE_API_KEY, but should not be 422
        assert response.status_code in (200, 202, 500, 503)

    def test_generate_accepts_image_base64(self, client):
        """Should accept base64 image input."""
        # Minimal valid PNG (1x1 transparent)
        minimal_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = client.post(
            "/demo/generate",
            json={
                "input_type": "image",
                "image_base64": minimal_png,
            },
        )
        # May fail without GOOGLE_API_KEY, but structure should be valid
        assert response.status_code in (200, 202, 500, 503)
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/demo/test_router.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.demo.router'"

**Step 4: Write the router implementation**

Create `src/demo/router.py`:

```python
"""Demo router for storyboard testing.

Endpoints:
- GET /demo/examples - List available example code files
- GET /demo/examples/{name} - Get code content for an example
- POST /demo/generate - Generate storyboard from image or code
"""

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.tools.storyboard import UnifiedStoryboardTool

router = APIRouter(prefix="/demo", tags=["demo"])

# Example files from conductor-ai tools
EXAMPLES = [
    {
        "name": "video_script_generator",
        "path": "src/tools/video/script_generator.py",
        "description": "AI-powered video script generation for sales outreach",
    },
    {
        "name": "unified_storyboard",
        "path": "src/tools/storyboard/unified_storyboard.py",
        "description": "Convert any input to executive PNG storyboard",
    },
    {
        "name": "video_scheduler",
        "path": "src/tools/video/scheduler.py",
        "description": "Optimal video send time prediction",
    },
    {
        "name": "loom_tracker",
        "path": "src/tools/video/loom_tracker.py",
        "description": "Video view analytics and engagement scoring",
    },
    {
        "name": "gemini_client",
        "path": "src/tools/storyboard/gemini_client.py",
        "description": "Gemini Vision + Image Generation client",
    },
]

# Project root for reading example files
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# Response Models
# ============================================================================


class ExampleInfo(BaseModel):
    """Example code file information."""

    name: str
    path: str
    description: str


class ExamplesResponse(BaseModel):
    """Response from GET /demo/examples."""

    examples: list[ExampleInfo]


class ExampleCodeResponse(BaseModel):
    """Response from GET /demo/examples/{name}."""

    name: str
    path: str
    code: str


class GenerateRequest(BaseModel):
    """Request for POST /demo/generate."""

    input_type: Literal["image", "code"] = Field(
        ..., description="Type of input: 'image' or 'code'"
    )
    image_base64: str | None = Field(
        None, description="Base64-encoded image (for input_type='image')"
    )
    code: str | None = Field(None, description="Code string (for input_type='code')")
    stage: Literal["preview", "demo", "shipped"] = Field(
        "preview", description="Storyboard stage"
    )
    audience: Literal["business_owner", "c_suite", "btl_champion"] = Field(
        "c_suite", description="Target audience"
    )


class GenerateResponse(BaseModel):
    """Response from POST /demo/generate."""

    success: bool
    storyboard_png: str | None = Field(
        None, description="Base64-encoded PNG storyboard"
    )
    file_path: str | None = Field(None, description="Path to saved PNG file")
    understanding: dict | None = Field(
        None, description="Extracted business insights"
    )
    error: str | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/examples", response_model=ExamplesResponse)
async def list_examples() -> ExamplesResponse:
    """List available example code files from conductor-ai tools."""
    return ExamplesResponse(
        examples=[ExampleInfo(**ex) for ex in EXAMPLES]
    )


@router.get("/examples/{name}", response_model=ExampleCodeResponse)
async def get_example(name: str) -> ExampleCodeResponse:
    """Get code content for a specific example."""
    # Find example by name
    example = next((ex for ex in EXAMPLES if ex["name"] == name), None)
    if not example:
        raise HTTPException(status_code=404, detail=f"Example '{name}' not found")

    # Read file content
    file_path = PROJECT_ROOT / example["path"]
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Example file not found: {example['path']}"
        )

    code = file_path.read_text()
    return ExampleCodeResponse(name=name, path=example["path"], code=code)


@router.post("/generate", response_model=GenerateResponse)
async def generate_storyboard(request: GenerateRequest) -> GenerateResponse:
    """Generate storyboard from image or code input."""
    # Validate input
    if request.input_type == "image" and not request.image_base64:
        raise HTTPException(
            status_code=422, detail="image_base64 required when input_type='image'"
        )
    if request.input_type == "code" and not request.code:
        raise HTTPException(
            status_code=422, detail="code required when input_type='code'"
        )

    # Determine input value
    input_value = (
        request.image_base64 if request.input_type == "image" else request.code
    )

    try:
        # Use UnifiedStoryboardTool
        tool = UnifiedStoryboardTool()
        result = await tool.run(
            {
                "input": input_value,
                "stage": request.stage,
                "audience": request.audience,
                "open_browser": False,  # Don't open browser on server
            }
        )

        if not result.success:
            return GenerateResponse(
                success=False,
                error=result.error or "Unknown error",
            )

        return GenerateResponse(
            success=True,
            storyboard_png=result.result.get("storyboard_png"),
            file_path=result.result.get("file_path"),
            understanding=result.result.get("understanding"),
        )

    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e),
        )
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/demo/test_router.py -v`
Expected: All tests PASS (some may skip without GOOGLE_API_KEY)

**Step 6: Commit**

```bash
git add src/demo/ tests/demo/
git commit -m "feat(demo): add demo router with examples and generate endpoints"
```

---

## Task 2: CLI Script

**Files:**
- Create: `demo_cli.py` (project root)

**Step 1: Create CLI script**

Create `demo_cli.py`:

```python
#!/usr/bin/env python3
"""CLI demo for storyboard generation.

Usage:
    # Generate from image
    python demo_cli.py --image /path/to/screenshot.png

    # Generate from code file
    python demo_cli.py --code src/tools/video/script_generator.py

    # Generate from stdin
    cat main.py | python demo_cli.py --code -

    # List examples
    python demo_cli.py --list-examples

    # Generate from example
    python demo_cli.py --example video_script_generator

    # Options
    python demo_cli.py --image X --stage demo --audience c_suite --no-browser
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.storyboard import UnifiedStoryboardTool


# Example files
EXAMPLES = {
    "video_script_generator": "src/tools/video/script_generator.py",
    "unified_storyboard": "src/tools/storyboard/unified_storyboard.py",
    "video_scheduler": "src/tools/video/scheduler.py",
    "loom_tracker": "src/tools/video/loom_tracker.py",
    "gemini_client": "src/tools/storyboard/gemini_client.py",
}


def list_examples():
    """Print available examples."""
    print("\nAvailable examples:\n")
    for name, path in EXAMPLES.items():
        print(f"  {name:25} -> {path}")
    print("\nUsage: python demo_cli.py --example <name>")


async def generate_storyboard(
    input_value: str,
    stage: str = "preview",
    audience: str = "c_suite",
    open_browser: bool = True,
):
    """Generate storyboard from input."""
    print(f"\n🎨 Generating storyboard...")
    print(f"   Stage: {stage}")
    print(f"   Audience: {audience}")
    print(f"   Open browser: {open_browser}\n")

    tool = UnifiedStoryboardTool()
    result = await tool.run(
        {
            "input": input_value,
            "stage": stage,
            "audience": audience,
            "open_browser": open_browser,
        }
    )

    if not result.success:
        print(f"❌ Error: {result.error}")
        return 1

    print("✅ Storyboard generated successfully!\n")

    understanding = result.result.get("understanding", {})
    print("📊 Understanding:")
    print(f"   Headline: {understanding.get('headline', 'N/A')}")
    print(f"   What it does: {understanding.get('what_it_does', 'N/A')}")
    print(f"   Business value: {understanding.get('business_value', 'N/A')}")
    print(f"   Who benefits: {understanding.get('who_benefits', 'N/A')}")

    print(f"\n📁 File saved to: {result.result.get('file_path', 'N/A')}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate executive storyboards from images or code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--image", "-i",
        help="Path to image file (PNG, JPG, etc.)",
    )
    input_group.add_argument(
        "--code", "-c",
        help="Path to code file, or '-' for stdin",
    )
    input_group.add_argument(
        "--example", "-e",
        choices=list(EXAMPLES.keys()),
        help="Use a built-in example",
    )
    input_group.add_argument(
        "--list-examples", "-l",
        action="store_true",
        help="List available examples",
    )

    # Generation options
    parser.add_argument(
        "--stage", "-s",
        choices=["preview", "demo", "shipped"],
        default="preview",
        help="Storyboard stage (default: preview)",
    )
    parser.add_argument(
        "--audience", "-a",
        choices=["business_owner", "c_suite", "btl_champion"],
        default="c_suite",
        help="Target audience (default: c_suite)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open result in browser",
    )

    args = parser.parse_args()

    # Handle list examples
    if args.list_examples:
        list_examples()
        return 0

    # Determine input value
    input_value = None

    if args.image:
        path = Path(args.image)
        if not path.exists():
            print(f"❌ Error: Image file not found: {args.image}")
            return 1
        input_value = str(path.absolute())

    elif args.code:
        if args.code == "-":
            # Read from stdin
            input_value = sys.stdin.read()
        else:
            path = Path(args.code)
            if not path.exists():
                print(f"❌ Error: Code file not found: {args.code}")
                return 1
            input_value = path.read_text()

    elif args.example:
        path = Path(EXAMPLES[args.example])
        if not path.exists():
            print(f"❌ Error: Example file not found: {EXAMPLES[args.example]}")
            return 1
        input_value = path.read_text()

    else:
        parser.print_help()
        return 1

    # Run generation
    return asyncio.run(
        generate_storyboard(
            input_value=input_value,
            stage=args.stage,
            audience=args.audience,
            open_browser=not args.no_browser,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make executable**

```bash
chmod +x demo_cli.py
```

**Step 3: Test CLI (manual)**

```bash
# List examples
python demo_cli.py --list-examples

# Test with --help
python demo_cli.py --help
```

Expected: Help text displays, examples list shows

**Step 4: Commit**

```bash
git add demo_cli.py
git commit -m "feat(demo): add CLI script for storyboard generation"
```

---

## Task 3: Web UI

**Files:**
- Create: `static/demo.html`

**Step 1: Create static directory**

```bash
mkdir -p static
```

**Step 2: Create Web UI**

Create `static/demo.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conductor Storyboard Demo</title>
    <style>
        :root {
            --primary: #2E5090;
            --primary-dark: #1e3a5f;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #22c55e;
            --error: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }

        h1 {
            color: var(--primary);
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
        }

        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .card-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 1rem;
        }

        /* Drop zone */
        .drop-zone {
            border: 2px dashed var(--border);
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }

        .drop-zone:hover, .drop-zone.drag-over {
            border-color: var(--primary);
            background: rgba(46, 80, 144, 0.05);
        }

        .drop-zone-text {
            color: var(--text-muted);
            margin-bottom: 1rem;
        }

        .drop-zone input[type="file"] {
            display: none;
        }

        .btn {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
        }

        .btn-secondary {
            background: var(--bg);
            color: var(--text);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--border);
        }

        .btn-large {
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            width: 100%;
        }

        /* Divider */
        .divider {
            display: flex;
            align-items: center;
            margin: 1.5rem 0;
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        .divider::before, .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }

        .divider span {
            padding: 0 1rem;
        }

        /* Code textarea */
        textarea {
            width: 100%;
            min-height: 150px;
            padding: 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.875rem;
            resize: vertical;
        }

        textarea:focus {
            outline: none;
            border-color: var(--primary);
        }

        /* Options */
        .options-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .option-group {
            flex: 1;
        }

        .option-group label {
            display: block;
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }

        select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.875rem;
            background: white;
        }

        /* Examples */
        .examples {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .example-btn {
            font-size: 0.75rem;
            padding: 0.375rem 0.75rem;
        }

        /* Preview */
        .preview-container {
            margin-top: 1rem;
            display: none;
        }

        .preview-container.show {
            display: block;
        }

        .preview-image {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .preview-thumb {
            max-width: 200px;
            max-height: 150px;
            object-fit: contain;
            border-radius: 4px;
            margin-top: 0.5rem;
        }

        /* Status */
        .status {
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            display: none;
        }

        .status.show {
            display: block;
        }

        .status.loading {
            background: rgba(46, 80, 144, 0.1);
            color: var(--primary);
        }

        .status.success {
            background: rgba(34, 197, 94, 0.1);
            color: var(--success);
        }

        .status.error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--error);
        }

        /* Understanding */
        .understanding {
            margin-top: 1rem;
            padding: 1rem;
            background: var(--bg);
            border-radius: 8px;
        }

        .understanding h4 {
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }

        .understanding p {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }

        .understanding strong {
            color: var(--text);
        }

        /* Result */
        .result {
            margin-top: 1.5rem;
        }

        .result-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        /* Footer */
        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Conductor Storyboard Demo</h1>
            <p class="subtitle">Generate executive infographics from images or code using Gemini AI</p>
        </header>

        <div class="card">
            <div class="card-title">Image Input</div>
            <div class="drop-zone" id="dropZone">
                <p class="drop-zone-text">Drop image here, paste (Cmd+V), or</p>
                <button class="btn btn-secondary" onclick="document.getElementById('fileInput').click()">Browse Files</button>
                <input type="file" id="fileInput" accept="image/*">
            </div>
            <div class="preview-container" id="imagePreview">
                <img class="preview-thumb" id="previewThumb" alt="Preview">
            </div>
        </div>

        <div class="divider"><span>OR</span></div>

        <div class="card">
            <div class="card-title">Code Input</div>
            <textarea id="codeInput" placeholder="Paste or type code here..."></textarea>
        </div>

        <div class="card">
            <div class="card-title">Options</div>
            <div class="options-row">
                <div class="option-group">
                    <label for="stage">Stage</label>
                    <select id="stage">
                        <option value="preview">Preview</option>
                        <option value="demo">Demo</option>
                        <option value="shipped">Shipped</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="audience">Audience</label>
                    <select id="audience">
                        <option value="c_suite">C-Suite</option>
                        <option value="business_owner">Business Owner</option>
                        <option value="btl_champion">BTL Champion</option>
                    </select>
                </div>
            </div>

            <button class="btn btn-primary btn-large" id="generateBtn" onclick="generate()">
                Generate Storyboard
            </button>

            <div class="status" id="status"></div>
        </div>

        <div class="card">
            <div class="card-title">Quick Examples</div>
            <div class="examples" id="examples">
                <!-- Populated by JS -->
            </div>
        </div>

        <div class="card result" id="resultCard" style="display: none;">
            <div class="card-title">Result</div>
            <img class="preview-image" id="resultImage" alt="Generated Storyboard">
            <div class="understanding" id="understanding"></div>
            <div class="result-actions">
                <button class="btn btn-primary" onclick="downloadResult()">Download PNG</button>
                <button class="btn btn-secondary" onclick="openInNewTab()">Open in New Tab</button>
            </div>
        </div>
    </div>

    <footer>
        Powered by Gemini 2.0 Flash | Conductor-AI
    </footer>

    <script>
        // State
        let imageBase64 = null;
        let resultPng = null;

        // API base URL (relative for same-origin)
        const API_BASE = '';

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadExamples();
            setupDropZone();
            setupPaste();
        });

        // Load examples
        async function loadExamples() {
            try {
                const res = await fetch(`${API_BASE}/demo/examples`);
                const data = await res.json();
                const container = document.getElementById('examples');
                container.innerHTML = data.examples.map(ex =>
                    `<button class="btn btn-secondary example-btn" onclick="loadExample('${ex.name}')">${ex.name.replace(/_/g, ' ')}</button>`
                ).join('');
            } catch (e) {
                console.error('Failed to load examples:', e);
            }
        }

        // Load example code
        async function loadExample(name) {
            try {
                showStatus('Loading example...', 'loading');
                const res = await fetch(`${API_BASE}/demo/examples/${name}`);
                const data = await res.json();
                document.getElementById('codeInput').value = data.code;
                imageBase64 = null;
                document.getElementById('imagePreview').classList.remove('show');
                hideStatus();
            } catch (e) {
                showStatus('Failed to load example: ' + e.message, 'error');
            }
        }

        // Setup drop zone
        function setupDropZone() {
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');

            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('drag-over');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                const file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    handleImageFile(file);
                }
            });

            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    handleImageFile(file);
                }
            });
        }

        // Setup paste
        function setupPaste() {
            document.addEventListener('paste', (e) => {
                const items = e.clipboardData.items;
                for (const item of items) {
                    if (item.type.startsWith('image/')) {
                        const file = item.getAsFile();
                        handleImageFile(file);
                        e.preventDefault();
                        break;
                    }
                }
            });
        }

        // Handle image file
        function handleImageFile(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imageBase64 = e.target.result;
                document.getElementById('previewThumb').src = imageBase64;
                document.getElementById('imagePreview').classList.add('show');
                document.getElementById('codeInput').value = '';
            };
            reader.readAsDataURL(file);
        }

        // Generate storyboard
        async function generate() {
            const code = document.getElementById('codeInput').value.trim();
            const stage = document.getElementById('stage').value;
            const audience = document.getElementById('audience').value;

            if (!imageBase64 && !code) {
                showStatus('Please provide an image or code', 'error');
                return;
            }

            const payload = {
                input_type: imageBase64 ? 'image' : 'code',
                stage,
                audience,
            };

            if (imageBase64) {
                payload.image_base64 = imageBase64;
            } else {
                payload.code = code;
            }

            try {
                showStatus('Generating storyboard... This may take 30-60 seconds.', 'loading');
                document.getElementById('generateBtn').disabled = true;

                const res = await fetch(`${API_BASE}/demo/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                const data = await res.json();

                if (!data.success) {
                    throw new Error(data.error || 'Generation failed');
                }

                resultPng = data.storyboard_png;
                document.getElementById('resultImage').src = `data:image/png;base64,${resultPng}`;

                // Show understanding
                if (data.understanding) {
                    const u = data.understanding;
                    document.getElementById('understanding').innerHTML = `
                        <h4>Extracted Insights</h4>
                        <p><strong>Headline:</strong> ${u.headline || 'N/A'}</p>
                        <p><strong>What it does:</strong> ${u.what_it_does || 'N/A'}</p>
                        <p><strong>Business value:</strong> ${u.business_value || 'N/A'}</p>
                        <p><strong>Who benefits:</strong> ${u.who_benefits || 'N/A'}</p>
                    `;
                }

                document.getElementById('resultCard').style.display = 'block';
                showStatus('Storyboard generated successfully!', 'success');

            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            } finally {
                document.getElementById('generateBtn').disabled = false;
            }
        }

        // Download result
        function downloadResult() {
            if (!resultPng) return;
            const link = document.createElement('a');
            link.href = `data:image/png;base64,${resultPng}`;
            link.download = `storyboard_${Date.now()}.png`;
            link.click();
        }

        // Open in new tab
        function openInNewTab() {
            if (!resultPng) return;
            const win = window.open();
            win.document.write(`<img src="data:image/png;base64,${resultPng}" style="max-width: 100%;">`);
        }

        // Status helpers
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status show ${type}`;
        }

        function hideStatus() {
            document.getElementById('status').className = 'status';
        }
    </script>
</body>
</html>
```

**Step 3: Commit**

```bash
git add static/
git commit -m "feat(demo): add web UI with drag/drop/paste support"
```

---

## Task 4: Wire Router to API

**Files:**
- Modify: `src/api.py:44` (add import and router)

**Step 1: Update src/api.py**

Add import after line 28:
```python
from src.demo.router import router as demo_router
```

Add router mount after line 44:
```python
app.include_router(demo_router)
```

**Step 2: Add static file serving**

Add imports at top:
```python
from fastapi.staticfiles import StaticFiles
```

Add after routers (around line 46):
```python
# Serve static files (demo web UI)
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**Step 3: Run existing tests**

```bash
pytest tests/test_api.py -v
```

Expected: All existing tests pass

**Step 4: Commit**

```bash
git add src/api.py
git commit -m "feat(api): wire demo router and static files"
```

---

## Task 5: Vercel Configuration

**Files:**
- Create: `vercel.json`

**Step 1: Create vercel.json**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "src/api.py",
      "use": "@vercel/python"
    },
    {
      "src": "static/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "src/api.py"
    }
  ],
  "env": {
    "GOOGLE_API_KEY": "@google_api_key"
  }
}
```

**Step 2: Commit**

```bash
git add vercel.json
git commit -m "feat(deploy): add Vercel configuration"
```

**Step 3: Deploy to Vercel**

```bash
vercel --prod
```

---

## Execution Order

```
Task 1 (Router) ──► Task 4 (Wire) ──► Task 5 (Vercel)
                          ↑
Task 2 (CLI) ─────────────┘
                          ↑
Task 3 (Web UI) ──────────┘
```

Tasks 1, 2, 3 can run in parallel. Task 4 depends on 1, 3. Task 5 depends on 4.

---

## Success Criteria

- [ ] `pytest tests/demo/test_router.py` - all tests pass
- [ ] `python demo_cli.py --list-examples` - shows examples
- [ ] `python demo_cli.py --example video_script_generator` - generates storyboard (needs GOOGLE_API_KEY)
- [ ] Web UI at `/static/demo.html` loads and shows examples
- [ ] Web UI generates storyboard from pasted code
- [ ] Web UI generates storyboard from dropped image
- [ ] Deployed to Vercel and accessible
