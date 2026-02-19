"""Transform HubSpot data to KnowledgeEntry objects."""

import hashlib
import logging
from datetime import datetime

from src.connectors.hubspot.schemas import HubSpotCall
from src.knowledge.base import KnowledgeEntry, KnowledgeSource, SourceType
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class HubSpotTransformer:
    """
    Transforms HubSpot calls into KnowledgeSource and KnowledgeEntry objects.

    HubSpot stores SalesMSG call transcripts in the hs_call_body property.
    Durations are stored in milliseconds (converted to seconds for KnowledgeSource).

    Uses KnowledgeExtractor to extract:
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

    def call_to_source(self, call: HubSpotCall) -> KnowledgeSource:
        """
        Convert HubSpot call to KnowledgeSource.

        Args:
            call: HubSpotCall object

        Returns:
            KnowledgeSource ready for ingestion
        """
        props = call.properties
        body = props.hs_call_body or ""

        # HubSpot stores duration in milliseconds - convert to seconds
        duration_seconds: int | None = None
        if props.hs_call_duration is not None:
            duration_seconds = props.hs_call_duration // 1000

        # Parse hs_timestamp for source_date
        source_date: datetime | None = None
        if props.hs_timestamp:
            try:
                source_date = datetime.fromisoformat(
                    props.hs_timestamp.replace("Z", "+00:00")
                )
            except Exception as e:
                logger.warning(f"[HUBSPOT] Failed to parse hs_timestamp: {e}")

        # Content hash for deduplication
        content_hash = hashlib.sha256(
            f"{call.id}:{body[:500]}".encode()
        ).hexdigest()

        return KnowledgeSource(
            source_type=SourceType.HUBSPOT_CALL,
            external_id=call.id,
            source_title=props.hs_call_title or f"HubSpot Call {call.id}",
            source_date=source_date,
            duration_seconds=duration_seconds,
            raw_content=body,
            content_hash=content_hash,
        )

    def call_to_transcript_request(
        self,
        call: HubSpotCall,
        contact_name: str | None = None,
        company_name: str | None = None,
    ) -> dict:
        """
        Build a dict ready for TranscriptToScenariosTool.run().

        Args:
            call: HubSpotCall object
            contact_name: Optional prospect contact name (from CRM associations)
            company_name: Optional prospect company name (from CRM associations)

        Returns:
            Dict with transcript, prospect_name, and prospect_company keys
        """
        body = call.properties.hs_call_body or ""

        return {
            "transcript": body,
            "prospect_name": contact_name,
            "prospect_company": company_name,
        }

    async def extract_knowledge(
        self,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """
        Extract knowledge from HubSpot source using LLM.

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
        context_parts.append("Context: Sales call transcript from HubSpot (SalesMSG)")

        additional_context = " | ".join(context_parts)

        # Extract using LLM
        result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        if result.error:
            logger.error(
                f"[HUBSPOT] Extraction failed for {source.external_id}: {result.error}"
            )
            return []

        logger.info(
            f"[HUBSPOT] Extracted {result.items_extracted} items from call {source.external_id}"
        )
        return result.entries
