# Observer: Architecture Report

**Date:** 2026-05-07
**Project:** epiphan-storyboard
**Branch:** feature/bdr-call-brief-and-surveys
**Commits reviewed:** 4e5752c, d58a675, bcb53d3 (Phase 1.1, 1.2, 1.3)

---

## Blockers (stop work immediately)

_None._

---

## Risks (address this sprint)

### R-1 — Two-pass extraction prompts are infrastructure-ready but not yet orchestrated
**Severity:** MEDIUM
**Where:** `src/tools/storyboard/prompt_builders.py:191–270` (the new two-pass functions) vs. `src/tools/storyboard/gemini_client.py` (no caller yet).
**Risk:** The plan's Fix #2 ships only half-done if Phase 1 ends here. The pipeline still uses single-pass extraction; the narrative→schema two-pass advantage isn't realized until a caller orchestrates both prompts.
**Mitigation:** Phase 1.6 (BDR Brief generator) is explicitly the place this gets wired per the plan's reuse table. Confirm before closing Phase 1.
**Owner:** Phase 1.6 implementer.

### R-2 — Phase-1 problem-statement library is intentionally partial; the matcher silently returns `[]` for the 6 unseeded verticals
**Severity:** MEDIUM
**Where:** `src/tools/storyboard/problem_statements.py:PROBLEM_STATEMENTS`
**Risk:** A user picking Government / K-12 / etc. from the demo dropdown will get the existing pipeline output with no problem-statement grounding (silent degradation). The output won't crash, but it'll be lower quality than Phase-1 verticals without any UI signal.
**Mitigation:** Either (a) add a UI banner in `static/demo.html` indicating which verticals are Phase-1, or (b) ensure the prompt builder logs a debug message when no statements are found.
**Owner:** Phase 1.8 (UI work).

### R-3 — `compact_transcript` uses cheap keyword scoring; semantic-rich content with no surface keywords could be dropped
**Severity:** LOW-MEDIUM
**Where:** `src/tools/storyboard/transcript_compactor.py:score_turn`
**Risk:** A prospect describing a real workaround using novel language ("our team kludges around it with a homegrown thing") would score 0 (no `_PAIN_PHRASES` match) and could be culled from compaction. The pain phrase list is what we know to look for, but reality is bigger than our list.
**Mitigation:** The `edge_pct` fallback (always retain first/last 10%) hedges this somewhat. Long-term: add an embedding-based similarity score against a JTBD-relevant seed. Not blocking Phase 1.

---

## Smells (log to backlog)

### S-1 — Two cooperating modules with no integration test
**Where:** `problem_statements.py` ↔ `prompt_builders.build_problem_statement_anchor` ↔ `_build_transcript_prompt`
**Smell:** All three are unit-tested independently; no test goes end-to-end from "vertical=higher_ed, persona=av_director, transcript pasted" through to "verbatim statement appears in the rendered transcript prompt." The Phase-1.3 test `test_anchor_appears_in_transcript_prompt` covers part of this but doesn't assert the verbatim content.
**Fix:** Add a single integration test in Phase 1.5 (when survey endpoints land) that exercises the full chain.

### S-2 — `AudiencePersona` enum is the chokepoint for all persona logic but doesn't cover every real role
**Where:** `src/tools/storyboard/epiphan_presets.py:613` (the enum)
**Smell:** The 17-value enum was sized for Phase-0 BDR personas, but the BDR Playbook doc has 32 roles. The Phase-1 mapping table has 9 stretch mappings (e.g., "Senior Pastor" → `venue_manager`).
**Fix:** Expand the enum in Phase 2 OR introduce a `vertical_persona` composite key (vertical, role_string) that doesn't require enum coverage.

### S-3 — `_FRANKENSTACK_PATTERN_BLOCK` is module-level constant; not vertical-aware
**Where:** `src/tools/storyboard/prompt_builders.py:164`
**Smell:** Higher Ed prospects' Frankenstacks ≠ Live Events prospects' Frankenstacks. A single global pattern block fits all but optimizes none.
**Fix:** Phase 2: parameterize per-vertical pattern blocks. For Phase 1 the global block is good enough.

### S-4 — Test transcripts use synthetic "Speaker 1: filler" content; never tested against a real Clari/Gong export
**Where:** All `test_transcript_compactor.py` and the new `test_prompt_builders.py` cases.
**Smell:** Synthetic data has lower variance than real-world transcripts. Real Clari exports have timestamps, speaker IDs, occasional [INAUDIBLE] tokens, and varying segmentation conventions.
**Fix:** Phase 1.9 (verification) should include at least one anonymized real transcript fixture and a regression test against it.

---

## Architectural Notes (no action)

- **Decoupling**: Phase 1.1 and 1.2 ship as pure additions with zero modifications to live code. That's why all 783 existing storyboard tests stayed green throughout. Phase 1.3 was the integration moment and was likewise non-destructive (the old `[:32000]` slice was *replaced*, not augmented; the new helpers are *additive*).
- **Reuse**: The `ForcesOfProgress` Pydantic model from `src/storyboard/schemas.py` is the canonical shape; `BuyerProfile` (Phase 1.4) reuses it rather than introducing a parallel structure. Good.
- **Module boundaries**: `problem_statements.py` (data + retrieval) and `transcript_compactor.py` (deterministic processing) have no LLM dependencies; they could be unit-tested at any volume without API costs. `prompt_builders.py` is purely string assembly. The actual LLM calls live in `gemini_client.py` and aren't touched in this phase. Clean separation.
