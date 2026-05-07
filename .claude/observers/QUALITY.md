# Observer: Code Quality Report

**Date:** 2026-05-07
**Project:** epiphan-storyboard
**Observer:** Self-audit by main agent (Claude Opus 4.7) after async observer-full agent ran out of context budget at 74s before writing report files. Findings below were derived from a focused grep + manual review of the diff between `main` and `feature/bdr-call-brief-and-surveys` (commits 4e5752c, d58a675, bcb53d3 — Phase 1.1, 1.2, 1.3).
**Files reviewed:**
- `src/tools/storyboard/problem_statements.py` (NEW, 603 LOC)
- `src/tools/storyboard/transcript_compactor.py` (NEW, 388 LOC)
- `src/tools/storyboard/prompt_builders.py` (modified, +205 LOC)
- 3 corresponding test files (~600 LOC of tests)

---

## Critical (must fix before merge)

_None._ Brand-agnosticism on the user's primary concern (LMS/CMS/conferencing partners) is fully clean. No partner is framed as broken in any prompt, fixture, or seeded statement.

---

## Warnings (fix or log to backlog)

### W-1 — MEDIUM: Crestron / Extron / Q-SYS named in Frankenstack pattern block
**Where:** `src/tools/storyboard/prompt_builders.py:177`
**What:** The Frankenstack block names "Crestron / Extron / Q-SYS" as the broken layer in the "control without capture" pattern.
**Why it matters:** The user's brand-agnostic guidance was specifically about partner platforms (the LMS/CMS user cited was Panopto). The existing codebase puts Crestron/Extron in `COMPETITIVE_INTEL` rather than partners, so naming them is consistent with prior art — but the user's spirit-of-the-rule may extend to *all* third-party platforms regardless of competitive vs. partner status.
**Recommendation:** Reframe to brand-agnostic language: "A control system wired to capture gear that doesn't expose a clean API". Drop the brand names. They aren't load-bearing for the pattern — what matters is the integration gap.
**Action:** Promote to a follow-up task.

### W-2 — LOW: Bare `except Exception` in `build_problem_statement_anchor`
**Where:** `src/tools/storyboard/prompt_builders.py:140`
**What:** Catches all exceptions from `get_problem_statements` and silently returns empty string.
**Why it matters:** Defensible as graceful degradation (the prompt builders all use this pattern for KnowledgeCache failures), but a typo or schema bug could be hidden.
**Recommendation:** Narrow to `except (ValueError, ImportError)` and add a `logger.debug(...)` so debug-mode users can see when grounding silently degrades.
**Action:** Promote to a follow-up task. Low priority.

### W-3 — LOW: `DOC_PERSONA_ALIASES` has pragmatic but imperfect mappings
**Where:** `src/tools/storyboard/problem_statements.py:32–84`
**What:** Several mappings are a stretch because the 17-value `AudiencePersona` enum doesn't cover every doc role. Examples:
- "IT Director / CIO" (Higher Ed) → `law_firm_it` — wrong vertical context, but no `it_director` exists
- "IT Director / AV Manager" (Government) → `av_director` — overlaps with the dedicated AV Director role
- "Senior Pastor / Ministry Director" → `venue_manager` — a real stretch
**Why it matters:** The persona detection pipeline downstream (Phase 1.6 BDR brief generator) will inherit these slightly-off mappings. For Phase-1 verticals (Higher Ed, Legal, Live Events) the mappings are reasonable; for Phase-2 verticals (Government, K-12, Houses of Worship) the gaps will surface.
**Recommendation:** Two options:
- (a) Extend `AudiencePersona` enum with `it_director`, `pastor`, `volunteer_av_lead`, etc.
- (b) Add a `note_for_reviewer` comment beside each stretch mapping documenting the tradeoff.
**Action:** Promote to a Phase-2 task — not blocking Phase 1 since none of the stretch mappings are in the Phase-1 verticals.

### W-4 — LOW: Test gaps for transcript_compactor edge cases
**Where:** `tests/tools/storyboard/test_transcript_compactor.py`
**What:** Tests don't cover:
- CRLF line endings (Windows-style)
- Unicode speaker names (e.g., `José Ramírez:` or `张伟:`)
- `target_chars=0` or negative values
- Transcripts larger than 1 MB (typical Clari export upper bound)
- Speaker labels with weird punctuation (e.g., `Dr. (Dr.) Smith:`)
**Why it matters:** Real Clari/Gong exports may contain any of these. CRLF is most likely to surface since macOS/Linux dev → Windows-exported transcripts hit this routinely.
**Recommendation:** Add 5 parametrized edge-case tests in a follow-up task.
**Action:** Promote to a follow-up task.

---

## Info (nice to have)

### I-1 — Token-cost concern: `_FRANKENSTACK_PATTERN_BLOCK` adds ~1.2 KB to every transcript prompt
**Where:** `src/tools/storyboard/prompt_builders.py:164–185`
**What:** The pattern block is unconditionally injected into every transcript prompt.
**Why it matters:** ~300 tokens × every call. At Phase-1 volume (a few calls/day) this is negligible. At higher volumes the block could be conditionally skipped when the transcript is very short or no Frankenstack signals detected by `score_turn`.
**Recommendation:** Defer until volume justifies. Note in the prompt-tuning task list.

### I-2 — `key_moments` and `full_context` may duplicate content for short calls
**Where:** `src/tools/storyboard/prompt_builders.py:_build_transcript_prompt`
**What:** When `compaction_ratio == 1.0` (short call passed through), `key_moments` is just the first 8 K of the same text already in `full_context`. The prompt presents both labeled distinctly, which could confuse the LLM.
**Why it matters:** Cheap waste of tokens; could mildly degrade extraction quality on already-short calls.
**Recommendation:** Skip the `key_moments` block in the prompt when `len(full_context) <= key_moments_chars`.
**Action:** Promote to a follow-up task. Low priority.

### I-3 — Two-pass extraction prompts exist but aren't wired into `gemini_client`
**Where:** `src/tools/storyboard/gemini_client.py` (NOT MODIFIED in Phase 1.3)
**What:** `build_narrative_extraction_prompt` and `build_schema_mapping_prompt` are exposed and tested, but no caller orchestrates the two-pass flow yet. The existing single-pass flow still runs.
**Why it matters:** This is the Fix #2 from the plan. The new prompts are infrastructure-ready but the integration moment is in the BDR Brief generator (Phase 1.6) per the plan's reuse table.
**Recommendation:** No action — this is intentional staging. Phase 1.6 will wire them.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned | 6 (3 new src, 3 new/extended tests) |
| LOC added | ~1,772 |
| Tests added | 41 (22 problem_statements + 12 compactor + 9 prompt_builders polish) — all green |
| Critical findings | 0 |
| Warnings | 4 |
| Info items | 3 |
| Brand-agnosticism violations on LMS/CMS/conferencing partners | 0 |
| `# TODO` / `# FIXME` left in new code | 0 |
| Pre-existing test regressions | 0 (all 783 storyboard tests still green) |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1–1.3 | 6 | 7 (0C/4W/3I) | report-written |

---

## CLEANUP TASKS

Each item below is sized to become a single TaskCreate. Promoted to the task list as task #11–14 by the main agent.

1. **(W-1)** Reframe `_FRANKENSTACK_PATTERN_BLOCK` `control without capture` bullet to drop "Crestron / Extron / Q-SYS" brand names. Use generic language: "A control system wired to capture gear that doesn't expose a clean API."
2. **(W-2)** Tighten `except Exception` in `build_problem_statement_anchor` to specific exception types and add a `logger.debug` so silent degradation is observable.
3. **(W-3)** Phase-2: extend `AudiencePersona` enum with `it_director`, `pastor`, `volunteer_av_lead`, etc., OR document each stretch mapping inline with a `note_for_reviewer` comment.
4. **(W-4)** Add 5 parametrized edge-case tests for `transcript_compactor`: CRLF, unicode speakers, target_chars=0, 1 MB transcript, weird speaker punctuation.
5. **(I-2)** When `compaction_ratio == 1.0` (no compaction needed), skip the `=== KEY MOMENTS ===` block in the transcript prompt so we don't duplicate content for the LLM.
