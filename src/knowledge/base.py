"""
Base classes for Coperniq Knowledge Brain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class SourceType(str, Enum):
    """Types of knowledge sources."""

    CLOSE_CRM_CALL = "close_crm_call"
    CLOSE_CRM_NOTE = "close_crm_note"
    LOOM_TRANSCRIPT = "loom_transcript"
    MIRO_BOARD = "miro_board"
    ENGINEER_CODE = "engineer_code"
    GONG_TRANSCRIPT = "gong_transcript"
    MANUAL_ENTRY = "manual_entry"


class KnowledgeType(str, Enum):
    """Types of knowledge entries."""

    FEATURE = "feature"  # Product feature
    PAIN_POINT = "pain_point"  # Customer pain point
    METRIC = "metric"  # Specific numbers/stats
    QUOTE = "quote"  # Verbatim customer quote
    APPROVED_TERM = "approved_term"  # Language that resonates
    BANNED_TERM = "banned_term"  # Language to avoid
    OBJECTION = "objection"  # Sales objections
    COMPETITOR = "competitor"  # Competitor mentions
    SUCCESS_STORY = "success_story"  # Customer wins
    USE_CASE = "use_case"  # Specific use cases
    PERSONA = "persona"  # ICP insights


@dataclass
class KnowledgeSource:
    """
    Represents a source of knowledge (call, transcript, code, etc.).
    """

    source_type: SourceType
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    file_path: Optional[str] = None
    source_title: Optional[str] = None
    source_date: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    participant_names: list[str] = field(default_factory=list)
    raw_content: Optional[str] = None
    content_hash: Optional[str] = None

    # Multi-tenant isolation
    org_id: Optional[str] = None

    # Set after database insert
    id: Optional[UUID] = None


@dataclass
class KnowledgeEntry:
    """
    A single piece of extracted knowledge.
    """

    knowledge_type: KnowledgeType
    content: str
    context: Optional[str] = None
    verbatim: bool = False

    # Relevance metadata
    audience: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    product_areas: list[str] = field(default_factory=list)

    # Quality signals
    confidence_score: float = 0.8
    usage_count: int = 0

    # Source attribution
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    company_name: Optional[str] = None

    # Link to source (set after ingestion)
    source_id: Optional[UUID] = None

    # Multi-tenant isolation
    org_id: Optional[str] = None

    # Set after database insert
    id: Optional[UUID] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        result = {
            "knowledge_type": self.knowledge_type.value,
            "content": self.content,
            "context": self.context,
            "verbatim": self.verbatim,
            "audience": self.audience,
            "industries": self.industries,
            "product_areas": self.product_areas,
            "confidence_score": self.confidence_score,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role,
            "company_name": self.company_name,
            "source_id": str(self.source_id) if self.source_id else None,
        }
        # Include org_id for multi-tenant isolation
        if self.org_id:
            result["org_id"] = self.org_id
        return result


@dataclass
class ExtractionResult:
    """Result of an extraction run."""

    source_id: UUID
    items_extracted: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_skipped: int = 0
    entries: list[KnowledgeEntry] = field(default_factory=list)
    error: Optional[str] = None
    execution_time_ms: int = 0
