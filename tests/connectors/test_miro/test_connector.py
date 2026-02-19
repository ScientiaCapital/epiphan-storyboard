"""Tests for Miro connector."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.base import ConnectorInstance, ConnectorType
from src.connectors.miro.connector import MiroConnector
from src.knowledge.base import KnowledgeEntry, KnowledgeType, ExtractionResult


@pytest.fixture
def miro_instance():
    """Create Miro connector instance."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.MIRO,
        config={},
    )


@pytest.fixture
def sample_image_data():
    """Create sample image data."""
    return b"fake-png-data"


def test_connector_metadata():
    """Test connector metadata."""
    connector = MiroConnector()

    assert connector.connector_type == ConnectorType.MIRO
    assert connector.display_name == "Miro"
    assert connector.auth_type.value == "manual"
    assert connector.supports_webhook is False


def test_get_required_config_fields():
    """Test get_required_config_fields returns empty list."""
    connector = MiroConnector()
    fields = connector.get_required_config_fields()

    assert fields == []


@pytest.mark.asyncio
async def test_test_connection_always_succeeds(miro_instance):
    """Test connection always succeeds for manual connector."""
    connector = MiroConnector()
    result = await connector.test_connection(miro_instance)

    assert result is True


@pytest.mark.asyncio
async def test_sync_returns_error(miro_instance):
    """Test sync method returns error message."""
    connector = MiroConnector()
    result = await connector.sync(miro_instance)

    assert result.success is False
    assert "upload_screenshot" in result.error_message.lower()


@pytest.mark.asyncio
async def test_full_sync_returns_error(miro_instance):
    """Test full_sync method returns error message."""
    connector = MiroConnector()
    result = await connector.full_sync(miro_instance)

    assert result.success is False
    assert "upload_screenshot" in result.error_message.lower()


@pytest.mark.asyncio
async def test_upload_screenshot_success(miro_instance, sample_image_data):
    """Test successful screenshot upload."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        # Mock Gemini vision
        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Product Roadmap"
        mock_understanding.tagline = "Q1 2025 Features"
        mock_understanding.what_it_does = "Shows upcoming features"
        mock_understanding.business_value = "Better planning"
        mock_understanding.who_benefits = "Product team"
        mock_understanding.differentiator = "Visual workflow"
        mock_understanding.pain_point_addressed = "Lack of visibility"
        mock_understanding.raw_extracted_text = "Feature A, Feature B"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

        # Mock knowledge service
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service._save_entries = AsyncMock(return_value=2)
        mock_service_class.return_value = mock_service

        # Mock extractor
        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
            source_id="source_id",
            items_extracted=2,
            entries=[
                KnowledgeEntry(knowledge_type=KnowledgeType.FEATURE, content="Feature A"),
                KnowledgeEntry(knowledge_type=KnowledgeType.FEATURE, content="Feature B"),
            ],
        ))
        mock_extractor_class.return_value = mock_extractor

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
            board_url="https://miro.com/app/board/abc123",
            title="Product Roadmap Q1",
        )

    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_extracted == 1
    assert result.items_created == 2
    mock_gemini.understand_image.assert_called_once()
    mock_service._save_source.assert_called_once()
    mock_service._save_entries.assert_called_once()


@pytest.mark.asyncio
async def test_upload_screenshot_no_title(miro_instance, sample_image_data):
    """Test upload without title uses default."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Test"
        mock_understanding.tagline = "Test"
        mock_understanding.what_it_does = "Test"
        mock_understanding.business_value = "Test"
        mock_understanding.who_benefits = "Test"
        mock_understanding.differentiator = "Test"
        mock_understanding.pain_point_addressed = "Test"
        mock_understanding.raw_extracted_text = "Test"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

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

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
        )

    assert result.success is True
    # Check that source was saved with default title
    call_args = mock_service._save_source.call_args[0][0]
    assert call_args.source_title == "Miro Board"


@pytest.mark.asyncio
async def test_upload_screenshot_duplicate(miro_instance, sample_image_data):
    """Test upload skips duplicate screenshot."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Test"
        mock_understanding.tagline = "Test"
        mock_understanding.what_it_does = "Test"
        mock_understanding.business_value = "Test"
        mock_understanding.who_benefits = "Test"
        mock_understanding.differentiator = "Test"
        mock_understanding.pain_point_addressed = "Test"
        mock_understanding.raw_extracted_text = "Test"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

        # Mock as duplicate
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]
        mock_service_class.return_value = mock_service

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
        )

    assert result.success is True
    assert result.items_skipped == 1
    assert result.items_extracted == 0


@pytest.mark.asyncio
async def test_upload_screenshot_vision_error(miro_instance, sample_image_data):
    """Test upload handles vision processing errors."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class:

        mock_gemini = Mock()
        mock_gemini.understand_image = AsyncMock(side_effect=Exception("Vision API Error"))
        mock_gemini_class.return_value = mock_gemini

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
        )

    assert result.success is False
    assert "Vision API Error" in result.error_message


@pytest.mark.asyncio
async def test_upload_screenshot_extraction_error(miro_instance, sample_image_data):
    """Test upload handles extraction errors."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Test"
        mock_understanding.tagline = "Test"
        mock_understanding.what_it_does = "Test"
        mock_understanding.business_value = "Test"
        mock_understanding.who_benefits = "Test"
        mock_understanding.differentiator = "Test"
        mock_understanding.pain_point_addressed = "Test"
        mock_understanding.raw_extracted_text = "Test"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

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

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
        )

    assert result.success is False
    assert result.error_message == "Extraction failed"
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_upload_screenshot_save_error(miro_instance, sample_image_data):
    """Test upload handles save errors."""
    connector = MiroConnector()

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Test"
        mock_understanding.tagline = "Test"
        mock_understanding.what_it_does = "Test"
        mock_understanding.business_value = "Test"
        mock_understanding.who_benefits = "Test"
        mock_understanding.differentiator = "Test"
        mock_understanding.pain_point_addressed = "Test"
        mock_understanding.raw_extracted_text = "Test"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(side_effect=Exception("Save failed"))
        mock_service_class.return_value = mock_service

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
        )

    assert result.success is False
    assert "Save failed" in result.error_message


@pytest.mark.asyncio
async def test_upload_screenshot_with_board_url(miro_instance, sample_image_data):
    """Test upload preserves board URL."""
    connector = MiroConnector()

    board_url = "https://miro.com/app/board/xyz789"

    with patch("src.tools.storyboard.gemini_client.GeminiStoryboardClient") as mock_gemini_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class, \
         patch("src.knowledge.extraction.KnowledgeExtractor") as mock_extractor_class:

        mock_gemini = Mock()
        mock_understanding = Mock()
        mock_understanding.headline = "Test"
        mock_understanding.tagline = "Test"
        mock_understanding.what_it_does = "Test"
        mock_understanding.business_value = "Test"
        mock_understanding.who_benefits = "Test"
        mock_understanding.differentiator = "Test"
        mock_understanding.pain_point_addressed = "Test"
        mock_understanding.raw_extracted_text = "Test"
        mock_gemini.understand_image = AsyncMock(return_value=mock_understanding)
        mock_gemini_class.return_value = mock_gemini

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

        result = await connector.upload_screenshot(
            instance=miro_instance,
            image_data=sample_image_data,
            board_url=board_url,
        )

    assert result.success is True
    # Check that source was saved with correct URL
    call_args = mock_service._save_source.call_args[0][0]
    assert call_args.external_url == board_url
