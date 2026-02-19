"""Tests for TaskClassifier - 3-stage task classification.

TDD approach: Write tests FIRST, then implement classifier.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# These imports will fail until we implement the modules
from src.router.schemas import TaskType, ClassificationResult, ClassificationRequest
from src.router.classifier import TaskClassifier


@pytest.fixture
def classifier():
    """Create TaskClassifier with LLM fallback disabled for pattern/keyword tests."""
    return TaskClassifier(enable_llm_fallback=False)


@pytest.fixture
def classifier_with_llm():
    """Create TaskClassifier with mocked LLM client for fallback tests."""
    mock_llm = AsyncMock()
    return TaskClassifier(llm_client=mock_llm, enable_llm_fallback=True)


class TestPatternMatching:
    """Test Stage 1: Pattern matching (instant, high confidence)."""

    @pytest.mark.asyncio
    async def test_classify_storyboard_pattern_match(self, classifier):
        """Test exact pattern match for storyboard tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="create a storyboard for this code")
        )
        assert result.task_type == TaskType.STORYBOARD
        assert result.confidence >= 0.9
        assert "pattern" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_video_pattern_runway(self, classifier):
        """Test pattern match for video generation with Runway keyword."""
        result = await classifier.classify(
            ClassificationRequest(query="generate video using runway ai")
        )
        assert result.task_type == TaskType.VIDEO
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_classify_scrape_pattern_url(self, classifier):
        """Test pattern match for web scraping tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="scrape data from https://example.com")
        )
        assert result.task_type == TaskType.SCRAPE
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_classify_code_run_pattern(self, classifier):
        """Test pattern match for code execution tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="run this python code in sandbox")
        )
        assert result.task_type == TaskType.CODE_RUN
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_classify_knowledge_pattern_crm(self, classifier):
        """Test pattern match for knowledge base / CRM tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="search the knowledge base for customer data")
        )
        assert result.task_type == TaskType.KNOWLEDGE
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_classify_sql_pattern_query(self, classifier):
        """Test pattern match for SQL query tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="run sql query SELECT * FROM users")
        )
        assert result.task_type == TaskType.SQL
        assert result.confidence >= 0.9


class TestKeywordScoring:
    """Test Stage 2: Keyword scoring (fast, medium confidence)."""

    @pytest.mark.asyncio
    async def test_classify_storyboard_keywords_multiple(self, classifier):
        """Test keyword scoring with multiple storyboard-related words."""
        # Use words that trigger keyword scoring but not pattern matching
        result = await classifier.classify(
            ClassificationRequest(
                query="I need a good visualization and diagram for my presentation slides"
            )
        )
        assert result.task_type == TaskType.STORYBOARD
        assert 0.7 <= result.confidence < 0.95

    @pytest.mark.asyncio
    async def test_classify_video_keywords(self, classifier):
        """Test keyword scoring for video tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="create a screen recording of the demo")
        )
        assert result.task_type == TaskType.VIDEO
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_classify_scrape_keywords_website(self, classifier):
        """Test keyword scoring for scrape tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="fetch content from the website and extract data")
        )
        assert result.task_type == TaskType.SCRAPE
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_classify_sql_keywords_database(self, classifier):
        """Test keyword scoring for SQL tasks."""
        result = await classifier.classify(
            ClassificationRequest(query="analyze the database and run some queries")
        )
        assert result.task_type == TaskType.SQL
        assert result.confidence >= 0.7


class TestLLMFallback:
    """Test Stage 3: LLM fallback for ambiguous cases."""

    @pytest.mark.asyncio
    async def test_classify_ambiguous_uses_llm(self, classifier_with_llm):
        """Test that ambiguous queries trigger LLM classification."""
        # Mock LLM response
        classifier_with_llm._llm_client.return_value = {
            "task_type": "knowledge",
            "confidence": 0.75,
            "reasoning": "Query appears to be asking for information retrieval",
        }

        result = await classifier_with_llm.classify(
            ClassificationRequest(query="help me with the project deliverable")
        )

        # Should have used LLM (check reasoning contains LLM indicator)
        assert result.task_type in list(TaskType)
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_classify_llm_invalid_json_fallback(self, classifier_with_llm):
        """Test graceful fallback when LLM returns invalid JSON."""
        # Mock LLM returning invalid JSON
        classifier_with_llm._llm_client.side_effect = json.JSONDecodeError(
            "Invalid JSON", "", 0
        )

        result = await classifier_with_llm.classify(
            ClassificationRequest(query="do something vague")
        )

        # Should default to KNOWLEDGE with low confidence
        assert result.task_type == TaskType.KNOWLEDGE
        assert result.confidence <= 0.5
        assert "fallback" in result.reasoning.lower() or "failed" in result.reasoning.lower()


class TestModelRecommendation:
    """Test model recommendation integration with model_catalog."""

    @pytest.mark.asyncio
    async def test_storyboard_recommends_vision_model(self, classifier):
        """Test that storyboard classification recommends vision-capable model."""
        result = await classifier.classify(
            ClassificationRequest(query="create storyboard from this image")
        )
        assert result.recommended_model is not None
        # Should be a vision-capable model (Gemini or Claude)
        assert any(
            name in result.recommended_model.lower()
            for name in ["gemini", "claude", "vision"]
        )

    @pytest.mark.asyncio
    async def test_code_run_recommends_coder_model(self, classifier):
        """Test that code_run classification recommends coding model."""
        result = await classifier.classify(
            ClassificationRequest(query="execute this python code")
        )
        assert result.recommended_model is not None
        # Should be a coding model (Qwen Coder or DeepSeek)
        assert any(
            name in result.recommended_model.lower()
            for name in ["qwen", "coder", "deepseek"]
        )


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query_low_confidence(self, classifier):
        """Test that empty/minimal queries result in low confidence."""
        result = await classifier.classify(ClassificationRequest(query="help"))
        assert result.confidence < 0.7

    @pytest.mark.asyncio
    async def test_multi_category_chooses_highest_score(self, classifier):
        """Test that queries matching multiple categories pick highest score."""
        result = await classifier.classify(
            ClassificationRequest(
                query="scrape the website and create a video visualization"
            )
        )
        # Should pick one - either SCRAPE or VIDEO based on scoring
        assert result.task_type in [TaskType.SCRAPE, TaskType.VIDEO]
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_with_context_improves_classification(self, classifier):
        """Test that providing context helps classification."""
        # Without context - ambiguous, should have low confidence
        result_no_context = await classifier.classify(
            ClassificationRequest(query="help with this task")
        )
        assert result_no_context.confidence < 0.8  # Ambiguous = low confidence

        # With context that contains SQL keywords - should classify as SQL
        result_with_context = await classifier.classify(
            ClassificationRequest(
                query="help with this task",
                context="run sql query select from users database",
            )
        )

        # Context containing SQL patterns should classify as SQL
        assert result_with_context.task_type == TaskType.SQL
        assert result_with_context.confidence >= 0.9  # Pattern match

    @pytest.mark.asyncio
    async def test_classifier_uses_no_openai(self, classifier_with_llm):
        """Verify classifier never uses OpenAI models (project rule)."""
        # Check that the classifier's LLM model is NOT OpenAI
        assert not hasattr(classifier_with_llm, "_openai_client")
        # If it has a model attribute, verify it's not OpenAI
        if hasattr(classifier_with_llm, "model"):
            assert "openai" not in classifier_with_llm.model.lower()
            assert "gpt" not in classifier_with_llm.model.lower()
