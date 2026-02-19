# Pipeline: Feature Development

Orchestrate a 6-phase development workflow with gate controls at every phase transition.

## Usage

```
/pipeline:feature [feature-description]
```

**Example:**
```
/pipeline:feature Add user authentication with JWT tokens
```

## Overview

This pipeline enforces:
- TDD approach throughout
- No OpenAI models (use DeepSeek/Qwen/Claude only)
- API keys in .env only
- >90% test coverage
- Code review before commit
- Gate approval at every phase

---

## Phase 0: Planning & Agent Assignment

**Goal:** Refine the feature idea and create an implementation plan.

### Step 1: Brainstorm

Invoke the brainstorming skill to refine requirements:

```
I'm using the superpowers:brainstorming skill to refine your idea into a design.
```

Gather through Socratic questioning:
- Feature purpose and scope
- Success criteria
- Constraints (technical, business)
- Dependencies on existing code

### Step 2: Create Plan

Invoke the writing-plans skill:

```
I'm using the superpowers:writing-plans skill to create the implementation plan.
```

Output: Detailed implementation plan with:
- Database schema (if needed)
- API endpoints
- UI components
- Test specifications

### Gate 0: Plan Approval

**Checklist:**
- [ ] Feature requirements clearly defined
- [ ] Implementation plan created
- [ ] No OpenAI dependencies in plan
- [ ] Scope reasonable for single pipeline run

**Ask:**
```
Phase 0 complete. Plan ready for review.

Proceed to Phase 1 (Database)? (yes/no)
```

---

## Phase 1: Database (Sequential Foundation)

**Goal:** Design and create database schema. This phase is SEQUENTIAL because other phases depend on it.

### Step 1: Schema Design

Dispatch the database architect agent:

```
Dispatching database-design:database-architect agent...

Task: Design database schema for [feature]
- Use Supabase PostgreSQL patterns
- Include Row Level Security (RLS) policies
- Follow conductor-ai naming conventions
- Generate migration SQL
```

### Step 2: Generate Migration

Create migration file in `sql/` directory:

```sql
-- sql/XXX_[feature_name].sql
-- Migration for [feature]

CREATE TABLE IF NOT EXISTS [table_name] (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- columns
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE [table_name] ENABLE ROW LEVEL SECURITY;
```

### Gate 1: Schema Approval

**Verification:**
```bash
set -e

# Verify migration file exists
test -f sql/*.sql || { echo "ERROR: No migration file created"; exit 1; }

# Check for OpenAI references
! grep -r "OPENAI" --include="*.sql" sql/ || { echo "ERROR: OpenAI reference found"; exit 1; }

# Verify no hardcoded keys
! grep -r "sk-" --include="*.sql" sql/ || { echo "ERROR: Hardcoded key found"; exit 1; }
```

**Checklist:**
- [ ] Migration file created in sql/
- [ ] RLS policies defined
- [ ] No OpenAI references
- [ ] No hardcoded API keys

**Ask:**
```
Phase 1 complete. Database schema ready.

Proceed to Phase 2 (Parallel Implementation)? (yes/no)
```

---

## Phase 2: Parallel Implementation

**Goal:** Implement backend, frontend, and tests SIMULTANEOUSLY.

### Parallel Agent Dispatch

Dispatch 3 agents in a single message (parallel execution):

```
Dispatching 3 agents in parallel...

**Agent 1: Backend** (api-scaffolding:fastapi-pro)
- Implement API endpoints for [feature]
- Follow FastAPI async patterns from src/api.py
- Use Pydantic v2 models
- Return: Files changed, endpoint list

**Agent 2: Frontend** (application-performance:frontend-developer)
- Build UI components for [feature]
- Follow React/TypeScript patterns
- Return: Component structure, files changed

**Agent 3: Tests** (python-development:python-pro)
- Use superpowers:test-driven-development skill
- Write failing tests FIRST (RED)
- Target >90% coverage
- Return: Test files, coverage estimate

All agents running concurrently...
```

### Wait for Completion

All three agents must complete before proceeding.

### Gate 2: Implementation Review

**Verification:**
```bash
set -e

# Run linter
ruff format . && ruff check . --fix

# Type check
mypy src/ plugins/

# Verify tests exist
test -f tests/test_*.py || { echo "ERROR: No tests created"; exit 1; }

# No OpenAI
! grep -r "OPENAI" --include="*.py" src/ plugins/ || exit 1
```

**Checklist:**
- [ ] Backend endpoints implemented
- [ ] Frontend components created
- [ ] Tests written (TDD approach)
- [ ] Linter passes
- [ ] Type checks pass

**Ask:**
```
Phase 2 complete. Implementation ready for integration.

Proceed to Phase 3 (Integration & Security)? (yes/no)
```

---

## Phase 3: Integration & Security

**Goal:** Wire components together and verify security.

### Step 1: Integration

- Register new tools in ToolRegistry (if applicable)
- Add API endpoints to router
- Wire frontend to backend APIs
- Update `__init__.py` exports

### Step 2: Security Scan

```bash
set -e

# Check for SSRF vulnerabilities in URLs
# Verify API key handling

# Critical: No OpenAI references
! grep -r "OPENAI" --include="*.py" src/ plugins/ || { echo "ERROR: OpenAI reference found"; exit 1; }

# Critical: No hardcoded keys
! grep -r "sk-" --include="*.py" src/ plugins/ || { echo "ERROR: Hardcoded key found"; exit 1; }

# Verify imports work
python -c "from src.tools import *" || { echo "ERROR: Import failed"; exit 1; }
```

### Gate 3: Security Verification

**Checklist:**
- [ ] Components wired together
- [ ] Imports working
- [ ] No OpenAI references
- [ ] No hardcoded API keys
- [ ] SSRF protections in place (if URLs handled)

**Ask:**
```
Phase 3 complete. Integration and security verified.

Proceed to Phase 4 (Testing)? (yes/no)
```

---

## Phase 4: Testing

**Goal:** Run comprehensive test suite using /validate command.

### Invoke Validation

Run the existing validation command:

```
Running /validate command...
```

This executes:
1. **Phase 1:** Code Quality (Ruff format + check)
2. **Phase 2:** Type Safety (mypy)
3. **Phase 3:** Tests (pytest with coverage)
4. **Phase 4:** Security Checks
5. **Phase 5:** Dependency Audit
6. **Phase 6:** Project Structure

### Coverage Requirement

```bash
# Must meet coverage threshold
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing --cov-fail-under=90
```

### Gate 4: All Tests Pass

**Verification:**
```bash
set -e

# Full test suite
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing

# Coverage check
coverage report --fail-under=90

# Type safety
mypy src/ plugins/
```

**Checklist:**
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Coverage >= 90%
- [ ] Type checks passing
- [ ] Security checks passing

**Ask:**
```
Phase 4 complete. All tests passing with [X]% coverage.

Proceed to Phase 5 (Code Review)? (yes/no)
```

---

## Phase 5: Code Review (BLOCKING)

**Goal:** 100% clean code before commit. This gate has NO SKIP option.

### Step 1: Dispatch Code Reviewer

```
Dispatching superpowers:code-reviewer agent...

Review focus:
- Code quality and patterns
- Security vulnerabilities
- Architecture alignment
- Test coverage gaps
```

### Step 2: Verification Before Completion

Invoke the verification skill:

```
I'm using the superpowers:verification-before-completion skill.
```

This ensures:
- All claims verified with evidence
- No assumptions about passing tests
- Actual verification output shown

### Gate 5: Code Review (BLOCKING)

**THIS GATE CANNOT BE SKIPPED**

**Verification:**
```bash
set -e

# Final security check
! grep -r "OPENAI" --include="*.py" src/ plugins/ || exit 1
! grep -r "sk-" --include="*.py" src/ plugins/ || exit 1

# Final test run
pytest tests/ -v --cov=src --cov-fail-under=90

# Final type check
mypy src/ plugins/
```

**Checklist:**
- [ ] Code review completed
- [ ] All review issues addressed
- [ ] No OpenAI references
- [ ] No hardcoded keys
- [ ] Tests passing
- [ ] Type checks passing

**On PASS:**
```
Phase 5 complete. Code review passed with zero issues.

Proceed to Phase 6 (Commit/PR)? (yes/no)
```

**On FAIL:**
```
Phase 5 FAILED. Code review found issues.

Issues found:
[list of issues]

Options:
1. Fix and re-review - I'll fix the issues and run review again
2. Manual fix - You fix, then tell me to re-review

NOTE: Skip is NOT available for Phase 5. Must be 100% clean.

Which option?
```

---

## Phase 6: Commit/PR

**Goal:** Clean commit or PR. Only proceeds if Phase 5 passed.

### Pre-requisites

- Phase 5 passed with zero errors
- All tests passing (verified fresh)
- No OpenAI references
- No hardcoded keys

### Invoke Finishing Skill

```
I'm using the superpowers:finishing-a-development-branch skill to complete this work.
```

### Verify Tests One More Time

```bash
pytest tests/ -v
```

### Present Options

```
Implementation complete. What would you like to do?

1. Merge back to main locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

### Execute Choice

**Option 1: Merge Locally**
```bash
git checkout main
git pull
git merge feature/[feature-name]
pytest tests/ -v  # Verify on merged result
git branch -d feature/[feature-name]
```

**Option 2: Create PR**
```bash
git push -u origin feature/[feature-name]
gh pr create --title "[feature-name]" --body "$(cat <<'EOF'
## Summary
- [Key change 1]
- [Key change 2]

## Test Plan
- [ ] All tests passing
- [ ] Coverage >= 90%

---
Generated with Claude Code
EOF
)"
```

**Option 3: Keep As-Is**
```
Keeping branch [name]. You can handle it later.
```

**Option 4: Discard**
```
This will permanently delete:
- Branch [name]
- All commits

Type 'discard' to confirm.
```

---

## Gate Failure Handling

When any gate fails (except Phase 5), present these options:

```
Gate [N] FAILED

Failed checks:
- [ ] [failed check description]

Error output:
[paste error output]

Options:
1. Fix and retry - I'll dispatch an agent to fix the issue
2. Manual fix - You fix it, then tell me to retry
3. Skip phase - Continue anyway (NOT available for Phase 5)
4. Abort pipeline - Stop here, keep all work

Which option?
```

---

## Critical Rules (Enforced at Every Gate)

These rules are NON-NEGOTIABLE:

```bash
# NO OpenAI models
! grep -r "OPENAI" --include="*.py" src/ plugins/ || exit 1

# API keys in .env ONLY
! grep -r "sk-" --include="*.py" src/ plugins/ || exit 1

# Coverage threshold
pytest tests/ --cov=src --cov-fail-under=90

# Type safety
mypy src/ plugins/
```

**Model usage:**
- DeepSeek V3/R1
- Qwen 3
- Claude Sonnet/Opus
- Gemini Flash

**NEVER use OpenAI models.**

---

## Troubleshooting

### Gate keeps failing

```bash
# Check specific error
pytest tests/test_[feature].py -vv --tb=long

# Check type errors
mypy src/[file].py --show-error-codes
```

### Coverage too low

```bash
# Find uncovered lines
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### OpenAI reference found

```bash
# Find the reference
grep -rn "OPENAI" --include="*.py" src/ plugins/

# Replace with appropriate model
# Use: deepseek/deepseek-chat, qwen/qwen-3, claude-sonnet-4-5-20250929
```

### Parallel agents not completing

- Check each agent's output separately
- Verify no conflicting file edits
- Run `git status` to see changes

### Type check failing

```bash
# Ignore third-party issues (add to pyproject.toml)
[tool.mypy]
ignore_missing_imports = true
```

---

## Phase Summary

```
Phase 0 (Planning) ──► Gate 0 (Plan Approved?)
         │
         ▼
Phase 1 (Database) ──► Gate 1 (Schema Approved?)
         │
         ▼
Phase 2 (Parallel) ──► Gate 2 (Linter + Types Pass?)
  ├─ Backend Agent
  ├─ Frontend Agent
  └─ Test Agent
         │
         ▼
Phase 3 (Integration) ──► Gate 3 (Security Verified?)
         │
         ▼
Phase 4 (Testing) ──► Gate 4 (All Tests Pass?)
         │
         ▼
Phase 5 (Review) ──► Gate 5 (100% Clean?) ◄── BLOCKING, NO SKIP
         │
         ▼
Phase 6 (Commit) ──► Present Options (Merge/PR/Keep/Discard)
```

**Total: 6 phases, 6 gates, with Phase 5 as blocking checkpoint.**
