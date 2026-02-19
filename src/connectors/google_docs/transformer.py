"""Transform Google Docs data to KnowledgeEntry objects."""

import logging

from src.connectors.google_docs.schemas import GoogleDocument, GoogleDriveFile
from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class GoogleDocsTransformer:
    """Transform Google Docs documents into knowledge entries."""

    def __init__(self):
        self.extractor = KnowledgeExtractor()

    async def transform_document(
        self,
        document: GoogleDocument,
        drive_file: GoogleDriveFile,
        plain_text: str,
        org_id: str,
    ) -> tuple[KnowledgeSource, list[KnowledgeEntry]]:
        """Transform a Google Doc into knowledge entries.

        Documents can contain:
        - Product documentation -> features, use_cases, documentation
        - Feature specs/PRDs -> features, approved_terms
        - Meeting notes -> pain_points, quotes, metrics
        - Glossaries -> approved_terms
        - Customer feedback -> pain_points, use_cases

        Args:
            document: Google Docs document object
            drive_file: Drive file metadata
            plain_text: Extracted plain text
            org_id: Organization ID for source

        Returns:
            Tuple of (source, entries)
        """
        # Create knowledge source
        source = KnowledgeSource(
            source_type=SourceType.MANUAL_ENTRY,  # Use existing enum value
            external_id=document.document_id,
            external_url=drive_file.web_view_link,
            source_title=f"Google Doc: {document.title}",
            source_date=drive_file.modified_time,
            raw_content=plain_text,
        )

        # Build context for extraction
        context_parts = [f"Google Doc: {document.title}"]

        # Infer knowledge types from document title
        title_lower = document.title.lower()

        if any(
            keyword in title_lower
            for keyword in ["feature", "spec", "prd", "product requirements"]
        ):
            context_parts.append("Extract features, use cases, and approved terms")
        elif any(keyword in title_lower for keyword in ["meeting", "notes", "call", "minutes"]):
            context_parts.append("Extract pain points, quotes, and metrics")
        elif any(
            keyword in title_lower for keyword in ["glossary", "terminology", "definitions"]
        ):
            context_parts.append("Extract approved terms and definitions")
        elif any(
            keyword in title_lower
            for keyword in ["docs", "documentation", "guide", "how to", "tutorial"]
        ):
            context_parts.append("Extract features, use cases, and documentation content")
        elif any(
            keyword in title_lower for keyword in ["customer", "user", "feedback", "interview"]
        ):
            context_parts.append("Extract pain points, quotes, use cases, and success stories")
        elif any(
            keyword in title_lower for keyword in ["competitor", "competitive", "market"]
        ):
            context_parts.append("Extract competitor information and market insights")

        additional_context = " | ".join(context_parts)

        # Extract knowledge using LLM
        extraction_result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        return source, extraction_result.entries
