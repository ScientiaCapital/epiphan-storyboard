"""
Base classes for Epiphan Knowledge Brain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
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
    HUBSPOT_CALL = "hubspot_call"
    CLARI_CALL = "clari_call"


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
    external_id: str | None = None
    external_url: str | None = None
    file_path: str | None = None
    source_title: str | None = None
    source_date: datetime | None = None
    duration_seconds: int | None = None
    participant_names: list[str] = field(default_factory=list)
    raw_content: str | None = None
    content_hash: str | None = None

    # Multi-tenant isolation
    org_id: str | None = None

    # Set after database insert
    id: UUID | None = None


@dataclass
class KnowledgeEntry:
    """
    A single piece of extracted knowledge.
    """

    knowledge_type: KnowledgeType
    content: str
    context: str | None = None
    verbatim: bool = False

    # Relevance metadata
    audience: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    product_areas: list[str] = field(default_factory=list)

    # Quality signals
    confidence_score: float = 0.8
    usage_count: int = 0

    # Source attribution
    speaker_name: str | None = None
    speaker_role: str | None = None
    company_name: str | None = None

    # Link to source (set after ingestion)
    source_id: UUID | None = None

    # Multi-tenant isolation
    org_id: str | None = None

    # Set after database insert
    id: UUID | None = None

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
    error: str | None = None
    execution_time_ms: int = 0
