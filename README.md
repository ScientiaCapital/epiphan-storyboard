# Conductor-AI

> Commercial SaaS Platform for AI Agent Orchestration

A ReAct-pattern agent orchestration system with tool calling, async polling, and Docker sandboxing. Built with FastAPI, Claude 4.5, Redis, and Supabase.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/ScientiaCapital/conductor-ai.git
cd conductor-ai

# Switch to feature branch
git fetch origin feature/agent-system
git checkout feature/agent-system

# Or work in the worktree (already set up)
cd .worktrees/agent-system

# Install dependencies
pip install -r builder/requirements.txt
pip install -r test-requirements.txt

# Run tests
python -m pytest tests/ -v
```

## Project Status

**Phase 2: Agent Orchestration System** (In Progress)

| Task | Status | Tests | Description |
|------|--------|-------|-------------|
| 1. Agent Schemas | ✅ Complete | 44 | Pydantic v2 models |
| 2. Tool Base Classes | ✅ Complete | 32 | BaseTool, Registry |
| 3. web_fetch Tool | ✅ Complete | 38 | HTTP with SSRF protection |
| 4. code_run Tool | ✅ Complete | 37 | Docker sandbox |
| 5. sql_query Tool | ✅ Complete | 53 | Supabase SQL |
| 6. State Manager | 🔄 Next | - | Redis + Supabase |
| 7. AgentRunner | ⏳ Pending | - | ReAct loop |
| 8. API Endpoints | ⏳ Pending | - | FastAPI routes |
| 9. Integration Test | ⏳ Pending | - | E2E testing |

**Total Tests**: 204 passing

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
├─────────────────────────────────────────────────────────────┤
│  POST /v1/agents/run    → Start agent session               │
│  GET  /v1/agents/{id}   → Poll status/steps                 │
│  POST /v1/agents/{id}/cancel → Cancel session               │
│  GET  /v1/tools         → List available tools              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AgentRunner                             │
│  ReAct Loop: Thought → Action → Observation → Repeat        │
├─────────────────────────────────────────────────────────────┤
│  1. Build system prompt with tool definitions               │
│  2. Call Claude 4.5 with conversation history               │
│  3. Parse JSON response (thought/action/is_final)           │
│  4. If is_final: return final_answer                        │
│  5. If action: execute tool, add observation                │
│  6. Repeat until max_steps or completion                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   web_fetch     │  │   code_run      │  │   sql_query     │
│   HTTP Client   │  │  Docker Sandbox │  │  Supabase SQL   │
│   SSRF Protected│  │  128MB/50% CPU  │  │  Approval Req   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     State Manager                            │
├─────────────────────────────────────────────────────────────┤
│  Redis (Hot State)     │  Supabase (Cold Storage)           │
│  • Active sessions     │  • Completed sessions              │
│  • 1 hour TTL          │  • Permanent persistence           │
│  • Fast polling        │  • Analytics/history               │
└─────────────────────────────────────────────────────────────┘
```

## Tools

### web_fetch
HTTP GET/POST with comprehensive security:
- SSRF protection via DNS resolution validation
- Redirect blocking to prevent internal access
- 50KB response limit, 30s timeout
- No approval required

### code_run
Sandboxed code execution:
- **Docker mode**: python:3.11-slim, node:20-slim
- Resource limits: 128MB RAM, 50% CPU, no network
- Subprocess fallback for development
- 60s max timeout

### sql_query
Supabase PostgreSQL queries:
- Blocks dangerous operations (DROP, TRUNCATE, ALTER)
- DELETE/UPDATE require WHERE clause
- Parameterized queries prevent injection
- **Requires approval for all queries**

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_DB_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379
```

## Development

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific tool tests
python -m pytest tests/tools/test_web_fetch.py -v
python -m pytest tests/tools/test_code_run.py -v
python -m pytest tests/tools/test_sql_query.py -v

# Run schema tests
python -m pytest tests/agents/test_schemas.py -v

# Start Redis (Docker Compose)
docker-compose up -d redis
```

## Project Structure

```
conductor-ai/
├── .worktrees/agent-system/     # Feature development worktree
│   ├── src/
│   │   ├── agents/
│   │   │   ├── schemas.py       # Pydantic agent models
│   │   │   └── state.py         # State manager (WIP)
│   │   └── tools/
│   │       ├── base.py          # BaseTool, ToolRegistry
│   │       ├── web_fetch.py     # HTTP tool
│   │       ├── code_run.py      # Code sandbox
│   │       └── sql_query.py     # SQL tool
│   ├── tests/                   # 204 tests
│   └── docs/plans/              # Implementation plans
├── builder/                     # vLLM builder (existing)
├── src/                         # Main source
│   ├── model_catalog.py         # Model definitions
│   └── cost_optimizer.py        # Cost optimization
├── docker-compose.yml           # Redis + services
└── CLAUDE.md                    # Project instructions
```

## Models

Primary models for agent orchestration:
- **Claude 4.5 Opus** (`claude-opus-4-5-20251101`) - Complex reasoning
- **Claude 4.5 Sonnet** (`claude-sonnet-4-5-20250929`) - Default agent model

Budget alternatives via OpenRouter:
- Qwen 2.5 72B
- DeepSeek V3

## Contributing

1. Work in the `.worktrees/agent-system` directory
2. Run tests before committing
3. Follow existing code patterns
4. All tools need security review

## License

Proprietary - Scientia Capital
