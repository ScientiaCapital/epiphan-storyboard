"""
Supabase Storage Service for Storyboards
=========================================

Handles auto-saving generated storyboards to Supabase Storage
and tracking metadata in the storyboard_assets table.
"""

import os
import logging
from datetime import datetime
from typing import Any
import uuid

logger = logging.getLogger(__name__)


class StoryboardStorage:
    """
    Storage service for storyboard images.

    Saves to:
    - Supabase Storage: coperniq-assets/generated-outputs/YYYY-MM-DD/
    - Supabase Table: storyboard_assets (metadata tracking)
    """

    def __init__(self):
        """Initialize storage client."""
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        """Lazy initialization of Supabase client."""
        if self._initialized:
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            logger.warning("[STORAGE] Supabase not configured - storage disabled")
            self._initialized = True
            return

        try:
            from supabase import create_client
            self._client = create_client(url, key)
            self._initialized = True
            logger.info("[STORAGE] Supabase client initialized")
        except ImportError:
            logger.warning("[STORAGE] supabase package not installed")
            self._initialized = True
        except Exception as e:
            logger.error(f"[STORAGE] Failed to initialize: {e}")
            self._initialized = True

    async def save_storyboard(
        self,
        png_bytes: bytes,
        audience: str,
        stage: str,
        input_type: str,
        headline: str | None = None,
        understanding: dict[str, Any] | None = None,
        org_id: str = "default",
    ) -> dict[str, Any] | None:
        """
        Save generated storyboard to Supabase Storage.

        Args:
            png_bytes: PNG image bytes
            audience: Target audience (e.g., 'top_tier_vc', 'field_crew')
            stage: Storyboard stage ('preview', 'demo', 'shipped')
            input_type: Input type ('code' or 'image')
            headline: Extracted headline from understanding
            understanding: Full understanding dict
            org_id: Organization ID for multi-tenant

        Returns:
            Dict with storage_path and public_url, or None if storage disabled
        """
        self._ensure_client()

        if not self._client:
            logger.debug("[STORAGE] Storage disabled - skipping save")
            return None

        try:
            # Generate unique filename
            date_prefix = datetime.now().strftime("%Y-%m-%d")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"storyboard_{audience}_{unique_id}.png"
            storage_path = f"generated-outputs/{date_prefix}/{filename}"

            # Upload to Supabase Storage
            result = self._client.storage.from_("coperniq-assets").upload(
                path=storage_path,
                file=png_bytes,
                file_options={"content-type": "image/png"}
            )

            # Get public URL
            public_url = self._client.storage.from_("coperniq-assets").get_public_url(storage_path)

            # Track in database
            self._client.table("storyboard_assets").insert({
                "storage_path": storage_path,
                "public_url": public_url,
                "audience": audience,
                "stage": stage,
                "input_type": input_type,
                "headline": headline,
                "understanding": understanding,
                "org_id": org_id,
            }).execute()

            logger.info(f"[STORAGE] Saved storyboard: {storage_path}")

            return {
                "storage_path": storage_path,
                "public_url": public_url,
            }

        except Exception as e:
            logger.error(f"[STORAGE] Failed to save storyboard: {e}")
            return None

    async def list_storyboards(
        self,
        org_id: str = "default",
        limit: int = 50,
        audience: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List saved storyboards.

        Args:
            org_id: Organization ID
            limit: Max results to return
            audience: Filter by audience type

        Returns:
            List of storyboard metadata dicts
        """
        self._ensure_client()

        if not self._client:
            return []

        try:
            query = self._client.table("storyboard_assets") \
                .select("*") \
                .eq("org_id", org_id) \
                .order("created_at", desc=True) \
                .limit(limit)

            if audience:
                query = query.eq("audience", audience)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"[STORAGE] Failed to list storyboards: {e}")
            return []


# Singleton instance
_storage_instance: StoryboardStorage | None = None


def get_storage() -> StoryboardStorage:
    """Get singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StoryboardStorage()
    return _storage_instance
