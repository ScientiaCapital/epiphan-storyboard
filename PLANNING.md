# PLANNING.md - Epiphan Storyboard Architecture

**Project**: epiphan-storyboard
**Type**: Multi-provider LLM agent orchestration with ReAct pattern
**Status**: Phase 12.5 Complete (Storyboard Hardening)
**Version**: 0.12.5
**Last Updated**: 2026-02-19

---

## Project Overview

**epiphan-storyboard** is a Python-based agentic AI orchestration platform that runs multi-step ReAct loops using multiple LLM providers (Anthropic Claude, Google Gemini, DeepSeek, Qwen, Moonshot via OpenRouter). It provides:

1. **SDK for plugin developers** - 5 imports only (BaseTool, ToolCategory, ToolDefinition, ToolResult, PluginRegistry)
2. **Tool registry system** - Auto-discover plugins from `plugins/` directory
3. **ReAct agent runner** - Multi-step reasoning with tool execution
4. **Audit/observability layer** - Track all tool executions in Supabase
5. **HTTP API** - FastAPI endpoints for agent execution

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        EPIPHAN STORYBOARD                               │
│                                                                    │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  HTTP Client   │  │  AgentRunner    │  │  AuditLogger     │  │
│  │  (SDK)         │──│  (ReAct Loop)   │──│  @audit_logged   │  │
│  │  StoryboardCli  │  │  StateManager   │  │  decorator       │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
│         │                     │                      │            │
│         │                     ▼                      │            │
│         │            ┌─────────────────┐             │            │
│         │            │  ToolRegistry   │◄────────────┤            │
│         │            │  (Global)       │             │            │
│         │            └─────────────────┘             │            │
│         │                     │                      │            │
│         │         ┌───────────┴───────────┐          │            │
│         │         ▼                       ▼          │            │
│         │  ┌──────────────┐      ┌──────────────┐   │            │
│         │  │ Core Tools   │      │   Plugins    │   │            │
│         │  │ - web_fetch  │      │ - scraper    │   │            │
│         │  │ - code_run   │      │ - sales      │   │            │
│         │  │ - sql_query  │      │ - custom     │   │            │
│         │  └──────────────┘      └──────────────┘   │            │
│         │                                            │            │
│         ▼                                            ▼            │
│  ┌──────────────┐                           ┌───────────────┐    │
│  │  FastAPI     │                           │  Supabase     │    │
│  │  Endpoints   │                           │  - audit_logs │    │
│  │  /agents/run │                           │  - tool_exec  │    │
│  │  /tools      │                           │  - leads      │    │
│  └──────────────┘                           └───────────────┘    │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │  Redis       │                                                │
│  │  (State)     │                                                │
│  └──────────────┘                                                │
└──────────────────────────────────────────────────────────────────┘

External LLM Providers:
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ DeepSeek   │  │ Qwen       │  │ Claude     │  │ Gemini     │
│ (OpenRouter)  (OpenRouter)  │ (Anthropic) │  │ (Google)   │
└────────────┘  └────────────┘  └────────────┘  └────────────┘
```

---

## Core Components

### 1. SDK (`src/sdk/`)

**Purpose**: Public API for plugin developers

**Exports**:
```python
from epiphan_storyboard.sdk import (
    BaseTool,           # Base class for all tools
    ToolCategory,       # Enum: DATA, COMMUNICATION, CODE, etc.
    ToolDefinition,     # Tool metadata (name, description, parameters)
    ToolResult,         # Tool execution result
    PluginRegistry,     # Register tools in plugins
)
```

**Design Philosophy**:
- **5 imports only** - Minimize cognitive load for plugin developers
- **Zero platform internals** - Plugins don't depend on core implementation
- **Type-safe** - Pydantic v2 models for all data
- **Async-first** - All tool.run() methods are async

**Example Plugin**:
```python
from epiphan_storyboard.sdk import BaseTool, ToolDefinition, ToolResult, PluginRegistry

registry = PluginRegistry()

@registry.tool
class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="Does something useful",
            category=ToolCategory.DATA,
            parameters={"type": "object", "properties": {...}},
        )

    async def run(self, arguments: dict) -> ToolResult:
        # Implementation
        return ToolResult(
            tool_name="my_tool",
            success=True,
            result={"data": "..."},
            execution_time_ms=100,
        )

def register(global_registry):
    """Called by PluginLoader."""
    for tool in registry.tools:
        global_registry.register(tool)
```

---

### 2. Tool System (`src/tools/`)

**Purpose**: Core tools and registry management

**Components**:
- `base.py` - BaseTool, ToolDefinition, ToolResult classes
- `registry.py` - Global ToolRegistry singleton
- `web_fetch.py` - HTTP requests with SSRF protection
- `code_run.py` - Docker-sandboxed Python/Node.js execution
- `sql_query.py` - Supabase PostgreSQL queries

**Registry Pattern**:
```python
from src.tools.registry import ToolRegistry

# Global singleton
registry = ToolRegistry()

# Register core tools
registry.register(WebFetchTool())
registry.register(CodeRunTool())

# Auto-discover plugins
PluginLoader.discover_and_register(registry, plugins_dir="plugins/")

# Get tool by name
tool = registry.get_tool("web_fetch")
result = await tool.run({"url": "https://example.com"})
```

---

### 3. Agent System (`src/agents/`)

**Purpose**: ReAct loop execution and state management

**Components**:
- `schemas.py` - AgentSession, AgentStep, Message schemas
- `state.py` - StateManager (Redis + Supabase)
- `runner.py` - AgentRunner (ReAct loop executor)

**ReAct Loop**:
```python
from src.agents.runner import AgentRunner

runner = AgentRunner(
    model="deepseek/deepseek-chat-v3",
    tools=["web_fetch", "sql_query"],
)

session = await runner.start_session(
    messages=[{"role": "user", "content": "Find Tesla dealers in California"}],
    org_id="my-org",
)

# Loop until completion
while session.status == "running":
    step = await runner.execute_step(session.session_id)
    if step.type == "tool_call":
        # Tool executed automatically
        pass
    elif step.type == "final_answer":
        print(step.content)
        break
```

**State Management**:
- **Redis** - Hot state (1hr TTL) for active sessions
- **Supabase** - Cold persistence for audit trail
- **Automatic failover** - If Redis unavailable, use Supabase only

---

### 4. Observability (`src/observability/`)

**Purpose**: Audit logging and tool execution tracking

**Components**:
- `audit.py` - AuditRecord, AuditLogger classes
- `decorators.py` - @audit_logged decorator

**Usage**:
```python
from src.observability import audit_logged

@audit_logged(category="data", tool_name="web_fetch")
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    response = await httpx.get(url)
    return response.json()

# Automatically logs to Supabase:
# - Input: {"url": "..."}
# - Output: {"data": {...}}
# - Execution time, success/failure, errors
```

**Database Schema** (`sql/001_audit_and_leads.sql`):
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    session_id TEXT,
    category TEXT,
    action TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name TEXT NOT NULL,
    input JSONB,
    output JSONB,
    execution_time_ms FLOAT,
    success BOOLEAN,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 5. Model Catalog (`src/model_catalog.py`)

**Purpose**: Smart model selection based on task requirements

**2025 Best-in-Class Models**:

| Model | Provider | Best For | Cost (per 1M tokens) |
|-------|----------|----------|---------------------|
| DeepSeek V3.1 | deepseek | Agents, coding, reasoning | $0.20 / $0.80 |
| DeepSeek R1 | deepseek | Deep reasoning, math | $3.00 / $7.00 |
| Qwen3-235B | alibaba | Hybrid thinking, multilingual | $0.30 / $1.20 |
| Kimi K2 | moonshot | Coding, tool-use | $0.15 / $0.60 |
| Claude Sonnet 4.5 | anthropic | Vision, analysis | $3.00 / $15.00 |

**Smart Selection**:
```python
from src.model_catalog import select_model

# Automatic task-based selection
model = select_model(task="coding")           # → qwen/qwen-2.5-coder-32b-instruct
model = select_model(task="reasoning")        # → deepseek/deepseek-r1
model = select_model(task="agents")           # → deepseek/deepseek-chat-v3
model = select_model(budget="budget")         # → deepseek/deepseek-r1-distill-qwen-8b
model = select_model(require_vision=True)     # → claude-sonnet-4-5-20250929
```

---

### 6. API (`src/api.py`)

**Purpose**: HTTP interface for agent execution

**Endpoints**:

```python
# FastAPI routes
POST /agents/run          # Start agent execution
GET  /agents/{id}         # Poll session status
POST /agents/{id}/cancel  # Cancel running session
GET  /tools               # List available tools
GET  /health              # Health check
```

**Example Usage**:
```python
from epiphan_storyboard.sdk import StoryboardClient

async with StoryboardClient("http://localhost:8000", org_id="my-org") as client:
    # Start agent
    session = await client.run_agent(
        messages=[{"role": "user", "content": "Scrape Tesla dealer locator"}],
        tools=["web_fetch", "my_tool"],
    )

    # Wait for completion
    result = await client.wait_for_completion(session.session_id)
    print(result.steps[-1]["final_answer"])
```

---

## Plugin Architecture

### Auto-Discovery

**Directory Structure**:
```
plugins/
├── example_plugin/
│   ├── __init__.py
│   ├── tools.py           # Tool implementations
│   └── register.py        # register(global_registry) function
├── scraper_tools/
│   ├── __init__.py
│   ├── dealer_locator.py
│   └── register.py
└── sales_tools/
    ├── __init__.py
    ├── outreach.py
    └── register.py
```

**Loading Process**:
1. `PluginLoader.discover_plugins("plugins/")` scans directory
2. For each plugin, imports `register.py`
3. Calls `register(global_registry)` to register tools
4. Tools are now available in ToolRegistry

---

## Data Flow

### End-to-End Example: Scraping Dealers

```
1. Client Request
   POST /agents/run
   {
     "messages": [{"role": "user", "content": "Scrape Tesla dealers in CA"}],
     "tools": ["web_fetch", "dealer_locator"]
   }

2. AgentRunner Initializes
   - Create session ID
   - Store in Redis + Supabase
   - Load tools from registry

3. ReAct Loop
   Step 1: LLM decides to use dealer_locator tool
   - AgentRunner.execute_step() → ToolRegistry.get_tool("dealer_locator")
   - DealerLocatorTool.run({"oem": "tesla", "state": "CA"})
   - AuditLogger logs execution to Supabase

   Step 2: LLM decides to use web_fetch tool
   - WebFetchTool.run({"url": "https://tesla.com/dealers?state=CA"})
   - Returns HTML

   Step 3: LLM extracts dealers from HTML
   - Code execution or text processing
   - Returns structured data

   Step 4: LLM provides final answer
   - "Found 25 Tesla dealers in California: [list]"

4. Response
   GET /agents/{session_id}
   {
     "status": "completed",
     "final_answer": "Found 25 Tesla dealers...",
     "steps": [...]
   }
```

---

## Technology Stack

### Core Framework
- **Python**: 3.13+ (type hints, match statements, async/await)
- **FastAPI**: Async HTTP framework
- **Pydantic**: v2 for data validation
- **Redis**: Session state storage (1hr TTL)
- **Supabase**: PostgreSQL for persistence

### LLM Providers
- **Anthropic Claude**: Via direct API
- **Google Gemini**: Via direct API
- **DeepSeek/Qwen/Kimi**: Via OpenRouter

### Testing & Quality
- **pytest**: Testing framework (1496 collected, 1478 passing)
- **pytest-asyncio**: Async test support
- **ruff**: Linting and formatting (replaces black + isort + flake8)
- **mypy**: Type checking
- **pytest-cov**: Coverage reporting (>90% target)

### Development Tools
- **Docker**: Code sandboxing (code_run tool)
- **docker-compose**: Redis + API services
- **aioresponses**: Mock HTTP responses in tests

---

## Security & Safety

### SSRF Protection (`src/sdk/security/ssrf.py`)
```python
from src.sdk.security import SSRFChecker

checker = SSRFChecker()
await checker.check_url("https://example.com")  # OK
await checker.check_url("http://localhost:22")  # Raises SSRFError
await checker.check_url("http://169.254.169.254")  # AWS metadata - blocked
```

**Blocked**:
- Private IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Localhost (127.0.0.1, ::1)
- Cloud metadata endpoints (169.254.169.254, fd00:ec2::254)

### Timeouts (`src/sdk/security/timeouts.py`)
```python
from src.sdk.security import with_timeout

@with_timeout(seconds=30)
async def long_running_operation():
    # Automatically cancelled after 30 seconds
    pass
```

### Approval System (`src/sdk/security/approval.py`)
```python
from src.sdk.security import require_approval

@require_approval(category="code_execution")
async def run_code(code: str):
    # Requires human approval before executing
    # Useful for destructive operations
    pass
```

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── sdk/                           # SDK tests (59 tests)
│   ├── test_base.py
│   ├── test_registry.py
│   ├── test_client.py
│   ├── test_security_ssrf.py
│   ├── test_security_timeout.py
│   └── test_security_approval.py
├── tools/                         # Tool tests
│   ├── test_web_fetch.py
│   ├── test_code_run.py
│   └── test_sql_query.py
├── agents/                        # Agent tests
│   ├── test_runner.py
│   ├── test_state.py
│   └── test_schemas.py
├── observability/                 # Audit tests
│   ├── test_audit_logger.py
│   └── test_decorators.py
└── integration/                   # Integration tests
    ├── test_plugin_loading.py
    └── test_end_to_end.py
```

### Coverage Requirements

**Minimum**: 90% for all new code
**Target**: 95%+ for SDK and core modules

```bash
# Run with coverage
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Deployment

### Local Development
```bash
# Start Redis
docker-compose up -d

# Run API server
uvicorn src.api:app --reload

# Run tests
pytest tests/ -v
```

### Production
```bash
# Build Docker image
docker build -t epiphan-storyboard:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables
```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
REDIS_URL=redis://localhost:6379
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Optional
GOOGLE_API_KEY=...              # For Gemini
APP_ENV=development
```

---

## Future Roadmap

### Phase 10 Options (User Decision Required)

**Option A: Real Data Ingestion Pipeline**
- [ ] Close CRM calls/notes ingestion (last 30 days)
- [ ] Loom transcript batch processing
- [ ] Miro roadmap screenshot analysis
- [ ] Test storyboard generation with real knowledge

**Option B: Advanced Features**
- [ ] Streaming responses (Server-Sent Events)
- [ ] Multi-agent collaboration
- [ ] Memory system (conversation history, RAG)
- [ ] Cost tracking per session

**Option C: Plugin Integrations (Tier 1)**
- [ ] dealer-scraper-mvp (fix 16 broken scrapers)
- [ ] sales-agent (LinkedIn scraping, lead enrichment)

### Phase 11: Production Hardening
- [ ] Horizontal scaling (multiple workers)
- [ ] Rate limiting per org
- [ ] Dashboard for monitoring
- [ ] Billing integration

---

## Completed Phases

| Phase | Description | Tests |
|-------|-------------|-------|
| 12.5 | Storyboard Hardening (brand colors, crash fixes, 45 safety tests) | 1496 |
| 12.0 | Auto Demo Video Pipeline (storyboard → scenes → video assets) | 1478 |
| 11.5 | Test Suite Repair (6 root causes, 0 source changes) | 1341 |
| 11.0 | Monetization Infrastructure (Stripe billing) | 114 |
| 10.0 | Agent Router (classifier + chains) | 41 |
| 9.0 | Screen Recording Module (Browserbase + Runway) | 100 |
| 8.0 | Mixed Input Parity (Text+Image) | 79 |
| 7.x | Knowledge Brain + Storyboard Integration | 260 |
| 6.0 | Demo App (CLI + Web UI) | 18 |
| 5.0 | Storyboard Pipeline API | 61 |
| 4.0 | Storyboard Tools | 202 |
| 3.0 | Video Tools Module | 186 |
| 2.0 | Plugin Integration | 28 |
| 1.0 | SDK Foundation | 59 |

**Total Tests**: 1496 collected (1478 passing, 22 skipped)

---

## Critical Rules

1. **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot, Claude, or Gemini
2. **API keys in .env only** - Never hardcode credentials
3. **Python 3.11+ features** - Use type hints, async/await, match statements
4. **Async-first design** - All I/O operations must be async
5. **>90% test coverage** - Non-negotiable for all new code
6. **SDK stability** - Never break the 5-import public API

---

**Last Updated**: 2026-02-19
**Version**: 0.12.5 (Phase 12.5 Complete)
