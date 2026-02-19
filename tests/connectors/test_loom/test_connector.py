"""Tests for Loom connector."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.base import ConnectorInstance, ConnectorType
from src.connectors.loom.connector import LoomConnector
from src.knowledge.base import KnowledgeEntry, KnowledgeType, ExtractionResult


@pytest.fixture
def loom_instance():
    """Create Loom connector instance."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.LOOM,
        config={},
    )


def test_connector_metadata():
    """Test connector metadata."""
    connector = LoomConnector()

    assert connector.connector_type == ConnectorType.LOOM
    assert connector.display_name == "Loom"
    assert connector.auth_type.value == "manual"
    assert connector.supports_webhook is False


def test_get_required_config_fields():
    """Test get_required_config_fields returns empty list."""
    connector = LoomConnector()
    fields = connector.get_required_config_fields()

    assert fields == []


@pytest.mark.asyncio
async def test_test_connection_always_succeeds(loom_instance):
    """Test connection always succeeds for manual connector."""
    connector = LoomConnector()
    result = await connector.test_connection(loom_instance)

    assert result is True


@pytest.mark.asyncio
async def test_sync_returns_error(loom_instance):
    """Test sync method returns error message."""
    connector = LoomConnector()
    result = await connector.sync(loom_instance)

    assert result.success is False
    assert "upload_transcript" in result.error_message.lower()


@pytest.mark.asyncio
async def test_full_sync_returns_error(loom_instance):
    """Test full_sync method returns error message."""
    connector = LoomConnector()
    result = await connector.full_sync(loom_instance)

    assert result.success is False
    assert "upload_transcript" in result.error_message.lower()


@pytest.mark.asyncio
async def test_upload_transcript_success(loom_instance):
    """Test successful transcript upload."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        # Mock knowledge service
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service._save_entries = AsyncMock(return_value=3)
        mock_service_class.return_value = mock_service

        # Mock extractor
        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
            source_id="source_id",
            items_extracted=3,
            entries=[
                KnowledgeEntry(knowledge_type=KnowledgeType.FEATURE, content="Feature 1"),
                KnowledgeEntry(knowledge_type=KnowledgeType.FEATURE, content="Feature 2"),
                KnowledgeEntry(knowledge_type=KnowledgeType.PAIN_POINT, content="Pain 1"),
            ],
        ))
        mock_extractor_class.return_value = mock_extractor

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/abc123",
            transcript="This is a test transcript with feature mentions.",
            title="Product Demo",
        )

    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_extracted == 1
    assert result.items_created == 3
    mock_service._save_source.assert_called_once()
    mock_service._save_entries.assert_called_once()


@pytest.mark.asyncio
async def test_upload_transcript_no_title(loom_instance):
    """Test upload without title uses default."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
            source_id="source_id",
            entries=[],
        ))
        mock_extractor_class.return_value = mock_extractor

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/xyz",
            transcript="Short transcript",
        )

    assert result.success is True
    # Check that source was saved with default title
    call_args = mock_service._save_source.call_args[0][0]
    assert call_args.source_title == "Loom Video"


@pytest.mark.asyncio
async def test_upload_transcript_duplicate(loom_instance):
    """Test upload skips duplicate transcript."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        # Mock as duplicate
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]
        mock_service_class.return_value = mock_service

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/duplicate",
            transcript="Duplicate content",
        )

    assert result.success is True
    assert result.items_skipped == 1
    assert result.items_extracted == 0


@pytest.mark.asyncio
async def test_upload_transcript_extraction_error(loom_instance):
    """Test upload handles extraction errors."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service_class.return_value = mock_service

        # Mock extraction error
        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
            source_id="source_id",
            error="Extraction failed",
        ))
        mock_extractor_class.return_value = mock_extractor

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/error",
            transcript="Error transcript",
        )

    assert result.success is False
    assert result.error_message == "Extraction failed"
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_upload_transcript_save_error(loom_instance):
    """Test upload handles save errors."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(side_effect=Exception("Save failed"))
        mock_service_class.return_value = mock_service

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/save-error",
            transcript="Save error",
        )

    assert result.success is False
    assert "Save failed" in result.error_message


@pytest.mark.asyncio
async def test_upload_transcript_empty_transcript(loom_instance):
    """Test upload with empty transcript."""
    connector = LoomConnector()

    with patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
            source_id="source_id",
            entries=[],
        ))
        mock_extractor_class.return_value = mock_extractor

        result = await connector.upload_transcript(
            instance=loom_instance,
            video_url="https://loom.com/share/empty",
            transcript="",
        )

    assert result.success is True
    assert result.items_created == 0
