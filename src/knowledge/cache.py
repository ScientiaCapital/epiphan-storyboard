"""
Knowledge Cache - Singleton for fast in-memory knowledge access.

Loads all knowledge from Supabase at startup and provides
fast access for storyboard generation prompts.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeCache:
    """
    Singleton cache for knowledge data.

    Usage:
        # At startup
        cache = KnowledgeCache.get()
        await cache.load()

        # During storyboard generation
        guidelines = cache.get_language_guidelines("c_suite")
        context = cache.get_context("c_suite")
    """

    _instance: "KnowledgeCache | None" = None
    _loaded: bool = False

    # Cached data
    approved_terms: dict[str, list[str]]  # audience -> terms
    banned_terms: list[str]
    pain_points: dict[str, list[str]]     # audience -> pain points
    features: list[str]
    metrics: list[str]
    quotes: list[str]

    def __init__(self):
        """Initialize empty cache."""
        self.approved_terms = {}
        self.banned_terms = []
        self.pain_points = {}
        self.features = []
        self.metrics = []
        self.quotes = []

    @classmethod
    def get(cls) -> "KnowledgeCache":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._loaded = False

    async def load(self) -> None:
        """Load all knowledge from Supabase."""
        if self._loaded:
            logger.debug("Knowledge cache already loaded, skipping")
            return

        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")

            if not url or not key:
                logger.warning("Supabase credentials not set, using empty cache")
                self._loaded = True
                return

            client = create_client(url, key)

            # Query all knowledge
            response = client.table("coperniq_knowledge").select(
                "knowledge_type, content, audience, confidence_score"
            ).gte("confidence_score", 0.7).execute()

            if not response.data:
                logger.info("No knowledge data found in database")
                self._loaded = True
                return

            # Process and group by type
            for row in response.data:
                kt = row["knowledge_type"]
                content = row["content"]
                audiences = row.get("audience") or []

                if kt == "banned_term":
                    self.banned_terms.append(content)

                elif kt == "approved_term":
                    # Group by audience
                    if audiences:
                        for aud in audiences:
                            if aud not in self.approved_terms:
                                self.approved_terms[aud] = []
                            self.approved_terms[aud].append(content)
                    else:
                        # No audience = applies to all
                        for aud in ["business_owner", "c_suite", "btl_champion", "top_tier_vc", "field_crew"]:
                            if aud not in self.approved_terms:
                                self.approved_terms[aud] = []
                            self.approved_terms[aud].append(content)

                elif kt == "pain_point":
                    if audiences:
                        for aud in audiences:
                            if aud not in self.pain_points:
                                self.pain_points[aud] = []
                            self.pain_points[aud].append(content)
                    else:
                        # No audience = applies to all
                        for aud in ["business_owner", "c_suite", "btl_champion", "top_tier_vc", "field_crew"]:
                            if aud not in self.pain_points:
                                self.pain_points[aud] = []
                            self.pain_points[aud].append(content)

                elif kt == "feature":
                    self.features.append(content)

                elif kt == "metric":
                    self.metrics.append(content)

                elif kt == "quote":
                    self.quotes.append(content)

            # Deduplicate
            self.banned_terms = list(set(self.banned_terms))
            self.features = list(set(self.features))
            self.metrics = list(set(self.metrics))
            self.quotes = list(set(self.quotes))

            for aud in self.approved_terms:
                self.approved_terms[aud] = list(set(self.approved_terms[aud]))
            for aud in self.pain_points:
                self.pain_points[aud] = list(set(self.pain_points[aud]))

            self._loaded = True
            logger.info(f"Knowledge cache loaded: {self.stats()}")

        except Exception as e:
            logger.error(f"Failed to load knowledge cache: {e}")
            self._loaded = True  # Mark as loaded to prevent retry loops

    async def reload(self) -> None:
        """Force reload from database."""
        self._loaded = False
        self.approved_terms = {}
        self.banned_terms = []
        self.pain_points = {}
        self.features = []
        self.metrics = []
        self.quotes = []
        await self.load()

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "banned_terms": len(self.banned_terms),
            "approved_terms": sum(len(v) for v in self.approved_terms.values()),
            "pain_points": sum(len(v) for v in self.pain_points.values()),
            "features": len(self.features),
            "metrics": len(self.metrics),
            "quotes": len(self.quotes),
            "audiences_with_approved": list(self.approved_terms.keys()),
            "audiences_with_pain_points": list(self.pain_points.keys()),
        }

    def get_language_guidelines(self, audience: str) -> dict[str, list[str]]:
        """
        Get language guidelines for an audience.

        Returns:
            dict with "avoid" (banned terms) and "use" (approved terms)
        """
        return {
            "avoid": self.banned_terms.copy(),
            "use": self.approved_terms.get(audience, []).copy(),
        }

    def get_context(self, audience: str) -> dict[str, list[str]]:
        """
        Get knowledge context for prompt enrichment.

        Returns:
            dict with pain_points, features, metrics, quotes
        """
        return {
            "pain_points": self.pain_points.get(audience, [])[:5],
            "features": self.features[:10],
            "metrics": self.metrics[:5],
            "quotes": self.quotes[:3],
        }

    def is_loaded(self) -> bool:
        """Check if cache is loaded."""
        return self._loaded

    def get_company_context(self) -> dict[str, str]:
        """
        Get company context from knowledge base.

        Returns empty dict if no company info stored - prompts work without it.
        This is intentional: zero hardcoding philosophy.
        """
        # Company context would come from a company_info knowledge type
        # For now, return empty - let model use its training
        return {
            "company_name": "",
            "tagline": "",
            "target_market": "",
        }

    def get_proof_points(self) -> list[str]:
        """
        Get proof points/metrics for marketing.

        Returns metrics from knowledge base, or empty list.
        """
        return self.metrics.copy()

    def get_quotes_for_audience(self, audience: str) -> list[str]:
        """
        Get customer quotes, optionally filtered by audience.

        Returns up to 5 quotes for prompt context.
        """
        # For now, quotes aren't audience-tagged, return all
        return self.quotes[:5]
