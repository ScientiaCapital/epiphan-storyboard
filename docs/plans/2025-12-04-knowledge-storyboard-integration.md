# Knowledge Brain + Storyboard Integration Design

**Date**: 2025-12-04
**Status**: Approved
**Author**: Claude + User

## Summary

Integrate the Knowledge Brain into storyboard generation so that approved/banned terms, pain points, features, and metrics from Close CRM calls are dynamically injected into storyboard prompts.

## Decision

- **Integration depth**: Medium (language guidelines + context enrichment)
- **Data strategy**: Preload on startup (fastest, requires restart for updates)
- **Architecture**: Singleton KnowledgeCache

## Architecture

### New Component: KnowledgeCache

**File**: `src/knowledge/cache.py`

A singleton that loads all knowledge from Supabase at app startup and provides fast in-memory access.

```python
class KnowledgeCache:
    _instance = None
    _loaded = False

    approved_terms: dict[str, list[str]]  # audience -> terms
    banned_terms: list[str]
    pain_points: dict[str, list[str]]     # audience -> pain points
    features: list[str]
    metrics: list[str]

    @classmethod
    def get(cls) -> "KnowledgeCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def load(self):
        """Load all knowledge from Supabase once."""
        # Query each knowledge type
        # Group by audience where applicable

    def get_language_guidelines(self, audience: str) -> dict:
        """Return merged approved/banned for this audience."""

    def get_context(self, audience: str) -> dict:
        """Return pain points + features for prompt enrichment."""
```

### Integration Points

**1. Startup Loading** (`src/api.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = KnowledgeCache.get()
    try:
        await cache.load()
        logger.info(f"Knowledge cache loaded: {cache.stats()}")
    except Exception as e:
        logger.warning(f"Knowledge cache failed to load: {e}")
    yield

app = FastAPI(lifespan=lifespan)
```

**2. Language Guidelines** (`src/tools/storyboard/gemini_client.py`)

Modify `_build_language_guidelines()` to merge static presets with dynamic knowledge:

```python
def _build_language_guidelines(self, icp_preset: dict, audience: str) -> str:
    # Get static defaults
    avoid = icp_preset.get("language_style", {}).get("avoid", [])
    use = icp_preset.get("language_style", {}).get("use", [])
    tone = icp_preset.get("tone", "Friendly and professional")

    # Merge with dynamic knowledge
    from src.knowledge.cache import KnowledgeCache
    cache = KnowledgeCache.get()
    knowledge = cache.get_language_guidelines(audience)

    avoid = list(set(knowledge["avoid"] + avoid))[:15]
    use = list(set(knowledge["use"] + use))[:15]

    return f"""LANGUAGE GUIDELINES:
- Tone: {tone}
- AVOID: {', '.join(avoid)}
- USE: {', '.join(use)}"""
```

**3. Context Enrichment** (`src/tools/storyboard/gemini_client.py`)

Add new method and inject into understand prompts:

```python
def _build_knowledge_context(self, audience: str) -> str:
    from src.knowledge.cache import KnowledgeCache
    cache = KnowledgeCache.get()
    ctx = cache.get_context(audience)

    sections = []
    if ctx["pain_points"]:
        sections.append(f"CUSTOMER PAIN POINTS: {'; '.join(ctx['pain_points'])}")
    if ctx["features"]:
        sections.append(f"PRODUCT FEATURES: {', '.join(ctx['features'])}")
    if ctx["metrics"]:
        sections.append(f"PROOF POINTS: {'; '.join(ctx['metrics'])}")

    return "\n".join(sections)
```

## Data Flow

```
APP STARTUP
    ↓
KnowledgeCache.load() queries Supabase coperniq_knowledge table
    ↓
Groups by knowledge_type and audience, stores in memory
    ↓
STORYBOARD REQUEST (audience="c_suite")
    ↓
GeminiStoryboardClient.understand_*()
    ↓
_build_language_guidelines() merges static + dynamic
_build_knowledge_context() adds pain points, features, metrics
    ↓
Prompt includes real customer context
    ↓
LLM generates more specific, targeted understanding
```

## Graceful Degradation

If Supabase is unavailable or knowledge table is empty:
- Cache loads with empty data
- Storyboards still work using `coperniq_presets.py` defaults
- Knowledge enrichment is additive, not required

## Files to Modify

| File | Action |
|------|--------|
| `src/knowledge/cache.py` | CREATE - Singleton cache |
| `src/knowledge/__init__.py` | UPDATE - Export KnowledgeCache |
| `src/tools/storyboard/gemini_client.py` | UPDATE - Add 2 methods, modify 4 understand methods |
| `src/api.py` | UPDATE - Add lifespan startup |
| `tests/knowledge/test_cache.py` | CREATE - Unit tests |

## Success Criteria

1. Storyboard prompts include dynamic approved/banned terms from DB
2. Storyboard prompts include pain points, features, metrics from DB
3. App starts successfully even if knowledge table is empty
4. Tests verify cache loading and prompt injection
