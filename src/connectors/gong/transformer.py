"""Transform Gong data to KnowledgeEntry objects."""

import logging

from src.connectors.gong.schemas import GongCall, GongTranscript
from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class GongTransformer:
    """
    Transforms Gong calls and transcripts into KnowledgeSource and KnowledgeEntry objects.

    Uses DeepSeek V3 via KnowledgeExtractor to extract:
    - pain_point: Customer frustrations
    - metric: Numbers/stats mentioned
    - quote: Verbatim customer quotes
    - objection: Sales objections
    - competitor: Competitor mentions
    - success_story: Customer wins
    """

    def __init__(self, extractor: KnowledgeExtractor | None = None):
        """
        Initialize transformer.

        Args:
            extractor: Optional KnowledgeExtractor (creates default if not provided)
        """
        self.extractor = extractor or KnowledgeExtractor()

    def call_to_source(
        self,
        call: GongCall,
        transcript: GongTranscript,
    ) -> KnowledgeSource:
        """
        Convert Gong call + transcript to KnowledgeSource.

        Args:
            call: GongCall metadata
            transcript: GongTranscript content

        Returns:
            KnowledgeSource ready for ingestion
        """
        # Build speaker map for readable names
        speaker_map = {}
        for party in call.parties:
            if party.id:
                speaker_map[party.id] = party.name or party.email or party.id

        # Convert transcript to text
        transcript_text = transcript.to_text(speaker_map=speaker_map)

        # Extract participant names
        participant_names = [
            party.name or party.email or "Unknown"
            for party in call.parties
            if party.name or party.email
        ]

        # Create source
        import hashlib

        content_hash = hashlib.sha256(transcript_text[:1000].encode()).hexdigest()

        source = KnowledgeSource(
            source_type=SourceType.GONG_TRANSCRIPT,
            external_id=call.id,
            external_url=call.url,
            source_title=call.title or f"Gong Call {call.id}",
            source_date=call.started,
            duration_seconds=call.duration,
            participant_names=participant_names,
            raw_content=transcript_text,
            content_hash=content_hash,
        )

        return source

    async def extract_knowledge(
        self,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """
        Extract knowledge from Gong source using LLM.

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
        context_parts.append("Context: Sales call transcript from Gong")

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
            f"Extracted {result.items_extracted} items from Gong call {source.external_id}"
        )
        return result.entries
