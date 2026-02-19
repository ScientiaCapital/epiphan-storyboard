"""Tests for knowledge base classes."""

import pytest
from uuid import UUID

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgeSource,
    KnowledgeType,
    SourceType,
    ExtractionResult,
)


class TestSourceType:
    """Tests for SourceType enum."""

    def test_close_crm_call(self):
        assert SourceType.CLOSE_CRM_CALL.value == "close_crm_call"

    def test_close_crm_note(self):
        assert SourceType.CLOSE_CRM_NOTE.value == "close_crm_note"

    def test_loom_transcript(self):
        assert SourceType.LOOM_TRANSCRIPT.value == "loom_transcript"

    def test_miro_board(self):
        assert SourceType.MIRO_BOARD.value == "miro_board"

    def test_engineer_code(self):
        assert SourceType.ENGINEER_CODE.value == "engineer_code"


class TestKnowledgeType:
    """Tests for KnowledgeType enum."""

    def test_pain_point(self):
        assert KnowledgeType.PAIN_POINT.value == "pain_point"

    def test_metric(self):
        assert KnowledgeType.METRIC.value == "metric"

    def test_quote(self):
        assert KnowledgeType.QUOTE.value == "quote"

    def test_feature(self):
        assert KnowledgeType.FEATURE.value == "feature"

    def test_approved_term(self):
        assert KnowledgeType.APPROVED_TERM.value == "approved_term"

    def test_banned_term(self):
        assert KnowledgeType.BANNED_TERM.value == "banned_term"

    def test_all_types_exist(self):
        """Verify all expected knowledge types are defined."""
        expected = [
            "feature", "pain_point", "metric", "quote",
            "approved_term", "banned_term", "objection",
            "competitor", "success_story", "use_case", "persona"
        ]
        actual = [t.value for t in KnowledgeType]
        for exp in expected:
            assert exp in actual, f"Missing knowledge type: {exp}"


class TestKnowledgeSource:
    """Tests for KnowledgeSource dataclass."""

    def test_minimal_source(self):
        source = KnowledgeSource(source_type=SourceType.CLOSE_CRM_CALL)
        assert source.source_type == SourceType.CLOSE_CRM_CALL
        assert source.external_id is None
        assert source.raw_content is None

    def test_full_source(self):
        source = KnowledgeSource(
            source_type=SourceType.LOOM_TRANSCRIPT,
            external_id="loom_123",
            external_url="https://loom.com/share/abc",
            source_title="Demo Video",
            participant_names=["Alice", "Bob"],
            raw_content="Full transcript here...",
            content_hash="abc123",
        )
        assert source.source_type == SourceType.LOOM_TRANSCRIPT
        assert source.external_id == "loom_123"
        assert source.external_url == "https://loom.com/share/abc"
        assert "Alice" in source.participant_names

    def test_participant_names_default(self):
        source = KnowledgeSource(source_type=SourceType.MIRO_BOARD)
        assert source.participant_names == []


class TestKnowledgeEntry:
    """Tests for KnowledgeEntry dataclass."""

    def test_minimal_entry(self):
        entry = KnowledgeEntry(
            knowledge_type=KnowledgeType.PAIN_POINT,
            content="We lose $3K per job",
        )
        assert entry.knowledge_type == KnowledgeType.PAIN_POINT
        assert entry.content == "We lose $3K per job"
        assert entry.confidence_score == 0.8

    def test_full_entry(self):
        entry = KnowledgeEntry(
            knowledge_type=KnowledgeType.QUOTE,
            content="Our PM lives in Excel",
            context="Discussion about current workflow",
            verbatim=True,
            audience=["c_suite", "btl_champion"],
            industries=["solar", "hvac"],
            product_areas=["PM Cloud"],
            confidence_score=0.95,
            speaker_name="John Smith",
            speaker_role="CEO",
            company_name="Acme Solar",
        )
        assert entry.knowledge_type == KnowledgeType.QUOTE
        assert entry.verbatim is True
        assert "c_suite" in entry.audience
        assert entry.speaker_role == "CEO"

    def test_to_dict(self):
        entry = KnowledgeEntry(
            knowledge_type=KnowledgeType.METRIC,
            content="$50K in change orders",
            context="Annual loss discussion",
            confidence_score=0.9,
        )
        data = entry.to_dict()

        assert data["knowledge_type"] == "metric"
        assert data["content"] == "$50K in change orders"
        assert data["context"] == "Annual loss discussion"
        assert data["confidence_score"] == 0.9
        assert data["verbatim"] is False

    def test_to_dict_with_source_id(self):
        from uuid import uuid4
        source_id = uuid4()

        entry = KnowledgeEntry(
            knowledge_type=KnowledgeType.FEATURE,
            content="Receptionist AI",
            source_id=source_id,
        )
        data = entry.to_dict()

        assert data["source_id"] == str(source_id)


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_empty_result(self):
        from uuid import uuid4
        source_id = uuid4()

        result = ExtractionResult(source_id=source_id)
        assert result.source_id == source_id
        assert result.items_extracted == 0
        assert result.entries == []
        assert result.error is None

    def test_successful_result(self):
        from uuid import uuid4
        source_id = uuid4()

        entries = [
            KnowledgeEntry(
                knowledge_type=KnowledgeType.PAIN_POINT,
                content="Test pain point",
            ),
            KnowledgeEntry(
                knowledge_type=KnowledgeType.METRIC,
                content="$10K/month",
            ),
        ]

        result = ExtractionResult(
            source_id=source_id,
            items_extracted=2,
            entries=entries,
            execution_time_ms=500,
        )

        assert result.items_extracted == 2
        assert len(result.entries) == 2
        assert result.execution_time_ms == 500

    def test_error_result(self):
        from uuid import uuid4
        source_id = uuid4()

        result = ExtractionResult(
            source_id=source_id,
            error="LLM timeout",
            execution_time_ms=30000,
        )

        assert result.error == "LLM timeout"
        assert result.items_extracted == 0
