# Pipeline: End of Day (Audit + Sync + Close Out)

Comprehensive end-of-day workflow to audit work, verify security, update docs, sync git, and prepare for tomorrow.

## Usage

```
/pipeline:eod
```

## Overview

This pipeline ensures:
- All work is audited and summarized
- Security sweep BEFORE any commits
- Documentation is current
- Code quality is verified
- Git is clean and synced
- Tomorrow's context is ready

---

## Phase 1: Audit Today's Work

**Goal:** Review what was accomplished today.

### Step 1: Load Context

Load project context skills:
```
Loading workflow-enforcer + project-context-skill...
```

### Step 2: Review Git Activity

```bash
# Today's commits
git log --oneline --since="midnight" --author="$(git config user.name)"

# Changed files (uncommitted)
git status --short

# Open worktrees
git worktree list

# Current branch
git branch --show-current
```

### Step 3: Summarize Work

Invoke brainstorming skill:
```
I'm using the superpowers:brainstorming skill to summarize today's work.

Summarize:
- Completed tasks
- Blockers encountered
- Next steps for tomorrow
```

### Gate 1: Audit Review

**Output:**
```
Today's Work Summary:
- Commits: [N] commits
- Files changed: [N] files
- Worktrees: [N] open

Completed:
- [task 1]
- [task 2]

Blockers:
- [blocker 1]

Next steps:
- [next 1]
```

**Ask:**
```
Phase 1 complete. Work audit ready.

Proceed to Phase 2 (Security Sweep)? (yes/no)
```

---

## Phase 2: Security Sweep (BEFORE ANY COMMITS)

**Goal:** Comprehensive security check before committing anything.

### Step 1: Secrets Scan

```bash
set -e

# Scan for API keys (common patterns)
echo "Scanning for secrets..."

# OpenAI keys (FORBIDDEN in this project)
! grep -rn "sk-[a-zA-Z0-9]\{20,\}" --include="*.py" --include="*.js" --include="*.ts" . || {
    echo "ERROR: Possible API key found"
    exit 1
}

# Generic API key patterns
! grep -rn "api[_-]?key.*['\"][a-zA-Z0-9]\{20,\}['\"]" --include="*.py" --include="*.js" . || {
    echo "WARNING: Possible hardcoded API key"
}

# AWS keys
! grep -rn "AKIA[A-Z0-9]\{16\}" . || {
    echo "ERROR: AWS key pattern found"
    exit 1
}

# Private keys
! grep -rn "BEGIN.*PRIVATE KEY" . || {
    echo "ERROR: Private key found"
    exit 1
}
```

### Step 2: Check Git History

```bash
# Check if any secrets were ever committed
git log -p --all -S "sk-" -- "*.py" "*.js" "*.ts" | head -50
git log -p --all -S "AKIA" -- "*.py" "*.js" "*.ts" | head -50
```

### Step 3: Dependency Audit

```bash
# Python dependencies
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    pip-audit 2>/dev/null || echo "pip-audit not installed, skipping"
fi

# Node dependencies
if [ -f "package.json" ]; then
    npm audit 2>/dev/null || echo "npm audit failed or not available"
fi
```

### Step 4: Env File Audit

```bash
set -e

# Ensure .env is gitignored
if [ -f ".env" ]; then
    grep -q "\.env" .gitignore || {
        echo "ERROR: .env not in .gitignore!"
        exit 1
    }
fi

# Check .env.example exists (good practice)
if [ -f ".env" ] && [ ! -f ".env.example" ]; then
    echo "WARNING: .env exists but no .env.example template"
fi

# Verify no .env files are tracked
git ls-files | grep -E "\.env$" && {
    echo "ERROR: .env file is tracked in git!"
    exit 1
} || true
```

### Step 5: SAST Scan (Static Analysis)

```bash
# Python security checks with ruff
ruff check . --select S --ignore S101 2>/dev/null || echo "Ruff security check skipped"

# Check for common vulnerabilities
! grep -rn "eval(" --include="*.py" . || echo "WARNING: eval() usage found"
! grep -rn "exec(" --include="*.py" . || echo "WARNING: exec() usage found"
! grep -rn "shell=True" --include="*.py" . || echo "WARNING: shell=True in subprocess"
```

### Gate 2: Security Verification

**Checklist:**
- [ ] No API keys/secrets in code
- [ ] No secrets in git history
- [ ] Dependencies audited
- [ ] .env properly gitignored
- [ ] No dangerous patterns (eval, exec, shell=True)

**On FAIL:**
```
Security issues found:

[list issues]

Options:
1. Fix now - I'll help remove the secrets
2. Note for tomorrow - Add to tomorrow's first task
3. Abort - Stop pipeline, do NOT commit

Which option?
```

**On PASS:**
```
Phase 2 complete. Security sweep passed.

Proceed to Phase 3 (Update Docs)? (yes/no)
```

---

## Phase 3: Update Project Docs

**Goal:** Keep documentation current.

### Step 1: Check Doc Files

```bash
# List doc files that should be updated
echo "Documentation files to review:"
ls -la TASK.md PLANNING.md Backlog.md CLAUDE.md 2>/dev/null || true
```

### Step 2: Update TASK.md

```
Review TASK.md:
- Mark completed tasks as DONE
- Move next priority task to top
- Add any new tasks discovered today
```

**Ask:** "Any updates to TASK.md? (describe or 'skip')"

### Step 3: Update PLANNING.md

```
Review PLANNING.md:
- Reflect today's progress
- Adjust any timeline changes
- Note blockers or dependencies
```

**Ask:** "Any updates to PLANNING.md? (describe or 'skip')"

### Step 4: Update Backlog.md

```
Review Backlog.md:
- Add new items discovered today
- Reprioritize if needed
- Archive completed items
```

**Ask:** "Any new backlog items? (describe or 'skip')"

### Step 5: Update CLAUDE.md

```
Review CLAUDE.md:
- Add any new patterns discovered
- Document decisions made today
- Update project status section
```

**Ask:** "Any patterns/decisions to add to CLAUDE.md? (describe or 'skip')"

### Gate 3: Docs Updated

**Checklist:**
- [ ] TASK.md reviewed/updated
- [ ] PLANNING.md reviewed/updated
- [ ] Backlog.md reviewed/updated
- [ ] CLAUDE.md reviewed/updated

**Ask:**
```
Phase 3 complete. Documentation updated.

Proceed to Phase 4 (Code Quality)? (yes/no)
```

---

## Phase 4: Code Quality Audit

**Goal:** Review code quality for uncommitted changes.

### Step 1: Code Review

If there are uncommitted changes:
```
Dispatching superpowers:code-reviewer agent...

Review scope: All uncommitted changes
Focus: Code quality, patterns, potential bugs
```

### Step 2: Linter Check

```bash
set -e

# Format code
ruff format . 2>/dev/null || true

# Lint check
ruff check . --fix 2>/dev/null || true

# Type check
mypy src/ plugins/ 2>/dev/null || echo "mypy skipped"
```

### Step 3: Test Coverage Check

```bash
# Check if new files have tests
git diff --name-only --cached | grep "\.py$" | while read file; do
    testfile="tests/test_$(basename $file)"
    if [ ! -f "$testfile" ]; then
        echo "WARNING: No test file for $file"
    fi
done
```

### Gate 4: Quality Verified

**Checklist:**
- [ ] Code review completed (if changes exist)
- [ ] Linter passes
- [ ] Type checks pass
- [ ] New code has tests

**Ask:**
```
Phase 4 complete. Code quality verified.

Proceed to Phase 5 (Git Sync)? (yes/no)
```

---

## Phase 5: Git Cleanup & Sync

**Goal:** Clean git state and sync everything.

### Step 1: Status Check

```bash
echo "=== Git Status ==="
git status

echo "=== Unpushed Commits ==="
git log --oneline @{u}..HEAD 2>/dev/null || echo "No upstream set"

echo "=== Stashes ==="
git stash list

echo "=== Worktrees ==="
git worktree list

echo "=== Branches ==="
git branch -vv
```

### Step 2: Commit Changes

If there are uncommitted changes:
```
Preparing commit...

Commit message format:
feat/fix/docs([scope]): [today's work summary]

- [change 1]
- [change 2]

EOD: [date]
```

```bash
git add .
git commit -m "$(cat <<'EOF'
feat(pipeline): End of day commit - [DATE]

- [Summary of today's work]

EOD automated commit

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 3: Push All Branches

```bash
# Push current branch
git push -u origin $(git branch --show-current)

# List other local branches that need pushing
git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads | \
    while read local remote; do
        if [ -z "$remote" ]; then
            echo "Branch $local has no upstream"
        fi
    done
```

### Step 4: Worktree Cleanup

```bash
# List worktrees
git worktree list

# Identify stale worktrees (branches already merged)
echo "Checking for stale worktrees..."
```

**Ask:** "Any worktrees to archive/remove? (list or 'skip')"

### Gate 5: Git Synced

**Checklist:**
- [ ] All changes committed
- [ ] All branches pushed
- [ ] Stashes reviewed
- [ ] Worktrees cleaned up

**Ask:**
```
Phase 5 complete. Git synced.

Proceed to Phase 6 (Final Verification)? (yes/no)
```

---

## Phase 6: Final Security Verification & Tomorrow Context

**Goal:** Final verification and prepare for tomorrow.

### Step 1: Pre-Commit Security Gate (BLOCKING)

```bash
set -e

echo "=== Final Security Gate ==="

# Secrets check (must pass)
! grep -rn "sk-" --include="*.py" . || {
    echo "BLOCKED: Secret pattern found"
    exit 1
}

# OpenAI check (project rule)
! grep -rn "OPENAI" --include="*.py" src/ plugins/ || {
    echo "BLOCKED: OpenAI reference found"
    exit 1
}

# Env check
grep -q "\.env" .gitignore || {
    echo "BLOCKED: .env not in .gitignore"
    exit 1
}

echo "Security gate PASSED"
```

### Step 2: Final State Verification

```bash
echo "=== Final State ==="

# Clean working tree
if [ -z "$(git status --porcelain)" ]; then
    echo "Working tree: CLEAN"
else
    echo "WARNING: Uncommitted changes remain"
fi

# All pushed
if [ -z "$(git log @{u}..HEAD 2>/dev/null)" ]; then
    echo "Branches: ALL PUSHED"
else
    echo "WARNING: Unpushed commits exist"
fi

# Docs current
echo "Docs updated: [based on Phase 3]"
```

### Step 3: Generate Tomorrow Context

```
Tomorrow's Context:

**Start Here:**
- Task: [next priority from TASK.md]
- File: [last file worked on]
- Line: [relevant line number]

**Context to Load:**
- Run: /pipeline:feature [next feature] OR continue existing work
- Review: [any blockers noted]

**First Command:**
[suggested first command for tomorrow]
```

### Gate 6: Day Complete

**Final Checklist:**
- [ ] Security gate passed
- [ ] Working tree clean
- [ ] All branches pushed
- [ ] Docs current
- [ ] Tomorrow context generated

**Output:**
```
=== END OF DAY COMPLETE ===

Summary:
- Commits today: [N]
- Files changed: [N]
- Security: PASSED
- Docs: UPDATED
- Git: SYNCED

Tomorrow: [next task]

Have a good evening!
```

---

## Critical Rules (Enforced Throughout)

```bash
# NO OpenAI (project rule)
! grep -r "OPENAI" --include="*.py" src/ plugins/

# NO hardcoded secrets
! grep -r "sk-" --include="*.py" .
! grep -r "AKIA" .
! grep -r "BEGIN.*PRIVATE KEY" .

# .env must be gitignored
grep -q "\.env" .gitignore
```

---

## Phase Summary

```
Phase 1 (Audit) ──► Gate 1 (Work Summarized?)
         │
         ▼
Phase 2 (Security) ──► Gate 2 (No Secrets?) ◄── CRITICAL
         │
         ▼
Phase 3 (Docs) ──► Gate 3 (Docs Updated?)
         │
         ▼
Phase 4 (Quality) ──► Gate 4 (Code Clean?)
         │
         ▼
Phase 5 (Git Sync) ──► Gate 5 (All Pushed?)
         │
         ▼
Phase 6 (Final) ──► Gate 6 (Security Gate + Tomorrow Ready?) ◄── BLOCKING
         │
         ▼
      DAY COMPLETE
```

**Total: 6 phases, with Phase 2 and Phase 6 as security gates.**

---

## Troubleshooting

### Secret found in code

```bash
# Find the secret
grep -rn "sk-" --include="*.py" .

# Remove and replace with env var
# In code: os.getenv("API_KEY")
# In .env: API_KEY=sk-xxx
```

### Secret in git history

```bash
# This is serious - may need to rotate the key
# Option 1: BFG Repo Cleaner
# Option 2: git filter-branch
# Option 3: Rotate the exposed key immediately
```

### Uncommitted changes won't commit

```bash
# Check what's blocking
git status
git diff

# Force add if needed (after security check)
git add -A
```

### Branch won't push

```bash
# Check upstream
git branch -vv

# Set upstream
git push -u origin $(git branch --show-current)
```
