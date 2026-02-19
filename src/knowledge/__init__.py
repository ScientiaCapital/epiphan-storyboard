"""
Coperniq Knowledge Brain - Learning Pipeline
=============================================

Ingests content from various sources and extracts knowledge for storyboard generation.

Sources supported:
- Close CRM (calls, notes)
- Loom (video transcripts)
- Miro (board screenshots)
- Engineer code (feature code)

Usage:
    from src.knowledge import (
        KnowledgeIngestionService,
        CloseCRMIngester,
        LoomIngester,
        MiroIngester,
    )

    # Initialize service
    service = KnowledgeIngestionService()

    # Ingest from Close CRM
    await service.ingest_close_crm(api_key="...", since_date="2025-01-01")

    # Ingest from Loom
    await service.ingest_loom(transcript_url="...")

    # Query knowledge for storyboard
    knowledge = await service.get_knowledge_for_storyboard(
        audience="c_suite",
        knowledge_types=["pain_point", "metric", "approved_term"]
    )
"""

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgeSource,
    KnowledgeType,
    SourceType,
)
from src.knowledge.cache import KnowledgeCache
from src.knowledge.extraction import KnowledgeExtractor
from src.knowledge.close_crm import CloseCRMIngester
from src.knowledge.service import KnowledgeIngestionService

__all__ = [
    "KnowledgeEntry",
    "KnowledgeSource",
    "KnowledgeType",
    "SourceType",
    "KnowledgeCache",
    "KnowledgeExtractor",
    "CloseCRMIngester",
    "KnowledgeIngestionService",
]
