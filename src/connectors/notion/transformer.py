"""Transform Notion data to KnowledgeEntry objects."""

import logging
from datetime import datetime

from src.connectors.notion.schemas import (
    NotionBlock,
    NotionDatabase,
    NotionPage,
)
from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgeSource,
    KnowledgeType,
    SourceType,
)
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class NotionTransformer:
    """Transform Notion pages and databases into knowledge entries."""

    def __init__(self):
        self.extractor = KnowledgeExtractor()

    async def transform_page(
        self,
        page: NotionPage,
        blocks: list[NotionBlock],
        org_id: str,
    ) -> tuple[KnowledgeSource, list[KnowledgeEntry]]:
        """Transform a Notion page into knowledge entries.

        Pages can contain:
        - Product documentation → features, use_cases
        - Meeting notes → pain_points, quotes, metrics
        - Wiki content → approved_terms, features
        - Product roadmaps → features, use_cases

        Args:
            page: Notion page metadata
            blocks: Page blocks (content)
            org_id: Organization ID for source

        Returns:
            Tuple of (source, entries)
        """
        # Create knowledge source
        source = KnowledgeSource(
            source_type=SourceType.MANUAL_ENTRY,  # Use existing enum value
            external_id=page.id,
            external_url=page.url,
            source_title=f"Notion Page: {page.get_title()}",
            source_date=page.created_time,
            raw_content=self._page_to_text(page, blocks),
        )

        # Build context
        context_parts = [f"Notion page: {page.get_title()}"]

        # Infer knowledge types from page title and content
        title_lower = page.get_title().lower()

        if any(keyword in title_lower for keyword in ["roadmap", "feature", "spec", "prd"]):
            context_parts.append("Extract features and use cases")
        elif any(keyword in title_lower for keyword in ["meeting", "notes", "call"]):
            context_parts.append("Extract pain points, quotes, and metrics")
        elif any(keyword in title_lower for keyword in ["docs", "wiki", "guide", "how to"]):
            context_parts.append("Extract features and approved terms")
        elif any(keyword in title_lower for keyword in ["customer", "user", "feedback"]):
            context_parts.append("Extract pain points, quotes, and use cases")

        additional_context = " | ".join(context_parts)

        # Extract knowledge using LLM
        extraction_result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        return source, extraction_result.entries

    async def transform_database(
        self,
        database: NotionDatabase,
        pages: list[NotionPage],
        org_id: str,
    ) -> tuple[KnowledgeSource, list[KnowledgeEntry]]:
        """Transform a Notion database into knowledge entries.

        Databases often contain:
        - Feature requests → features, use_cases
        - Customer feedback → pain_points, quotes
        - Product specs → features, approved_terms

        Args:
            database: Notion database metadata
            pages: Database pages (rows)
            org_id: Organization ID for source

        Returns:
            Tuple of (source, entries)
        """
        # Create knowledge source
        source = KnowledgeSource(
            source_type=SourceType.MANUAL_ENTRY,
            external_id=database.id,
            external_url=database.url,
            source_title=f"Notion Database: {database.get_title()}",
            source_date=database.created_time,
            raw_content=self._database_to_text(database, pages),
        )

        # Build context
        context_parts = [f"Notion database: {database.get_title()}"]

        db_title_lower = database.get_title().lower()
        db_desc = database.get_description() or ""
        db_desc_lower = db_desc.lower()

        if any(keyword in db_title_lower or keyword in db_desc_lower
               for keyword in ["feature", "roadmap", "spec"]):
            context_parts.append("Extract features and use cases")
        elif any(keyword in db_title_lower or keyword in db_desc_lower
                 for keyword in ["feedback", "customer", "user"]):
            context_parts.append("Extract pain points and quotes")
        elif any(keyword in db_title_lower or keyword in db_desc_lower
                 for keyword in ["competitor", "market"]):
            context_parts.append("Extract competitors and market insights")

        additional_context = " | ".join(context_parts)

        # Extract knowledge using LLM
        extraction_result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        return source, extraction_result.entries

    def _page_to_text(self, page: NotionPage, blocks: list[NotionBlock]) -> str:
        """Convert page and blocks to plain text.

        Args:
            page: Notion page
            blocks: Page blocks

        Returns:
            Plain text representation
        """
        parts = [
            f"Page: {page.get_title()}",
            f"Created: {page.created_time.strftime('%Y-%m-%d')}",
            "",  # Empty line
        ]

        # Extract text from blocks
        for block in blocks:
            text = block.get_text_content()
            if text:
                # Add heading markers
                if block.type == "heading_1":
                    parts.append(f"\n# {text}")
                elif block.type == "heading_2":
                    parts.append(f"\n## {text}")
                elif block.type == "heading_3":
                    parts.append(f"\n### {text}")
                elif block.type == "bulleted_list_item":
                    parts.append(f"- {text}")
                elif block.type == "numbered_list_item":
                    parts.append(f"1. {text}")
                elif block.type == "to_do":
                    parts.append(f"- [ ] {text}")
                elif block.type == "quote":
                    parts.append(f"> {text}")
                elif block.type == "callout":
                    parts.append(f"💡 {text}")
                else:
                    parts.append(text)

        return "\n".join(parts)

    def _database_to_text(
        self,
        database: NotionDatabase,
        pages: list[NotionPage],
    ) -> str:
        """Convert database and pages to plain text.

        Args:
            database: Notion database
            pages: Database pages

        Returns:
            Plain text representation
        """
        parts = [
            f"Database: {database.get_title()}",
        ]

        if database.get_description():
            parts.append(f"Description: {database.get_description()}")

        parts.append(f"\nPages ({len(pages)}):")
        parts.append("")

        # List pages with titles
        for i, page in enumerate(pages, 1):
            title = page.get_title()
            parts.append(f"{i}. {title}")

            # Add some property values if available
            for prop_name, prop_value in page.properties.items():
                if isinstance(prop_value, dict):
                    prop_type = prop_value.get("type")

                    # Extract text from different property types
                    if prop_type == "rich_text":
                        text_array = prop_value.get("rich_text", [])
                        if text_array:
                            text = "".join(item.get("plain_text", "") for item in text_array)
                            if text:
                                parts.append(f"   {prop_name}: {text}")

                    elif prop_type == "select":
                        select_value = prop_value.get("select")
                        if select_value:
                            parts.append(f"   {prop_name}: {select_value.get('name', '')}")

                    elif prop_type == "multi_select":
                        multi_select = prop_value.get("multi_select", [])
                        if multi_select:
                            names = [item.get("name", "") for item in multi_select]
                            parts.append(f"   {prop_name}: {', '.join(names)}")

                    elif prop_type == "number":
                        number = prop_value.get("number")
                        if number is not None:
                            parts.append(f"   {prop_name}: {number}")

                    elif prop_type == "checkbox":
                        checkbox = prop_value.get("checkbox")
                        if checkbox is not None:
                            parts.append(f"   {prop_name}: {'✓' if checkbox else '✗'}")

        return "\n".join(parts)
