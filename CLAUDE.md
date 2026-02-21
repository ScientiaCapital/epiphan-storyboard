# Epiphan Storyboard

## Identity
- Epiphan Video storyboard and content generation platform
- Owner: THK Enterprises LLC
- Deployed on Vercel

## Dev Commands
- `uvicorn src.api:app --reload` — Run dev server
- `python -m pytest tests/ -v` — Run tests
- `python -m mypy src/ --ignore-missing-imports` — Type check
- `ruff check src/` — Lint
- `ruff format src/` — Format

## Code Conventions
- Python 3.13+, async/await throughout
- Pydantic v2 for all schemas
- Type hints required on all functions
- FastAPI routers in src/routers/
- Agent logic in src/router/ (classifier + chains)
- Tools in src/tools/ (storyboard, recording, video)

## Key Architecture
- src/api.py — FastAPI app entry point
- src/tools/storyboard/ — Storyboard generation (Gemini Flash)
- src/tools/storyboard/epiphan_presets.py — ICP presets and personas
- src/router/ — Agent router (classification + chain execution)
- src/knowledge/ — Knowledge brain (learning pipeline)
- src/connectors/ — Data connectors (Gong, Fireflies, Close, etc.)
- src/billing/ — Stripe billing integration

## Epiphan Context
- Products: Pearl Mini ($3,750), Pearl Nano ($1,999), Pearl Nexus ($3,299), Pearl-2 ($7,999), EC20 PTZ ($1,899), AV.io 4K ($579.95), AV.io HD+ ($449.95), AV.io SDI+ ($579.95)
- Verticals (10): Higher Ed, Corporate, Live Events, Government, Houses of Worship, Healthcare, Industrial, Legal, UX Research, K-12
- Personas (8 BDR Playbook):
  - ATL Decision Makers (7): AV Director, L&D Director, Sim Center Director, Court Admin, Corp Comms, EHS Manager, Law Firm IT
  - BTL Operators (1): Technical Director
- Default persona: av_director (most common buyer across verticals)

## Rules
- NO OpenAI — use Anthropic, Google Gemini, or OpenRouter only
- All content must reference Epiphan products only
- All storyboard content must use epiphan_presets.py ICP

---

## MANDATORY: Observer Protocol

**You MUST follow this protocol before writing ANY code.** No exceptions. No rationalizing.

### Step 1: Classify Task Scope

| Scope | Criteria | Observer Required |
|-------|----------|-------------------|
| **MINIMAL** | Typos, comments, single config tweak | None |
| **SMALL** | 1-3 files changed, no new dependencies | observer-lite (Haiku) |
| **STANDARD** | 4-10 files, or any new dependency | observer-full (Sonnet) |
| **FULL** | >10 files, new architecture, new patterns | observer-full + feature contract |

### Step 2: Spawn Observer (if SMALL or above)

```
# For SMALL scope:
Task tool -> subagent_type: "observer-lite"
  prompt: "Run quality checks on the epiphan-storyboard codebase. Focus on [relevant area]."

# For STANDARD/FULL scope:
Task tool -> subagent_type: "observer-full"
  prompt: "Run full drift detection on epiphan-storyboard. The current task is: [describe task]."
```

### Step 3: For FULL scope — Create Feature Contract First

Before coding, create `.claude/contracts/[feature-name].md`:
- Define IN SCOPE and OUT OF SCOPE boundaries
- List success criteria
- Get observer approval before writing code

### Step 4: Verify Observer Ran

Before making your first code change, confirm:
- [ ] `.claude/OBSERVER_QUALITY.md` has a real date (not `_not yet run_`)
- [ ] Scope classification matches the task complexity

**If the PreToolUse hook prints `** OBSERVER NOT ACTIVE **`, STOP and spawn the observer.**

### Scope Escalation Rule

If during work you hit ANY of these triggers, upgrade from Lite to Full:
- **>5 files modified** (the PostToolUse hook will remind you)
- **New dependency added** to package.json or pyproject.toml
- **Task scope expanded** beyond original description

---

## Dual-Team Workflow

This project uses the **TK Dual-Team Daily Workflow**.

### Quality Gates

| Gate | Check | Enforced By |
|------|-------|-------------|
| Pre-code | Observer spawned | PreToolUse hook |
| During code | Scope escalation | PostToolUse hook |
| Pre-merge | No open BLOCKERs | OBSERVER_ALERTS.md |

### Observer Cost Guide

| Observer | Model | Cost | When |
|----------|-------|------|------|
| observer-lite | Haiku 4.5 | ~$0.03-0.05 | SMALL scope |
| observer-full | Sonnet 4.6 | ~$0.50-2.00 | STANDARD/FULL scope |

### Copy-Paste Prompts

**START DAY:** Start day — project is epiphan-storyboard. Path: ~/Desktop/tk_projects/epiphan-storyboard
**FEATURE BUILD:** Feature build — [FEATURE_NAME]
**END DAY:** End day — project is epiphan-storyboard
