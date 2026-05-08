# Planning — epiphan-storyboard

**Last updated:** 2026-05-07

## Active sprint: Phase 1 — BDR Discovery Workflow ✅ COMPLETE

Shipped on `feature/bdr-call-brief-and-surveys` (10 commits, 5,630 LOC, 1,446 tests).
Production-deployed to `https://epiphan-storyboard.vercel.app` and smoke-verified.

**Estimated effort:** 4.5 dev-days (per `tidy-beaming-pebble.md` plan)
**Actual:** ~1 session (compressed via subagent-assisted parallel execution)

## Next sprint: Phase 2 priorities

Ranked by leverage / impact:

1. **DA-R1: Wire two-pass extraction in `gemini_client.py`** (HIGH impact)
   - Phase 1.3 shipped the prompts; orchestration is the remaining 2–3 hr
   - Unlocks the Forces-of-Progress quality lift documented in the original plan
2. **End-to-end grounding integration test** (MEDIUM impact, prevents regressions)
3. **Real-world transcript fixtures** (MEDIUM impact, catches Clari/Gong-specific quirks)
4. **Phase-2 vertical degradation UI signal** (MEDIUM impact, UX clarity)
5. **SSOT for demo dropdowns** (MEDIUM impact, prevents recurring 422 bug class)

## Tomorrow

If continuing the BDR thread → start with DA-R1 (highest leverage, ~half-day).
If switching focus → DA-W4 + DA-I2 are quick (40 min combined) and clear backlog.
If a new vertical's BDR-playbook content arrives → port it as Phase-2 vertical #4.

See `.claude/TASK.md` for the prioritized backlog.

## Velocity note

Today's session shipped 9 plan-phases that were estimated at 4.5 dev-days. The compression came from:
- Strong upfront plan (`tidy-beaming-pebble.md`) eliminated rework
- TDD discipline kept all 1,446 tests green throughout
- Brand-agnostic guardrail caught early prevented downstream rewrites
- Modular decoupling (Phase 1.1 + 1.2 ship as pure additions before Phase 1.3 integration) limited blast radius
