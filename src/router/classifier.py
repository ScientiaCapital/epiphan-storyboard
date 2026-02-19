"""TaskClassifier - 3-stage task classification for agent routing.

Classification Algorithm:
1. Pattern Matching (instant, 0.95 confidence) - regex for exact phrases
2. Keyword Scoring (fast, 0.7-0.9 confidence) - weighted keyword matching
3. LLM Fallback (for ambiguous cases <0.7 confidence) - uses DeepSeek V3

NO OpenAI models - uses DeepSeek/Qwen/Gemini per project rules.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from src.router.schemas import (
    ClassificationRequest,
    ClassificationResult,
    TaskType,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Stage 1: Pattern Matching Rules (instant, high confidence)
# ============================================================================

PATTERN_RULES: dict[TaskType, list[str]] = {
    TaskType.STORYBOARD: [
        r"\bstoryboard\b",
        r"generate\s+(?:a\s+)?visualization",
        r"create\s+(?:a\s+)?presentation",
        r"executive\s+summary\s+image",
        r"code\s+to\s+(?:image|png|visual)",
        r"infographic\s+(?:from|for)",
    ],
    TaskType.VIDEO: [
        r"video\s+generation",
        r"create\s+(?:a\s+)?video",
        r"generate\s+(?:a\s+)?video",
        r"edit\s+video",
        r"\brunway\b",
        r"screen\s+recording",
        r"record\s+(?:the\s+)?screen",
    ],
    TaskType.SCRAPE: [
        r"scrape\s+(?:the\s+)?(?:website|data|page|url)",
        r"fetch\s+(?:from\s+)?(?:url|http)",
        r"web\s+scraping",
        r"crawl\s+(?:the\s+)?(?:website|data|page)",
        r"extract\s+(?:data\s+)?from\s+(?:the\s+)?(?:web|page|url)",
        r"https?://\S+",  # URL pattern
    ],
    TaskType.CODE_RUN: [
        r"run\s+(?:this\s+)?(?:python|javascript|code)",
        r"execute\s+(?:this\s+)?(?:python|javascript|code)",
        r"sandbox\s+execution",
        r"(?:python|javascript|node)\s+(?:script|code)",
    ],
    TaskType.KNOWLEDGE: [
        r"knowledge\s+base",
        r"search\s+(?:the\s+)?(?:crm|knowledge)",
        r"extract\s+from\s+(?:the\s+)?crm",
        r"customer\s+(?:data|info|information)",
        r"close\s+crm",
    ],
    TaskType.SQL: [
        r"sql\s+query",
        r"database\s+query",
        r"run\s+(?:a\s+)?query",
        r"select\s+\*?\s*from",
        r"supabase\s+query",
        r"insert\s+into",
        r"update\s+\w+\s+set",
    ],
}

# ============================================================================
# Stage 2: Keyword Scoring Weights
# ============================================================================

KEYWORD_WEIGHTS: dict[TaskType, dict[str, float]] = {
    TaskType.STORYBOARD: {
        "storyboard": 1.0,
        "visualization": 0.8,
        "infographic": 0.9,
        "presentation": 0.7,
        "diagram": 0.6,
        "miro": 0.8,
        "screenshot": 0.5,
        "visual": 0.6,
        "png": 0.5,
        "image": 0.4,
    },
    TaskType.VIDEO: {
        "video": 1.0,
        "runway": 0.9,
        "recording": 0.8,
        "screen capture": 0.8,
        "animation": 0.7,
        "clip": 0.6,
        "footage": 0.7,
        "mp4": 0.6,
    },
    TaskType.SCRAPE: {
        "scrape": 1.0,
        "crawl": 0.9,
        "fetch": 0.8,
        "extract": 0.7,
        "website": 0.6,
        "url": 0.6,
        "http": 0.5,
        "html": 0.5,
        "webpage": 0.7,
    },
    TaskType.CODE_RUN: {
        "run code": 1.0,
        "execute": 0.9,
        "python": 0.7,
        "javascript": 0.7,
        "sandbox": 0.8,
        "script": 0.6,
        "node": 0.6,
        "eval": 0.7,
    },
    TaskType.KNOWLEDGE: {
        "knowledge base": 1.0,
        "crm": 0.9,
        "close": 0.5,
        "customer": 0.6,
        "loom": 0.7,
        "transcript": 0.6,
        "search": 0.4,
        "find info": 0.6,
    },
    TaskType.SQL: {
        "sql": 1.0,
        "database": 0.9,
        "query": 0.7,
        "select": 0.6,
        "supabase": 0.9,
        "postgres": 0.8,
        "table": 0.5,
        "rows": 0.5,
    },
}

# ============================================================================
# Task Type to Model Mapping (integrates with model_catalog)
# ============================================================================

TASK_TYPE_MODEL_MAP: dict[TaskType, dict[str, Any]] = {
    TaskType.STORYBOARD: {
        "task": "vision",
        "require_vision": True,
        "model": "gemini-1.5-flash",  # Default for storyboard
    },
    TaskType.VIDEO: {
        "task": "agents",
        "model": "deepseek/deepseek-chat-v3",
    },
    TaskType.SCRAPE: {
        "task": "tool-use",
        "model": "deepseek/deepseek-chat-v3",
    },
    TaskType.CODE_RUN: {
        "task": "coding",
        "model": "qwen/qwen-2.5-coder-32b-instruct",
    },
    TaskType.KNOWLEDGE: {
        "task": "agents",
        "model": "deepseek/deepseek-chat-v3",
    },
    TaskType.SQL: {
        "task": "coding",
        "model": "qwen/qwen-2.5-coder-32b-instruct",
    },
}

# LLM classification prompt
LLM_CLASSIFICATION_PROMPT = """You are a task classification expert for an AI agent system.

Classify the user's request into ONE of these categories:
- storyboard: Generate storyboards, visualizations, infographics from code/images
- video: Video generation, editing, screen recording
- scrape: Web scraping, URL fetching, data extraction from websites
- code_run: Execute Python/JavaScript code in sandbox
- knowledge: Search knowledge base, CRM queries, customer data
- sql: Database queries, SQL execution, Supabase queries

Analyze the request and respond with JSON only:
{
  "task_type": "<category>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}

If the task doesn't fit any category well, choose "knowledge" as default.
"""


class TaskClassifier:
    """3-stage task classifier for agent routing.

    Classification stages:
    1. Pattern Matching - regex patterns for exact phrases (0.95 confidence)
    2. Keyword Scoring - weighted keyword matching (0.7-0.9 confidence)
    3. LLM Fallback - DeepSeek V3 for ambiguous cases (<0.7 confidence)

    NO OpenAI models are used per project rules.
    """

    def __init__(
        self,
        llm_client: Any = None,
        enable_llm_fallback: bool = True,
        confidence_threshold: float = 0.7,
    ):
        """Initialize classifier.

        Args:
            llm_client: Optional async LLM client for testing (mock injection)
            enable_llm_fallback: Whether to use LLM for low-confidence cases
            confidence_threshold: Minimum confidence to skip LLM (0.0-1.0)
        """
        self._llm_client = llm_client
        self._enable_llm_fallback = enable_llm_fallback
        self._confidence_threshold = confidence_threshold
        self._http_client: httpx.AsyncClient | None = None

        # LLM model for classification (NO OpenAI)
        self.model = os.getenv("CLASSIFIER_LLM_MODEL", "deepseek/deepseek-chat-v3")

    async def classify(self, request: ClassificationRequest) -> ClassificationResult:
        """Classify a task into a task type.

        Uses 3-stage classification:
        1. Pattern matching (instant, high confidence)
        2. Keyword scoring (fast, medium confidence)
        3. LLM fallback (for ambiguous cases)

        Args:
            request: Classification request with query and optional context

        Returns:
            ClassificationResult with task_type, confidence, and reasoning
        """
        query = request.query.lower().strip()
        context = (request.context or "").lower().strip()
        full_text = f"{query} {context}".strip()

        # Stage 1: Pattern Matching
        pattern_result = self._pattern_match(full_text)
        if pattern_result:
            task_type, confidence, reasoning = pattern_result
            return ClassificationResult(
                task_type=task_type,
                confidence=confidence,
                reasoning=reasoning,
                extracted_params=self._extract_params(full_text, task_type),
                recommended_model=self._get_model_recommendation(task_type),
            )

        # Stage 2: Keyword Scoring
        scores = self._keyword_score(full_text)
        if scores:
            best_type = max(scores, key=lambda t: scores[t])
            best_score = scores[best_type]

            if best_score >= self._confidence_threshold:
                return ClassificationResult(
                    task_type=best_type,
                    confidence=best_score,
                    reasoning=f"Keyword scoring: matched keywords for {best_type.value}",
                    extracted_params=self._extract_params(full_text, best_type),
                    recommended_model=self._get_model_recommendation(best_type),
                )

        # Stage 3: LLM Fallback
        if self._enable_llm_fallback:
            try:
                llm_result = await self._llm_classify(query, request.context)
                return llm_result
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")

        # Fallback to KNOWLEDGE with low confidence
        return ClassificationResult(
            task_type=TaskType.KNOWLEDGE,
            confidence=0.4,
            reasoning="Fallback: No strong pattern or keyword match, defaulting to knowledge",
            extracted_params={},
            recommended_model=self._get_model_recommendation(TaskType.KNOWLEDGE),
        )

    def _pattern_match(self, text: str) -> tuple[TaskType, float, str] | None:
        """Stage 1: Fast pattern matching using regex.

        Returns:
            (task_type, confidence, reasoning) or None if no match
        """
        for task_type, patterns in PATTERN_RULES.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return (
                        task_type,
                        0.95,
                        f"Pattern match: '{pattern}' matched for {task_type.value}",
                    )
        return None

    def _keyword_score(self, text: str) -> dict[TaskType, float]:
        """Stage 2: Score each task type based on keyword presence.

        Returns:
            Dict mapping TaskType to normalized score (0.0-1.0)
        """
        scores: dict[TaskType, float] = {}

        for task_type, keywords in KEYWORD_WEIGHTS.items():
            total_score = 0.0
            max_possible = sum(keywords.values())

            for keyword, weight in keywords.items():
                if keyword.lower() in text:
                    total_score += weight

            if max_possible > 0:
                # Normalize to 0.7-0.9 range (keyword matches aren't as confident as patterns)
                normalized = (total_score / max_possible) * 0.2 + 0.7
                if total_score > 0:
                    scores[task_type] = min(normalized, 0.9)

        return scores

    async def _llm_classify(
        self, query: str, context: str | None
    ) -> ClassificationResult:
        """Stage 3: Use LLM for classification (fallback for ambiguous cases).

        Uses DeepSeek V3 (cheapest, fast: $0.20/$0.80 per 1M tokens).
        """
        # Use injected mock client for testing
        if self._llm_client is not None:
            try:
                response = await self._llm_client(query)
                return ClassificationResult(
                    task_type=TaskType(response["task_type"]),
                    confidence=response["confidence"],
                    reasoning=f"LLM classification: {response['reasoning']}",
                    extracted_params={},
                    recommended_model=self._get_model_recommendation(
                        TaskType(response["task_type"])
                    ),
                )
            except Exception as e:
                raise ValueError(f"LLM classification failed: {e}") from e

        # Real LLM call via OpenRouter
        user_message = f"Request: {query}"
        if context:
            user_message += f"\n\nContext: {context}"

        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self._http_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": LLM_CLASSIFICATION_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,  # Low temp for consistent classification
                    "max_tokens": 256,
                },
                headers={
                    "Authorization": f"Bearer {(os.getenv('OPENROUTER_API_KEY') or '').strip()}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON response (handle markdown code blocks)
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            parsed = json.loads(content)
            task_type = TaskType(parsed["task_type"])

            return ClassificationResult(
                task_type=task_type,
                confidence=parsed["confidence"],
                reasoning=f"LLM classification: {parsed['reasoning']}",
                extracted_params={},
                recommended_model=self._get_model_recommendation(task_type),
            )

        except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"LLM classification failed: {e}")
            raise

    def _get_model_recommendation(self, task_type: TaskType) -> str:
        """Get recommended model for the task type.

        Integrates with model_catalog patterns.
        """
        try:
            from src.model_catalog import select_model

            mapping = TASK_TYPE_MODEL_MAP.get(task_type, {})
            return select_model(
                task=mapping.get("task", "agents"),
                require_vision=mapping.get("require_vision", False),
            )
        except ImportError:
            # Fallback if model_catalog not available
            mapping = TASK_TYPE_MODEL_MAP.get(task_type, {})
            model = mapping.get("model", "deepseek/deepseek-chat-v3")
            return str(model) if model else "deepseek/deepseek-chat-v3"

    def _extract_params(self, text: str, task_type: TaskType) -> dict[str, Any]:
        """Extract relevant parameters from the query.

        Returns:
            Dict of extracted parameters based on task type
        """
        params: dict[str, Any] = {}

        # Extract URLs for scrape tasks
        if task_type == TaskType.SCRAPE:
            urls = re.findall(r"https?://\S+", text)
            if urls:
                params["urls"] = urls

        # Extract language for code_run tasks
        if task_type == TaskType.CODE_RUN:
            if "python" in text.lower():
                params["language"] = "python"
            elif "javascript" in text.lower() or "node" in text.lower():
                params["language"] = "javascript"

        return params

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
