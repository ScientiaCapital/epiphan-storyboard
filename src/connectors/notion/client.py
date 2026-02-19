"""Notion REST API client.

Official API docs: https://developers.notion.com/reference/intro
"""

import logging
from typing import Any

import httpx

from src.connectors.notion.schemas import (
    NotionBlock,
    NotionBlocksResponse,
    NotionDatabase,
    NotionDatabaseQueryResponse,
    NotionPage,
    NotionSearchResponse,
)

logger = logging.getLogger(__name__)


class NotionAPIClient:
    """Client for Notion REST API.

    Rate limits:
    - 3 requests per second per integration
    - Cursor-based pagination

    API Version: 2022-06-28
    """

    BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"

    def __init__(self, access_token: str):
        """Initialize Notion client.

        Args:
            access_token: Notion OAuth access token or internal integration token
        """
        self.access_token = access_token

    async def search(
        self,
        query: str = "",
        filter_type: str | None = None,  # "page" or "database"
        cursor: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[NotionPage | NotionDatabase], str | None]:
        """Search pages and databases.

        Args:
            query: Search query (empty string returns all)
            filter_type: Filter by "page" or "database"
            cursor: Pagination cursor from previous call
            page_size: Results per page (max 100)

        Returns:
            Tuple of (results, next_cursor)
        """
        payload: dict[str, Any] = {
            "page_size": min(page_size, 100),
        }

        if query:
            payload["query"] = query

        if filter_type:
            payload["filter"] = {"property": "object", "value": filter_type}

        if cursor:
            payload["start_cursor"] = cursor

        result = await self._post("/search", payload)

        # Parse response
        response = NotionSearchResponse(**result)

        # Convert results to Page or Database objects
        items: list[NotionPage | NotionDatabase] = []
        for item_dict in response.results:
            try:
                if item_dict.get("object") == "page":
                    items.append(NotionPage(**item_dict))
                elif item_dict.get("object") == "database":
                    items.append(NotionDatabase(**item_dict))
            except Exception as e:
                logger.warning(f"Failed to parse item {item_dict.get('id')}: {e}")
                continue

        next_cursor = response.next_cursor if response.has_more else None

        logger.info(
            f"[NOTION] Searched {len(items)} items (cursor: {cursor} -> {next_cursor})"
        )
        return items, next_cursor

    async def get_page(self, page_id: str) -> NotionPage:
        """Get page metadata.

        Args:
            page_id: Page ID (with or without hyphens)

        Returns:
            NotionPage object
        """
        page_id = self._normalize_id(page_id)
        result = await self._get(f"/pages/{page_id}")
        return NotionPage(**result)

    async def get_database(self, database_id: str) -> NotionDatabase:
        """Get database metadata.

        Args:
            database_id: Database ID (with or without hyphens)

        Returns:
            NotionDatabase object
        """
        database_id = self._normalize_id(database_id)
        result = await self._get(f"/databases/{database_id}")
        return NotionDatabase(**result)

    async def get_blocks(
        self,
        block_id: str,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[NotionBlock], str | None]:
        """Get child blocks of a page or block.

        Args:
            block_id: Page ID or block ID
            cursor: Pagination cursor
            page_size: Blocks per page (max 100)

        Returns:
            Tuple of (blocks, next_cursor)
        """
        block_id = self._normalize_id(block_id)

        params: dict[str, Any] = {
            "page_size": min(page_size, 100),
        }

        if cursor:
            params["start_cursor"] = cursor

        result = await self._get(f"/blocks/{block_id}/children", params=params)

        # Parse response
        response = NotionBlocksResponse(**result)

        # Convert to Block objects
        blocks: list[NotionBlock] = []
        for block_dict in response.results:
            try:
                blocks.append(NotionBlock(**block_dict))
            except Exception as e:
                logger.warning(f"Failed to parse block {block_dict.get('id')}: {e}")
                continue

        next_cursor = response.next_cursor if response.has_more else None

        logger.info(f"[NOTION] Fetched {len(blocks)} blocks from {block_id}")
        return blocks, next_cursor

    async def query_database(
        self,
        database_id: str,
        cursor: str | None = None,
        page_size: int = 100,
        filter_dict: dict | None = None,
        sorts: list[dict] | None = None,
    ) -> tuple[list[NotionPage], str | None]:
        """Query database rows (pages).

        Args:
            database_id: Database ID
            cursor: Pagination cursor
            page_size: Pages per page (max 100)
            filter_dict: Notion filter object
            sorts: List of sort objects

        Returns:
            Tuple of (pages, next_cursor)
        """
        database_id = self._normalize_id(database_id)

        payload: dict[str, Any] = {
            "page_size": min(page_size, 100),
        }

        if cursor:
            payload["start_cursor"] = cursor

        if filter_dict:
            payload["filter"] = filter_dict

        if sorts:
            payload["sorts"] = sorts

        result = await self._post(f"/databases/{database_id}/query", payload)

        # Parse response
        response = NotionDatabaseQueryResponse(**result)

        # Convert to Page objects
        pages: list[NotionPage] = []
        for page_dict in response.results:
            try:
                pages.append(NotionPage(**page_dict))
            except Exception as e:
                logger.warning(f"Failed to parse page {page_dict.get('id')}: {e}")
                continue

        next_cursor = response.next_cursor if response.has_more else None

        logger.info(f"[NOTION] Queried {len(pages)} pages from database {database_id}")
        return pages, next_cursor

    async def get_all_blocks(self, page_id: str) -> list[NotionBlock]:
        """Recursively get all blocks from a page (including nested blocks).

        Args:
            page_id: Page ID

        Returns:
            List of all blocks (flattened)
        """
        all_blocks = []

        async def fetch_recursive(block_id: str):
            cursor = None
            while True:
                blocks, cursor = await self.get_blocks(block_id, cursor=cursor)
                all_blocks.extend(blocks)

                # Recursively fetch children if block has children
                for block in blocks:
                    if block.has_children:
                        await fetch_recursive(block.id)

                if not cursor:
                    break

        await fetch_recursive(page_id)
        return all_blocks

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute GET request.

        Args:
            endpoint: API endpoint (e.g., "/pages/{id}")
            params: Query parameters

        Returns:
            Response data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self._get_headers(),
                params=params or {},
            )

            response.raise_for_status()
            return response.json()

    async def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute POST request.

        Args:
            endpoint: API endpoint
            payload: JSON payload

        Returns:
            Response data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}{endpoint}",
                headers=self._get_headers(),
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth and API version.

        Returns:
            Headers dict
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": self.API_VERSION,
        }

    def _normalize_id(self, id_str: str) -> str:
        """Normalize ID by removing hyphens.

        Notion IDs can be with or without hyphens. API accepts both,
        but we normalize for consistency.

        Args:
            id_str: ID string

        Returns:
            Normalized ID without hyphens
        """
        return id_str.replace("-", "")
