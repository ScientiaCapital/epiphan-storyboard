"""Transform Clari Copilot data to KnowledgeEntry objects."""

import hashlib
import logging

from src.connectors.clari.schemas import ClariCallDetails
from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class ClariTransformer:
    """
    Transforms Clari Copilot calls into KnowledgeSource and KnowledgeEntry objects.

    Uses KnowledgeExtractor to extract:
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

    def call_to_source(self, call_details: ClariCallDetails) -> KnowledgeSource:
        """
        Convert Clari call details to KnowledgeSource.

        Args:
            call_details: ClariCallDetails with metadata and transcript

        Returns:
            KnowledgeSource ready for ingestion
        """
        transcript_text = call_details.transcript_to_text()

        # Extract participant names from participants list
        participant_names = [
            p.name or p.email or "Unknown"
            for p in call_details.call.participants
            if p.name or p.email
        ]

        # Content hash for deduplication — keyed by call ID + first 500 chars of transcript
        content_hash = hashlib.sha256(
            f"{call_details.call.id}:{transcript_text[:500]}".encode()
        ).hexdigest()

        return KnowledgeSource(
            source_type=SourceType.CLARI_CALL,
            external_id=call_details.call.id,
            source_title=call_details.call.title or f"Clari Call {call_details.call.id}",
            duration_seconds=call_details.call.duration,
            participant_names=participant_names,
            raw_content=transcript_text,
            content_hash=content_hash,
        )

    def call_to_transcript_request(self, call_details: ClariCallDetails) -> dict:
        """
        Build a dict suitable for TranscriptToScenariosTool.run().

        The first external participant (non-host) is used as prospect_name.

        Args:
            call_details: ClariCallDetails with metadata and transcript

        Returns:
            Dict with "transcript" and "prospect_name" keys
        """
        transcript_text = call_details.transcript_to_text()

        # Use the first non-host participant as prospect name, falling back to
        # any participant with a name or email, then empty string
        prospect_name = ""
        for p in call_details.call.participants:
            if p.role and p.role.lower() != "host":
                prospect_name = p.name or p.email or ""
                if prospect_name:
                    break

        # If we didn't find an external participant, use any named participant
        if not prospect_name:
            for p in call_details.call.participants:
                if p.name or p.email:
                    prospect_name = p.name or p.email or ""
                    break

        return {
            "transcript": transcript_text,
            "prospect_name": prospect_name,
        }

    async def extract_knowledge(
        self,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """
        Extract knowledge from Clari source using LLM.

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
        context_parts.append("Context: AE sales call transcript from Clari Copilot")

        additional_context = " | ".join(context_parts)

        # Extract using LLM
        result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        if result.error:
            logger.error(
                f"[CLARI] Extraction failed for {source.external_id}: {result.error}"
            )
            return []

        logger.info(
            f"[CLARI] Extracted {result.items_extracted} items from Clari call {source.external_id}"
        )
        return result.entries
