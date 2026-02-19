# Architecture Document
# Conductor-AI - Screen Recording Module
# PLANNING DOC - Technical Architecture for Future Feature

> **Note**: This describes architecture for a planned screen recording feature. The existing system focuses on storyboard generation from images/text. This module would add actual screen recording capabilities.

---

## System Overview

The screen recording module extends Conductor-AI with automated video capture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SCREEN RECORDING MODULE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Scenario    │───▶│   Screen     │───▶│    Video     │               │
│  │  Generator   │    │   Recorder   │    │   Assembler  │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    NEW DEPENDENCIES                              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │    │
│  │  │Browserbase │  │ ElevenLabs │  │   FFmpeg   │  │ Playwright │ │    │
│  │  │  (Cloud)   │  │   (TTS)    │  │  (Video)   │  │ (Record)   │ │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    EXISTING INFRASTRUCTURE                       │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │    │
│  │  │  Supabase  │  │  Gemini    │  │  Knowledge │  │  Storyboard│ │    │
│  │  │    DB      │  │  Client    │  │    Base    │  │   System   │ │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure (Proposed Additions)

```
conductor-ai/
├── src/
│   ├── tools/
│   │   ├── recording/              # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── browserbase.py      # Cloud browser client
│   │   │   ├── screen_capture.py   # Video recording
│   │   │   ├── scenario_gen.py     # Script generation
│   │   │   ├── narrator.py         # ElevenLabs TTS
│   │   │   ├── assembler.py        # FFmpeg pipeline
│   │   │   └── captions.py         # SRT generation
│   │   ├── storyboard/             # EXISTING
│   │   └── video/                  # EXISTING
│   ├── agents/                     # EXISTING
│   └── knowledge/                  # EXISTING - will integrate
├── docs/
│   ├── VIDEO_RECORDING_PRD.md      # This planning doc
│   └── VIDEO_RECORDING_ARCH.md     # This architecture doc
└── tests/
    └── tools/
        └── test_recording/         # NEW tests
```

---

## LangGraph Workflow (Screen Recording)

### State Schema

```python
from typing import TypedDict, Literal

class RecordingState(TypedDict):
    # Session
    session_id: str
    target_url: str
    auth_config: dict
    
    # Discovery
    pages: list[dict]
    features: list[dict]
    
    # Current Scenario
    scenario: dict | None
    scenario_status: Literal["pending", "approved", "recording", "complete"]
    
    # Recording
    raw_video_path: str | None
    timing_events: list[dict]
    screenshots: list[str]
    
    # Narration
    narration_script: str
    audio_path: str | None
    word_timestamps: list[dict]
    
    # Output
    final_video_url: str | None
    captions_url: str | None
    
    # Tracking
    costs: dict
    errors: list[str]
```

### Workflow Graph

```
START
  │
  ▼
┌─────────────┐
│   crawl     │  Discover app features
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   plan      │  Select scenarios to record
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ For each scenario:      │
│  ┌─────────────────┐    │
│  │ write_script    │    │
│  └────────┬────────┘    │
│           ▼             │
│  ┌─────────────────┐    │
│  │ record_screen   │    │  ← Browserbase + Playwright
│  └────────┬────────┘    │
│           ▼             │
│  ┌─────────────────┐    │
│  │ generate_audio  │    │  ← ElevenLabs TTS
│  └────────┬────────┘    │
│           ▼             │
│  ┌─────────────────┐    │
│  │ assemble_video  │    │  ← FFmpeg
│  └────────┬────────┘    │
└───────────┼─────────────┘
            │
            ▼
┌─────────────┐
│   export    │  Upload to R2/Supabase
└──────┬──────┘
       │
       ▼
      END
```

---

## Key Components

### 1. Browserbase Client

```python
# src/tools/recording/browserbase.py
import httpx
from playwright.async_api import async_playwright

class BrowserbaseClient:
    """Cloud browser for authenticated app access."""
    
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        
    async def create_session(self) -> dict:
        """Create new browser session."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.browserbase.com/v1/sessions",
                headers={"x-bb-api-key": self.api_key},
                json={"projectId": self.project_id}
            )
            return response.json()
    
    async def connect(self, session_id: str):
        """Connect Playwright to session."""
        ws_url = f"wss://connect.browserbase.com?sessionId={session_id}"
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(ws_url)
        return browser.contexts[0].pages[0]
```

### 2. Screen Recorder

```python
# src/tools/recording/screen_capture.py
from pathlib import Path

class ScreenRecorder:
    """Record browser interactions with timing data."""
    
    def __init__(self, page, output_dir: Path):
        self.page = page
        self.output_dir = output_dir
        self.timing_events = []
        
    async def start(self, filename: str):
        """Begin recording."""
        self.video_path = self.output_dir / filename
        await self.page.video.start(path=str(self.video_path))
        self.start_time = time.time()
        
    async def record_action(self, action: str, target: str, step: int):
        """Log action with timestamp."""
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        
        # Screenshot before action
        screenshot = self.output_dir / f"step_{step}.png"
        await self.page.screenshot(path=str(screenshot))
        
        self.timing_events.append({
            "step": step,
            "action": action,
            "target": target,
            "timestamp_ms": elapsed_ms,
            "screenshot": str(screenshot)
        })
        
    async def stop(self) -> dict:
        """Stop recording, return metadata."""
        await self.page.video.stop()
        return {
            "video_path": str(self.video_path),
            "timing_events": self.timing_events,
            "duration_ms": int((time.time() - self.start_time) * 1000)
        }
```

### 3. ElevenLabs Narrator

```python
# src/tools/recording/narrator.py
import httpx
from pathlib import Path

class ElevenLabsNarrator:
    """Generate TTS narration with timestamps."""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    VOICE_PRESETS = {
        "professional": "ErXwobaYiN019PkySvjV",
        "friendly": "21m00Tcm4TlvDq8ikWAM",
        "energetic": "AZnzlk1XvdvUeBnXmlld",
        "calm": "MF3mGyEYCl7XYWbV9V6O",
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"xi-api-key": api_key},
            timeout=60.0
        )
        
    async def generate(
        self,
        text: str,
        voice: str = "friendly",
        output_path: Path = None,
    ) -> dict:
        """Generate speech with word timestamps."""
        voice_id = self.VOICE_PRESETS.get(voice, voice)
        
        response = await self.client.post(
            f"{self.BASE_URL}/text-to-speech/{voice_id}/with-timestamps",
            json={
                "text": text,
                "model_id": "eleven_turbo_v2",
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Save audio
        import base64
        audio_bytes = base64.b64decode(data["audio_base64"])
        output_path.write_bytes(audio_bytes)
        
        return {
            "audio_path": str(output_path),
            "word_timestamps": data["alignment"],
            "duration_ms": data["audio_duration_ms"]
        }
```

### 4. Video Assembler

```python
# src/tools/recording/assembler.py
import subprocess
from pathlib import Path

class VideoAssembler:
    """Combine video, audio, and captions."""
    
    def assemble(
        self,
        video_path: Path,
        audio_path: Path,
        captions_path: Path | None,
        output_path: Path,
    ) -> Path:
        """FFmpeg assembly pipeline."""
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
        ]
        
        if captions_path:
            cmd.extend([
                "-vf", f"subtitles={captions_path}:force_style='FontSize=24'"
            ])
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            str(output_path)
        ])
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def create_thumbnail(self, video_path: Path, output_path: Path, at_sec: float = 5.0):
        """Extract thumbnail frame."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", str(at_sec),
            "-vframes", "1",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
```

---

## Integration Points

### With Existing Knowledge Base

```python
# Use knowledge to inform scenario scripts
from src.knowledge.service import KnowledgeService

async def enrich_scenario(scenario: dict, knowledge: KnowledgeService):
    """Add knowledge-based context to scenario narration."""
    
    # Get relevant pain points for this feature
    pain_points = await knowledge.search(
        query=scenario["feature_name"],
        types=["pain_point", "objection"]
    )
    
    # Get approved terminology
    terminology = await knowledge.get_by_type("approved_term")
    
    return {
        **scenario,
        "pain_points": pain_points,
        "terminology": terminology
    }
```

### With Existing Storyboard System

The screen recording module complements storyboards:
- **Storyboards**: Static slides from images/text (existing)
- **Screen Recordings**: Dynamic videos of actual app usage (new)

Could share:
- Persona definitions (COI/ROI/EASE framing)
- Banned terms list
- Brand guidelines
- Output storage (Supabase/R2)

---

## Environment Variables (New)

```bash
# Add to existing .env
BROWSERBASE_API_KEY=bb_live_xxx
BROWSERBASE_PROJECT_ID=proj_xxx
ELEVENLABS_API_KEY=sk_xxx
ELEVENLABS_DEFAULT_VOICE=friendly
```

---

## Cost Estimates

| Component | Per Minute | Notes |
|-----------|------------|-------|
| Browserbase | $0.08 | Cloud browser |
| ElevenLabs | $0.18 | TTS generation |
| LLM (script) | $0.10 | Scenario writing |
| FFmpeg | $0.02 | Processing |
| Storage | $0.01 | R2 |
| **Total** | **~$0.39** | Target: <$0.50 |

---

## Implementation Priority

1. **Phase 1**: Basic Browserbase + Playwright recording (no narration)
2. **Phase 2**: Add ElevenLabs narration
3. **Phase 3**: FFmpeg assembly pipeline
4. **Phase 4**: Scenario generation from feature discovery
5. **Phase 5**: Knowledge base integration
6. **Phase 6**: API endpoints & UI

---

*Document Version: 1.0*  
*Created: 2025-01-15*  
*Status: PLANNING - Architecture proposal for future feature*
