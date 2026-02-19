# Product Requirements Document (PRD)
# Conductor-AI v1.0 - Screen Recording Module
# PLANNING DOC - Future Feature for App Walkthrough Video Generation

> **Note**: This describes a planned screen recording feature to complement the existing storyboard generation capabilities. The system would crawl web apps, record UI interactions, and generate narrated training videos.

---

## Executive Summary

This module would add automated training video generation by:
1. Crawling web applications to discover features
2. Writing scenario scripts for user journeys  
3. Recording screen interactions with the Browserbase cloud browser
4. Generating AI voice narration (ElevenLabs)
5. Assembling final videos with captions (FFmpeg)

**Complementary to existing storyboard system**: While storyboards generate content from images/text/transcripts, this module would create actual screen recordings showing the product in action.

---

## Agent Specifications

### 1. Feature Discovery Agent
**Model**: Qwen2.5-72B via OpenRouter  
**Purpose**: Crawl application, build feature inventory

**Capabilities:**
- Navigate authenticated flows via Browserbase
- Detect interactive elements (buttons, forms, modals)
- Build navigation graph between features
- Identify feature categories

**Output Schema:**
```yaml
features:
  - id: "feature_001"
    name: "Create New Project"
    category: "core"
    path: "/projects/new"
    interactions:
      - type: "form"
        fields: ["name", "description", "template"]
      - type: "button"  
        label: "Create Project"
    prerequisites: []
    discovered_at: "2025-01-15T10:30:00Z"
```

### 2. Scenario Generator Agent
**Model**: Claude Opus 4.5  
**Purpose**: Create realistic user journey scripts

**Scenario Types:**
| Type | Description | Duration |
|------|-------------|----------|
| onboarding | First-time user setup | 60-90s |
| feature_tutorial | Single feature deep-dive | 45-60s |
| workflow_guide | Multi-step process | 90-120s |
| troubleshooting | Common issue resolution | 30-45s |
| whats_new | Feature announcement | 30-45s |

**Script Format:**
```yaml
scenario:
  id: "onboarding_001"
  title: "Getting Started with Coperniq"
  type: "onboarding"
  persona: "project_manager"
  estimated_duration_sec: 75
  
  steps:
    - step: 1
      action: "navigate"
      target: "/login"
      narration: "Let's start by logging into your Coperniq account."
      timing:
        action_delay_ms: 500
        narration_pause_ms: 1000
        
    - step: 2
      action: "click"
      target: "button[data-testid='google-signin']"
      narration: "Click Sign in with Google for the fastest setup."
      timing:
        highlight_duration_ms: 800
```

### 3. Screen Recorder Agent
**Model**: DeepSeek-V3 for navigation decisions  
**Purpose**: Execute scenarios, capture video

**Recording Specs:**
- Resolution: 1920x1080 @ 30fps
- Format: WebM (raw), MP4 (final)
- Cursor: Visible with click highlights
- Typing: Natural pace (50ms per character)

**Timing Configuration:**
```python
RECORDING_CONFIG = {
    "resolution": {"width": 1920, "height": 1080},
    "fps": 30,
    "action_delay_ms": 500,
    "typing_speed_ms": 50,
    "scroll_duration_ms": 800,
    "click_highlight_ms": 300,
    "max_duration_sec": 180,
}
```

### 4. Narration Agent
**Provider**: ElevenLabs  
**Purpose**: Generate synchronized voice narration

**Voice Presets:**
| Preset | Voice ID | Use Case |
|--------|----------|----------|
| professional | ErXwobaYiN019PkySvjV | Enterprise, formal |
| friendly | 21m00Tcm4TlvDq8ikWAM | Onboarding, tutorials |
| energetic | AZnzlk1XvdvUeBnXmlld | Product launches |
| calm | MF3mGyEYCl7XYWbV9V6O | Troubleshooting |

**Output:**
- Audio: MP3 44.1kHz 128kbps
- Timestamps: Word-level alignment
- Captions: SRT format

### 5. Video Assembler Agent
**Tools**: FFmpeg pipeline  
**Purpose**: Combine video + audio + captions

**Pipeline:**
```
Raw Video → Speed Adjust → Audio Merge → Caption Burn → Branding → Export
```

**Output Formats:**
| Format | Resolution | Use Case |
|--------|------------|----------|
| MP4 HD | 1920x1080 | YouTube, LMS |
| MP4 720p | 1280x720 | Help center |
| WebM | 1920x1080 | Web embed |
| GIF | 480p | Slack, docs |

### 6. Orchestrator Agent
**Model**: Claude Opus 4.5  
**Purpose**: Coordinate workflow, ensure quality

**Decision Points:**
- Split complex features into multiple videos
- Rewrite awkward narration
- Retry failed recordings
- Flag UI changes that break scenarios

**Cost Control:** <15 Opus calls per video

---

## Data Models

### Scenario
```python
class Scenario(BaseModel):
    id: str
    session_id: str
    title: str
    description: str
    type: ScenarioType  # onboarding, tutorial, etc.
    persona: str
    steps: list[ScenarioStep]
    estimated_duration_sec: int
    status: str  # pending, approved, recorded
    created_at: datetime
```

### Recording
```python
class Recording(BaseModel):
    id: str
    scenario_id: str
    status: str  # recording, processing, complete, failed
    raw_video_url: str | None
    timing_manifest: list[TimingEvent]
    duration_ms: int
    screenshots: list[str]
    error: str | None
```

### Video
```python
class Video(BaseModel):
    id: str
    scenario_id: str
    recording_id: str
    title: str
    video_url: str
    thumbnail_url: str
    captions_url: str
    transcript: str
    duration_sec: int
    format: str
    resolution: str
    file_size_bytes: int
```

---

## API Endpoints

### Scenario Generation
```
POST /api/v1/recording/scenarios/generate
{
  "target_url": "https://app.coperniq.ai",
  "auth": {
    "type": "oauth",
    "provider": "google"
  },
  "scenario_types": ["onboarding", "feature_tutorial"],
  "max_scenarios": 10
}
```

### Start Recording
```
POST /api/v1/recording/scenarios/{id}/record
{
  "voice_preset": "friendly",
  "resolution": "1080p",
  "include_captions": true
}
```

### Export Video
```
POST /api/v1/recording/videos/{id}/export
{
  "formats": ["mp4_1080p", "gif"],
  "include_transcript": true
}
```

---

## Cost Model

**Per Video Minute Target: <$0.50**

| Component | Est. Cost/Min |
|-----------|---------------|
| Browserbase | $0.08 |
| LLM (blended) | $0.15 |
| ElevenLabs TTS | $0.18 |
| FFmpeg (compute) | $0.02 |
| Storage (R2) | $0.01 |
| **Total** | **~$0.44** |

---

## Integration with Existing System

This module would integrate with the current storyboard system:

1. **Knowledge Base**: Use existing `coperniq_knowledge` to inform scenario scripts
2. **Persona System**: Leverage COI/ROI/EASE value angles for narration tone
3. **Gemini Client**: Could use for script enhancement/review
4. **Storage**: Use existing Supabase/R2 infrastructure

**New Dependencies:**
- Browserbase SDK
- ElevenLabs SDK  
- FFmpeg (system install)
- Playwright (for recording)

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Browserbase client integration
- Basic screen recording with Playwright
- Simple narration (static text)

### Phase 2: Intelligence (Week 3-4)
- Feature discovery agent
- Scenario generation
- Dynamic narration scripts

### Phase 3: Polish (Week 5-6)
- Video assembly pipeline
- Caption generation
- Quality review loop

### Phase 4: Integration (Week 7-8)
- Knowledge base integration
- API endpoints
- UI for video management

---

*Document Version: 1.0*  
*Created: 2025-01-15*  
*Status: PLANNING - Not yet implemented*
