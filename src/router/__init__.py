"""Agent Router Module - Dynamic task classification and routing.

This module provides:
- TaskClassifier: 3-stage classification (pattern → keyword → LLM)
- AgentRouter: Routes tasks to appropriate tool chains
- Pre-built chains: Storyboard, Video, Scrape, CodeRun, Knowledge, SQL
- RouterJobManager: Redis + Supabase job state management

Usage:
    from src.router import TaskClassifier, AgentRouter
    from src.router.schemas import TaskType, ClassificationRequest

    classifier = TaskClassifier()
    result = await classifier.classify(ClassificationRequest(query="create storyboard"))
"""

from src.router.classifier import TaskClassifier
from src.router.schemas import (
    ClassificationRequest,
    ClassificationResult,
    RouterJob,
    RouterJobResponse,
    RouterJobStatus,
    RouterJobStatusResponse,
    RouterRequest,
    TaskType,
)

__all__ = [
    # Schemas
    "TaskType",
    "RouterJobStatus",
    "ClassificationResult",
    "ClassificationRequest",
    "RouterRequest",
    "RouterJob",
    "RouterJobResponse",
    "RouterJobStatusResponse",
    # Classifier
    "TaskClassifier",
]
