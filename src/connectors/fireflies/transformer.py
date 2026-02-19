"""Transform Fireflies data to KnowledgeEntry objects."""

import logging

from src.connectors.fireflies.schemas import FirefliesTranscript
from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class FirefliesTransformer:
    """
    Transforms Fireflies transcripts into KnowledgeSource and KnowledgeEntry objects.

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

    def transcript_to_source(self, transcript: FirefliesTranscript) -> KnowledgeSource:
        """
        Convert Fireflies transcript to KnowledgeSource.

        Args:
            transcript: FirefliesTranscript

        Returns:
            KnowledgeSource ready for ingestion
        """
        # Convert to text
        transcript_text = transcript.to_text()

        # Create source
        import hashlib

        content_hash = hashlib.sha256(transcript_text[:1000].encode()).hexdigest()

        source = KnowledgeSource(
            source_type=SourceType.GONG_TRANSCRIPT,  # Reuse same type for now
            external_id=transcript.id,
            external_url=transcript.meeting_url or transcript.video_url,
            source_title=transcript.title or f"Fireflies Meeting {transcript.id}",
            source_date=transcript.date,
            duration_seconds=transcript.duration,
            participant_names=transcript.participants,
            raw_content=transcript_text,
            content_hash=content_hash,
        )

        return source

    async def extract_knowledge(
        self,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """
        Extract knowledge from Fireflies source using LLM.

        Args:
            source: KnowledgeSource with transcript text

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
        context_parts.append(
            "Context: Meeting transcript from Fireflies.ai with action items and keywords"
        )

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
            f"Extracted {result.items_extracted} items from Fireflies transcript {source.external_id}"
        )
        return result.entries
