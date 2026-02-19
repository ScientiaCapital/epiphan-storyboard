"""
Knowledge Extraction using LLMs.

Extracts structured knowledge (pain points, metrics, features, etc.)
from raw content (transcripts, code, notes).
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Optional

import httpx

from src.knowledge.base import (
    ExtractionResult,
    KnowledgeEntry,
    KnowledgeSource,
    KnowledgeType,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractorConfig:
    """Configuration for knowledge extraction."""

    # Model selection (DeepSeek V3.2 for text extraction)
    openrouter_api_key: str = ""
    model: str = "deepseek/deepseek-chat-v3"

    # Extraction settings
    temperature: float = 0.6  # Higher for creative extraction
    max_tokens: int = 4096

    def __post_init__(self):
        if not self.openrouter_api_key:
            self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")


EXTRACTION_PROMPT = """Extract reusable knowledge from this content.

CONTENT:
---
{content}
---

CONTEXT: {context}

FIND AND EXTRACT:
- Pain points (frustrations - preserve exact words)
- Metrics (numbers: dollars, hours, percentages, counts)
- Quotes (verbatim statements worth reusing)
- Features/capabilities mentioned
- Language that resonates (approved terms)
- Objections or concerns raised
- Competitors mentioned
- Use cases discussed

For each finding, note:
- Type (pain_point, metric, quote, feature, approved_term, objection, competitor, use_case)
- Content (verbatim when applicable)
- Confidence (0.0-1.0)
- Speaker/company if known
- Relevant audience if obvious

Return JSON:
{{
    "extractions": [
        {{
            "knowledge_type": "pain_point|metric|quote|feature|approved_term|objection|competitor|use_case",
            "content": "Extracted knowledge",
            "context": "Surrounding context",
            "verbatim": true/false,
            "confidence_score": 0.0-1.0,
            "speaker_name": "Name if known",
            "speaker_role": "Role if known",
            "company_name": "Company if known",
            "audience": [],
            "industries": [],
            "product_areas": []
        }}
    ],
    "summary": "Brief summary"
}}"""


class KnowledgeExtractor:
    """
    Extracts knowledge from raw content using LLMs.
    """

    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or ExtractorConfig()

    async def extract(
        self,
        source: KnowledgeSource,
        content: Optional[str] = None,
        additional_context: str = "",
    ) -> ExtractionResult:
        """
        Extract knowledge from a source.

        Args:
            source: The knowledge source metadata
            content: Content to extract from (uses source.raw_content if not provided)
            additional_context: Additional context to help extraction

        Returns:
            ExtractionResult with extracted entries
        """
        start_time = perf_counter()

        content = content or source.raw_content
        if not content:
            return ExtractionResult(
                source_id=source.id,
                error="No content to extract from",
                execution_time_ms=0,
            )

        # Build context string
        context_parts = []
        if source.source_title:
            context_parts.append(f"Source: {source.source_title}")
        if source.source_type:
            context_parts.append(f"Type: {source.source_type.value}")
        if source.participant_names:
            context_parts.append(f"Participants: {', '.join(source.participant_names)}")
        if additional_context:
            context_parts.append(additional_context)
        context_str = " | ".join(context_parts) if context_parts else "No additional context"

        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            content=content[:15000],  # Limit content length
            context=context_str,
        )

        try:
            # Call LLM via OpenRouter
            response = await self._call_llm(prompt)

            # Parse response
            entries = self._parse_extraction_response(response, source)

            execution_time_ms = int((perf_counter() - start_time) * 1000)

            return ExtractionResult(
                source_id=source.id,
                items_extracted=len(entries),
                entries=entries,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.exception(f"Extraction failed: {e}")
            return ExtractionResult(
                source_id=source.id,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM via OpenRouter."""
        if not self.config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _parse_extraction_response(
        self,
        response: str,
        source: KnowledgeSource,
    ) -> list[KnowledgeEntry]:
        """Parse LLM response into KnowledgeEntry objects."""
        entries = []

        try:
            # Clean response (remove markdown if present)
            json_str = response.strip()
            if json_str.startswith("```"):
                parts = json_str.split("```")
                if len(parts) >= 2:
                    json_str = parts[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
                json_str = json_str.strip()

            # Repair truncated JSON
            json_str = self._repair_json(json_str)

            data = json.loads(json_str)
            extractions = data.get("extractions", [])

            for item in extractions:
                try:
                    knowledge_type_str = item.get("knowledge_type", "").lower()

                    # Map to enum
                    type_map = {
                        "pain_point": KnowledgeType.PAIN_POINT,
                        "metric": KnowledgeType.METRIC,
                        "quote": KnowledgeType.QUOTE,
                        "feature": KnowledgeType.FEATURE,
                        "approved_term": KnowledgeType.APPROVED_TERM,
                        "objection": KnowledgeType.OBJECTION,
                        "competitor": KnowledgeType.COMPETITOR,
                        "use_case": KnowledgeType.USE_CASE,
                        "success_story": KnowledgeType.SUCCESS_STORY,
                    }

                    knowledge_type = type_map.get(knowledge_type_str)
                    if not knowledge_type:
                        logger.warning(f"Unknown knowledge type: {knowledge_type_str}")
                        continue

                    content = item.get("content", "").strip()
                    if not content:
                        continue

                    entry = KnowledgeEntry(
                        knowledge_type=knowledge_type,
                        content=content,
                        context=item.get("context"),
                        verbatim=item.get("verbatim", False),
                        confidence_score=float(item.get("confidence_score", 0.8)),
                        speaker_name=item.get("speaker_name"),
                        speaker_role=item.get("speaker_role"),
                        company_name=item.get("company_name"),
                        audience=item.get("audience", []),
                        industries=item.get("industries", []),
                        product_areas=item.get("product_areas", []),
                        source_id=source.id,
                    )
                    entries.append(entry)

                except Exception as e:
                    logger.warning(f"Failed to parse extraction item: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction JSON: {e}")
            logger.debug(f"Raw response: {response[:500]}")

        return entries

    def _repair_json(self, json_str: str) -> str:
        """Attempt to repair truncated or malformed JSON."""
        # Fix unterminated strings
        quote_count = json_str.count('"') - json_str.count('\\"')
        if quote_count % 2 == 1:
            json_str = json_str + '"'

        # Add missing closing brackets
        open_brackets = json_str.count('[') - json_str.count(']')
        if open_brackets > 0:
            json_str = json_str + ']' * open_brackets

        # Add missing closing braces
        open_braces = json_str.count('{') - json_str.count('}')
        if open_braces > 0:
            json_str = json_str + '}' * open_braces

        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        return json_str
