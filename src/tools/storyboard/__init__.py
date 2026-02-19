"""
Storyboard Tools Module for Conductor-AI
=========================================

AI-powered code/roadmap to executive storyboard pipeline:
- CodeToStoryboardTool: Transform code files into beautiful one-page PNG storyboards
- RoadmapToStoryboardTool: Transform Miro/roadmap screenshots into sanitized teasers

Two-stage pipeline:
1. UNDERSTAND (Gemini Vision) - Analyze input, extract business value
2. GENERATE (Gemini Image Gen) - Create beautiful PNG storyboard

Target audience: MEP+energy contractors ($5M+ ICP)
- Business owners: profit, growth, less headaches
- C-suite: ROI, competitive edge, scalability
- BTL champions: easier day-to-day, looking good to boss

Cost efficiency:
- Gemini 2.5 Flash Vision + Image Gen
- No OpenAI - Gemini only
"""

from src.tools.storyboard.code_to_storyboard import CodeToStoryboardTool
from src.tools.storyboard.roadmap_to_storyboard import RoadmapToStoryboardTool
from src.tools.storyboard.unified_storyboard import UnifiedStoryboardTool
from src.tools.storyboard.coperniq_presets import (
    COPERNIQ_ICP,
    SANITIZE_RULES,
    get_icp_preset,
    get_audience_persona,
    sanitize_content,
)
from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    StoryboardUnderstanding,
)

__all__ = [
    # Core tools
    "CodeToStoryboardTool",
    "RoadmapToStoryboardTool",
    "UnifiedStoryboardTool",
    # Gemini client
    "GeminiStoryboardClient",
    "StoryboardUnderstanding",
    # ICP presets and utilities
    "COPERNIQ_ICP",
    "SANITIZE_RULES",
    "get_icp_preset",
    "get_audience_persona",
    "sanitize_content",
]
