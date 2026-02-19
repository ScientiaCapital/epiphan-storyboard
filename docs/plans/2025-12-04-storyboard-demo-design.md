# Storyboard Demo System Design

**Date:** 2025-12-04
**Status:** Approved for Implementation

## Overview

Build a CLI + Web UI demo for the UnifiedStoryboardTool that generates executive-ready PNG infographics from images (Miro screenshots, diagrams) or code files using Gemini 2.0 Flash.

## Requirements

- **CLI Demo Script**: Command-line interface for quick testing
- **Simple Web UI**: Browser-based interface with drag/drop/paste/browse
- **FastAPI Backend**: API endpoints wrapping UnifiedStoryboardTool
- **Vercel Deployment**: Already configured (prj_W9iWYswxkSJDNs4hmDWODlRwMkX0)
- **Test Sources**: conductor-ai tools + user-pasted code
- **Priority**: Speed to working demo

## Architecture

```
CLI (demo_cli.py)              Web UI (demo.html)
┌──────────────┐               ┌──────────────────┐
│ python       │               │ Static HTML/JS   │
│ demo_cli.py  │               │ Drag/Paste/Pick  │
│ --image X    │               │ Code textarea    │
│ --code Y     │               └────────┬─────────┘
└──────┬───────┘                        │
       │                                │
       ▼                                ▼
┌──────────────────────────────────────────────────┐
│            FastAPI /demo endpoints               │
│  POST /demo/generate  (accepts image OR code)    │
│  GET  /demo/examples  (list conductor-ai tools)  │
└──────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│        UnifiedStoryboardTool (existing)          │
│        Gemini 2.0 Flash Vision + Image Gen       │
└──────────────────────────────────────────────────┘
                        │
                        ▼
               PNG opens in browser
```

## API Endpoints

### POST /demo/generate

Main generation endpoint accepting image or code input.

**Request (multipart/form-data OR JSON):**
```json
{
  "input_type": "image" | "code",
  "image_file": "<uploaded file>",
  "image_base64": "data:image/...",
  "code": "def calculate...",
  "stage": "preview" | "demo" | "shipped",
  "audience": "business_owner" | "c_suite" | "btl_champion"
}
```

**Response:**
```json
{
  "success": true,
  "storyboard_png": "<base64 encoded PNG>",
  "file_path": "/tmp/storyboard_xxx.png",
  "understanding": {
    "headline": "Smarter Scheduling for Your Crews",
    "what_it_does": "Automatically assigns jobs...",
    "business_value": "Save 5 hours per week",
    "who_benefits": "Operations managers",
    "differentiator": "Built for contractors",
    "pain_point_addressed": "Manual scheduling headaches"
  }
}
```

### GET /demo/examples

List available example code files from conductor-ai.

**Response:**
```json
{
  "examples": [
    {"name": "video_script_generator", "path": "src/tools/video/script_generator.py", "description": "Video script generation tool"},
    {"name": "unified_storyboard", "path": "src/tools/storyboard/unified_storyboard.py", "description": "Storyboard generation tool"},
    {"name": "video_scheduler", "path": "src/tools/video/scheduler.py", "description": "Optimal send time prediction"}
  ]
}
```

### GET /demo/examples/{name}

Get code content for a specific example.

**Response:**
```json
{
  "name": "video_script_generator",
  "path": "src/tools/video/script_generator.py",
  "code": "class VideoScriptGeneratorTool..."
}
```

## CLI Design

```bash
# Generate from image
python demo_cli.py --image /path/to/screenshot.png

# Generate from code file
python demo_cli.py --code src/tools/video/script_generator.py

# Generate from stdin (pipe code)
cat main.py | python demo_cli.py --code -

# List examples
python demo_cli.py --list-examples

# Generate from example
python demo_cli.py --example video_script_generator

# Options
python demo_cli.py --image X --stage demo --audience c_suite --no-browser
```

## Web UI Design

Clean, single-page interface with:
- Image drop zone (drag + paste + browse)
- Code textarea
- Stage/audience dropdowns
- Generate button
- Quick example buttons
- Result display with download option

```
┌─────────────────────────────────────────────────────────┐
│  Conductor Storyboard Demo                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │                                                    │ │
│  │     Drop image here, paste (Cmd+V), or browse     │ │
│  │            [Browse Files]                          │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                        OR                                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ def calculate_roi():                              │ │
│  │     # Paste or type code here...                  │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Stage: [Preview]   Audience: [C-Suite]                 │
│                                                          │
│           [ Generate Storyboard ]                        │
│                                                          │
│  ─────────────────────────────────────────────────────  │
│  Quick Examples: [Video Script] [Storyboard] [Scheduler] │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
conductor-ai/
├── demo/
│   ├── demo_cli.py           # CLI interface
│   ├── demo_routes.py        # FastAPI router
│   └── static/
│       └── demo.html         # Web UI (single file)
├── src/
│   └── api.py                # Mount demo router
└── vercel.json               # Deployment config (new)
```

## Deployment

**Vercel Project:** conductor-ai (already configured)
- Static files served from demo/static/
- API routes via FastAPI serverless functions
- Environment: GOOGLE_API_KEY required

## Technology Choices

- **No OpenAI** - Gemini 2.0 Flash only
- **No build step** - Plain HTML/JS for Web UI
- **Existing tools** - Reuse UnifiedStoryboardTool
- **FastAPI** - Match existing API architecture

## Success Criteria

1. CLI can generate storyboard from image file
2. CLI can generate storyboard from code file
3. Web UI accepts drag/drop images
4. Web UI accepts clipboard paste
5. Web UI accepts file browser
6. Web UI accepts code input
7. Quick examples work
8. PNG opens in browser
9. Deployed to Vercel
