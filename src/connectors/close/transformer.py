"""Transform Close CRM data to KnowledgeEntry objects."""

import hashlib
import logging
from datetime import datetime

from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class CloseTransformer:
    """
    Transforms Close CRM calls and notes into KnowledgeSource and KnowledgeEntry objects.

    Uses DeepSeek V3 via KnowledgeExtractor to extract:
    - pain_point: Customer frustrations
    - metric: Numbers/stats mentioned
    - quote: Verbatim customer quotes
    - objection: Sales objections
    - competitor: Competitor mentions
    - success_story: Customer wins
    - use_case: Specific use cases
    """

    def __init__(self, extractor: KnowledgeExtractor | None = None):
        """
        Initialize transformer.

        Args:
            extractor: Optional KnowledgeExtractor (creates default if not provided)
        """
        self.extractor = extractor or KnowledgeExtractor()

    def call_to_source(self, call: dict) -> KnowledgeSource:
        """
        Convert Close CRM call to KnowledgeSource.

        Args:
            call: Close CRM call dict

        Returns:
            KnowledgeSource ready for ingestion
        """
        # Extract transcript or note text
        transcript = call.get("note", "") or ""

        # Get participant info
        participants = []
        if call.get("user_name"):
            participants.append(call["user_name"])
        if call.get("contact_name"):
            participants.append(call["contact_name"])

        # Parse date
        source_date = None
        if call.get("date_created"):
            try:
                source_date = datetime.fromisoformat(
                    call["date_created"].replace("Z", "+00:00")
                )
            except Exception as e:
                logger.warning(f"Failed to parse date: {e}")

        # Create content hash for deduplication
        content_hash = hashlib.sha256(
            f"{call.get('id', '')}:{transcript[:500]}".encode()
        ).hexdigest()

        return KnowledgeSource(
            source_type=SourceType.CLOSE_CRM_CALL,
            external_id=call.get("id"),
            source_title=f"Call with {call.get('contact_name', 'Unknown')}",
            source_date=source_date,
            duration_seconds=call.get("duration"),
            participant_names=participants,
            raw_content=transcript,
            content_hash=content_hash,
        )

    def note_to_source(self, note: dict) -> KnowledgeSource:
        """
        Convert Close CRM note to KnowledgeSource.

        Args:
            note: Close CRM note dict

        Returns:
            KnowledgeSource ready for ingestion
        """
        content = note.get("note", "")

        # Get participant info
        participants = []
        if note.get("user_name"):
            participants.append(note["user_name"])
        if note.get("contact_name"):
            participants.append(note["contact_name"])

        # Parse date
        source_date = None
        if note.get("date_created"):
            try:
                source_date = datetime.fromisoformat(
                    note["date_created"].replace("Z", "+00:00")
                )
            except Exception as e:
                logger.warning(f"Failed to parse date: {e}")

        # Create content hash
        content_hash = hashlib.sha256(
            f"{note.get('id', '')}:{content[:500]}".encode()
        ).hexdigest()

        return KnowledgeSource(
            source_type=SourceType.CLOSE_CRM_NOTE,
            external_id=note.get("id"),
            source_title=f"Note: {content[:50]}...",
            source_date=source_date,
            participant_names=participants,
            raw_content=content,
            content_hash=content_hash,
        )

    async def extract_knowledge(
        self,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """
        Extract knowledge from Close CRM source using LLM.

        Args:
            source: KnowledgeSource with call/note text

        Returns:
            List of extracted KnowledgeEntry objects
        """
        # Build context for extraction
        context_parts = []
        if source.participant_names:
            context_parts.append(f"Participants: {', '.join(source.participant_names)}")
        if source.duration_seconds:
            minutes = source.duration_seconds // 60
            context_parts.append(f"Duration: {minutes} minutes")

        if source.source_type == SourceType.CLOSE_CRM_CALL:
            context_parts.append("Context: Sales call from Close CRM")
        else:
            context_parts.append("Context: Sales note from Close CRM")

        additional_context = " | ".join(context_parts)

        # Extract using LLM
        result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        if result.error:
            logger.error(f"Extraction failed for {source.external_id}: {result.error}")
            return []

        logger.info(
            f"Extracted {result.items_extracted} items from Close CRM {source.source_type.value} {source.external_id}"
        )
        return result.entries
