"""
Video Tools Module for Conductor-AI
====================================

AI-powered video prospecting orchestration suite:
- Script generation with Chinese LLM cost optimization
- AI video generation (Kling, HaiLuo, Runway, Pika, Luma)
- Loom analytics monitoring + viewer enrichment
- Optimal send time prediction
- Industry-specific demo template management

Cost efficiency:
- LLM: DeepSeek V3 ($0.20/$0.80 per 1M tokens) - 10-50x cheaper than GPT-4
- Video: Kling AI (~$0.01/sec) - 10-50x cheaper than Runway
"""

from src.tools.video.video_analytics import LoomViewTrackerTool, ViewerEnrichmentTool
from src.tools.video.video_generator import BatchVideoGeneratorTool, VideoGeneratorTool
from src.tools.video.video_scheduler import VideoSchedulerTool
from src.tools.video.video_script_generator import VideoScriptGeneratorTool
from src.tools.video.video_template_manager import VideoTemplateManagerTool

__all__ = [
    # Core script generation
    "VideoScriptGeneratorTool",
    # AI video generation
    "VideoGeneratorTool",
    "BatchVideoGeneratorTool",
    # Loom analytics + enrichment
    "LoomViewTrackerTool",
    "ViewerEnrichmentTool",
    # Send time optimization
    "VideoSchedulerTool",
    # Demo template management
    "VideoTemplateManagerTool",
]
