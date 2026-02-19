# Epiphan Storyboard Project Context
Last Updated: 2026-02-19

## Current Sprint: Plugin SDK & Project Integration

### Phase 1: SDK Foundation - COMPLETE
All Week 1 tasks finished:
- [x] SDK directory structure (`src/sdk/`)
- [x] Public API exports (BaseTool, ToolCategory, ToolDefinition, ToolResult)
- [x] PluginRegistry + PluginLoader for auto-discovery
- [x] StoryboardClient HTTP client
- [x] Security utilities (SSRF, timeout, approval gates)
- [x] Testing utilities (MockRegistry, ToolTestBase)
- [x] Example plugin template (`plugins/example_plugin/`)
- [x] pyproject.toml with SDK extras
- [x] 59 SDK tests passing

### Phase 2: dealer-scraper-mvp Integration - NEXT
Ready to start:
- [ ] Create `plugins/scraper_tools/` in dealer-scraper-mvp
- [ ] Implement DealerLocatorTool
- [ ] Implement ContractorEnrichTool
- [ ] Implement LicenseValidateTool
- [ ] Test agent fixing broken scrapers

## Architecture Overview

### SDK Public API (5 imports)
```python
from epiphan_storyboard.sdk import (
    BaseTool,           # Abstract base for custom tools
    ToolCategory,       # Enum: WEB, DATA, CODE, FILE, SYSTEM
    ToolDefinition,     # Pydantic model for tool metadata
    ToolResult,         # Pydantic model for execution results
    PluginRegistry,     # Isolated registry for plugin tools
)
```

### Plugin Pattern
```python
# External project creates tools
@registry.tool
class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="my_tool", ...)

    async def run(self, arguments: dict) -> ToolResult:
        ...

# Register with epiphan-storyboard
def register(global_registry):
    for tool in registry.tools:
        global_registry.register(tool)
```

### Model Catalog (Black Box Selection)
```python
from src.model_catalog import select_model

# Automatic best-model selection
model = select_model(task="coding")        # -> qwen/qwen-2.5-coder-32b-instruct
model = select_model(task="reasoning")     # -> deepseek/deepseek-r1
model = select_model(task="agents")        # -> deepseek/deepseek-chat-v3
model = select_model(budget="budget")      # -> deepseek/deepseek-r1-distill-qwen-8b
```

## Key Files

### SDK Files
| File | Purpose |
|------|---------|
| `src/sdk/__init__.py` | Public API exports |
| `src/sdk/registry.py` | PluginRegistry, PluginLoader |
| `src/sdk/client.py` | StoryboardClient HTTP client |
| `src/sdk/security/` | SSRF, timeout, approval utilities |
| `src/sdk/testing/` | MockRegistry, ToolTestBase |

### Core Files
| File | Purpose |
|------|---------|
| `src/tools/base.py` | BaseTool, ToolDefinition, ToolResult |
| `src/tools/registry.py` | Global ToolRegistry singleton |
| `src/model_catalog.py` | Model catalog + smart selector |
| `src/api.py` | FastAPI endpoints |
| `src/agents/` | AgentRunner, StateManager, schemas |

## Recent Changes (2026-02-19)
1. Full branding cleanup — all references updated to Epiphan Storyboard
2. Demo UI rebranded with Epiphan colors (navy #1D2B51 + green #8CBE3F)
3. Gemini client decomposed from 1801 → 940 lines
4. 8 real buyer personas aligned with BDR Playbook

## Environment
```bash
# Start services
docker-compose up -d

# Run tests
python3 -m pytest tests/ -v

# SDK tests only
python3 -m pytest tests/sdk/ -v
```

## Blockers
None currently.

## Next Steps
1. Begin dealer-scraper-mvp integration (Week 2)
2. Create DealerLocatorTool for OEM scraping
3. Test autonomous scraper fixing with agent
