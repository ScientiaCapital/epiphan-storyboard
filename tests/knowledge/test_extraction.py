"""Tests for knowledge extraction module."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from src.knowledge.base import (
    KnowledgeSource,
    KnowledgeType,
    SourceType,
)
from src.knowledge.extraction import (
    KnowledgeExtractor,
    ExtractorConfig,
    EXTRACTION_PROMPT,
)


class TestExtractorConfig:
    """Tests for ExtractorConfig."""

    def test_default_config(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            config = ExtractorConfig()
            assert config.openrouter_api_key == "test-key"
            assert config.model == "deepseek/deepseek-chat-v3"
            assert config.temperature == 0.6  # Higher for creative extraction

    def test_explicit_key(self):
        config = ExtractorConfig(openrouter_api_key="explicit-key")
        assert config.openrouter_api_key == "explicit-key"

    def test_custom_model(self):
        config = ExtractorConfig(
            openrouter_api_key="key",
            model="custom/model",
        )
        assert config.model == "custom/model"


class TestExtractionPrompt:
    """Tests for the extraction prompt template."""

    def test_prompt_has_content_placeholder(self):
        assert "{content}" in EXTRACTION_PROMPT

    def test_prompt_has_context_placeholder(self):
        assert "{context}" in EXTRACTION_PROMPT

    def test_prompt_mentions_knowledge_types(self):
        # New minimal prompt uses lowercase
        for kt in ["Pain points", "Metrics", "Quotes", "Features"]:
            assert kt in EXTRACTION_PROMPT

    def test_prompt_requests_json(self):
        assert "JSON" in EXTRACTION_PROMPT


class TestKnowledgeExtractor:
    """Tests for KnowledgeExtractor class."""

    def test_init_default(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test"}):
            extractor = KnowledgeExtractor()
            assert extractor.config is not None

    def test_init_with_config(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)
        assert extractor.config.openrouter_api_key == "test"

    @pytest.mark.asyncio
    async def test_extract_no_content(self):
        """Test extraction with no content returns error."""
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(
            source_type=SourceType.CLOSE_CRM_CALL,
            raw_content=None,
        )
        source.id = uuid4()

        result = await extractor.extract(source)

        assert result.error == "No content to extract from"
        assert result.items_extracted == 0


class TestJsonRepair:
    """Tests for JSON repair functionality."""

    def test_repair_unterminated_string(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        broken = '{"key": "value'
        repaired = extractor._repair_json(broken)
        assert repaired.count('"') % 2 == 0

    def test_repair_missing_brace(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        broken = '{"key": "value"'
        repaired = extractor._repair_json(broken)
        assert repaired.endswith("}")

    def test_repair_missing_bracket(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        broken = '{"items": ["a", "b"'
        repaired = extractor._repair_json(broken)
        assert "]" in repaired

    def test_repair_trailing_comma(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        broken = '{"items": ["a", "b",]}'
        repaired = extractor._repair_json(broken)
        # Should be parseable
        data = json.loads(repaired)
        assert data["items"] == ["a", "b"]


class TestResponseParsing:
    """Tests for parsing extraction responses."""

    def test_parse_valid_response(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.CLOSE_CRM_CALL)
        source.id = uuid4()

        response = json.dumps({
            "extractions": [
                {
                    "knowledge_type": "pain_point",
                    "content": "We lose $3K per job",
                    "context": "Discussing invoicing issues",
                    "verbatim": True,
                    "confidence_score": 0.9,
                    "speaker_name": "John",
                    "speaker_role": "CEO",
                }
            ],
            "summary": "One pain point extracted",
        })

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 1
        assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT
        assert entries[0].content == "We lose $3K per job"
        assert entries[0].verbatim is True
        assert entries[0].speaker_name == "John"

    def test_parse_markdown_wrapped_json(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.LOOM_TRANSCRIPT)
        source.id = uuid4()

        response = """```json
{
    "extractions": [
        {
            "knowledge_type": "metric",
            "content": "$50K in change orders",
            "confidence_score": 0.85
        }
    ],
    "summary": "One metric"
}
```"""

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 1
        assert entries[0].knowledge_type == KnowledgeType.METRIC
        assert entries[0].content == "$50K in change orders"

    def test_parse_multiple_extractions(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.MIRO_BOARD)
        source.id = uuid4()

        response = json.dumps({
            "extractions": [
                {
                    "knowledge_type": "feature",
                    "content": "Receptionist AI",
                    "product_areas": ["Intelligence"],
                },
                {
                    "knowledge_type": "feature",
                    "content": "Document Engine",
                    "product_areas": ["PM Cloud"],
                },
                {
                    "knowledge_type": "quote",
                    "content": "Our PM lives in Excel",
                    "verbatim": True,
                },
            ],
            "summary": "Three items extracted",
        })

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 3
        assert entries[0].knowledge_type == KnowledgeType.FEATURE
        assert entries[2].knowledge_type == KnowledgeType.QUOTE
        assert entries[2].verbatim is True

    def test_parse_unknown_type_skipped(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.ENGINEER_CODE)
        source.id = uuid4()

        response = json.dumps({
            "extractions": [
                {
                    "knowledge_type": "unknown_type",
                    "content": "This should be skipped",
                },
                {
                    "knowledge_type": "feature",
                    "content": "This should be kept",
                },
            ],
            "summary": "Two items",
        })

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 1
        assert entries[0].content == "This should be kept"

    def test_parse_empty_content_skipped(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.CLOSE_CRM_NOTE)
        source.id = uuid4()

        response = json.dumps({
            "extractions": [
                {
                    "knowledge_type": "pain_point",
                    "content": "",  # Empty content
                },
                {
                    "knowledge_type": "pain_point",
                    "content": "Valid content",
                },
            ],
        })

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 1
        assert entries[0].content == "Valid content"

    def test_parse_invalid_json_returns_empty(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.CLOSE_CRM_CALL)
        source.id = uuid4()

        response = "This is not valid JSON at all"

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 0

    def test_parse_with_audience_and_industries(self):
        config = ExtractorConfig(openrouter_api_key="test")
        extractor = KnowledgeExtractor(config=config)

        source = KnowledgeSource(source_type=SourceType.CLOSE_CRM_CALL)
        source.id = uuid4()

        response = json.dumps({
            "extractions": [
                {
                    "knowledge_type": "approved_term",
                    "content": "saves you time",
                    "audience": ["c_suite", "business_owner"],
                    "industries": ["solar", "hvac"],
                    "product_areas": ["PM Cloud"],
                }
            ],
        })

        entries = extractor._parse_extraction_response(response, source)

        assert len(entries) == 1
        assert "c_suite" in entries[0].audience
        assert "solar" in entries[0].industries
        assert "PM Cloud" in entries[0].product_areas
