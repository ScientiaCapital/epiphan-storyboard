"""Tests for KnowledgeCache singleton."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.knowledge.cache import KnowledgeCache


class TestKnowledgeCacheSingleton:
    """Test singleton behavior."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    def test_singleton_returns_same_instance(self):
        """Test that get() always returns same instance."""
        cache1 = KnowledgeCache.get()
        cache2 = KnowledgeCache.get()
        assert cache1 is cache2

    def test_reset_clears_singleton(self):
        """Test that reset() clears the singleton."""
        cache1 = KnowledgeCache.get()
        KnowledgeCache.reset()
        cache2 = KnowledgeCache.get()
        assert cache1 is not cache2


class TestKnowledgeCacheInit:
    """Test cache initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    def test_init_creates_empty_cache(self):
        """Test that new cache has empty data."""
        cache = KnowledgeCache.get()
        assert cache.banned_terms == []
        assert cache.approved_terms == {}
        assert cache.pain_points == {}
        assert cache.features == []
        assert cache.metrics == []
        assert cache.quotes == []

    def test_is_loaded_false_initially(self):
        """Test that cache is not loaded initially."""
        cache = KnowledgeCache.get()
        assert cache.is_loaded() is False


class TestKnowledgeCacheLoad:
    """Test cache loading."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    @pytest.mark.asyncio
    async def test_load_without_credentials_sets_loaded(self):
        """Test that load without credentials still marks loaded."""
        with patch.dict("os.environ", {}, clear=True):
            cache = KnowledgeCache.get()
            await cache.load()
            assert cache.is_loaded() is True
            assert cache.banned_terms == []

    @pytest.mark.asyncio
    async def test_load_only_runs_once(self):
        """Test that load only queries database once."""
        cache = KnowledgeCache.get()
        cache._loaded = True  # Simulate already loaded

        # This should not actually query anything
        await cache.load()
        assert cache.is_loaded() is True

    @pytest.mark.asyncio
    async def test_reload_forces_fresh_load(self):
        """Test that reload clears and reloads data."""
        cache = KnowledgeCache.get()
        cache._loaded = True
        cache.banned_terms = ["old_term"]

        with patch.dict("os.environ", {}, clear=True):
            await cache.reload()

        assert cache.is_loaded() is True
        assert cache.banned_terms == []  # Cleared


class TestKnowledgeCacheDataProcessing:
    """Test data processing and grouping."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    @pytest.mark.asyncio
    async def test_load_processes_banned_terms(self):
        """Test that banned terms are processed correctly."""
        mock_response = MagicMock()
        mock_response.data = [
            {"knowledge_type": "banned_term", "content": "API", "audience": None, "confidence_score": 1.0},
            {"knowledge_type": "banned_term", "content": "microservices", "audience": None, "confidence_score": 1.0},
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_response

        with patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_KEY": "key"}):
            with patch("supabase.create_client", return_value=mock_client):
                cache = KnowledgeCache.get()
                await cache.load()

        assert "API" in cache.banned_terms
        assert "microservices" in cache.banned_terms

    @pytest.mark.asyncio
    async def test_load_groups_approved_terms_by_audience(self):
        """Test that approved terms are grouped by audience."""
        mock_response = MagicMock()
        mock_response.data = [
            {"knowledge_type": "approved_term", "content": "saves time", "audience": ["c_suite", "business_owner"], "confidence_score": 1.0},
            {"knowledge_type": "approved_term", "content": "field friendly", "audience": ["field_crew"], "confidence_score": 1.0},
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_response

        with patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_KEY": "key"}):
            with patch("supabase.create_client", return_value=mock_client):
                cache = KnowledgeCache.get()
                await cache.load()

        assert "saves time" in cache.approved_terms.get("c_suite", [])
        assert "saves time" in cache.approved_terms.get("business_owner", [])
        assert "field friendly" in cache.approved_terms.get("field_crew", [])
        assert "field friendly" not in cache.approved_terms.get("c_suite", [])

    @pytest.mark.asyncio
    async def test_load_deduplicates_terms(self):
        """Test that duplicate terms are removed."""
        mock_response = MagicMock()
        mock_response.data = [
            {"knowledge_type": "banned_term", "content": "API", "audience": None, "confidence_score": 1.0},
            {"knowledge_type": "banned_term", "content": "API", "audience": None, "confidence_score": 1.0},
            {"knowledge_type": "banned_term", "content": "API", "audience": None, "confidence_score": 1.0},
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_response

        with patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_KEY": "key"}):
            with patch("supabase.create_client", return_value=mock_client):
                cache = KnowledgeCache.get()
                await cache.load()

        assert cache.banned_terms.count("API") == 1


class TestKnowledgeCacheGetters:
    """Test getter methods."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    def test_get_language_guidelines_returns_dict(self):
        """Test that get_language_guidelines returns proper structure."""
        cache = KnowledgeCache.get()
        cache.banned_terms = ["API", "microservices"]
        cache.approved_terms = {"c_suite": ["saves time", "ROI"]}

        result = cache.get_language_guidelines("c_suite")

        assert "avoid" in result
        assert "use" in result
        assert "API" in result["avoid"]
        assert "saves time" in result["use"]

    def test_get_language_guidelines_empty_audience(self):
        """Test that missing audience returns empty use list."""
        cache = KnowledgeCache.get()
        cache.banned_terms = ["API"]
        cache.approved_terms = {}

        result = cache.get_language_guidelines("unknown_audience")

        assert result["avoid"] == ["API"]
        assert result["use"] == []

    def test_get_context_returns_dict(self):
        """Test that get_context returns proper structure."""
        cache = KnowledgeCache.get()
        cache.pain_points = {"c_suite": ["PM in spreadsheets", "Manual invoicing"]}
        cache.features = ["Receptionist AI", "Document Engine"]
        cache.metrics = ["65% faster", "$3K savings"]
        cache.quotes = ["This changed everything"]

        result = cache.get_context("c_suite")

        assert "pain_points" in result
        assert "features" in result
        assert "metrics" in result
        assert "quotes" in result
        assert len(result["pain_points"]) <= 5
        assert len(result["features"]) <= 10

    def test_get_context_limits_results(self):
        """Test that get_context respects limits."""
        cache = KnowledgeCache.get()
        cache.pain_points = {"c_suite": [f"pain_{i}" for i in range(20)]}
        cache.features = [f"feature_{i}" for i in range(20)]

        result = cache.get_context("c_suite")

        assert len(result["pain_points"]) == 5
        assert len(result["features"]) == 10


class TestKnowledgeCacheStats:
    """Test stats method."""

    def setup_method(self):
        """Reset singleton before each test."""
        KnowledgeCache.reset()

    def test_stats_returns_counts(self):
        """Test that stats returns all counts."""
        cache = KnowledgeCache.get()
        cache.banned_terms = ["a", "b", "c"]
        cache.approved_terms = {"c_suite": ["x", "y"], "field_crew": ["z"]}
        cache.features = ["f1", "f2"]

        stats = cache.stats()

        assert stats["banned_terms"] == 3
        assert stats["approved_terms"] == 3  # Total across audiences
        assert stats["features"] == 2
        assert "c_suite" in stats["audiences_with_approved"]
        assert "field_crew" in stats["audiences_with_approved"]
