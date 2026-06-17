# Active Tasks

**Updated:** 2026-06-17 (/end — product-grounded image gen + Pearl Duo shipped)

## Today's sprint (2026-06-17, approved) — 2 PRs, 6 commits, both deployed

1. ✅ **Product-grounded, reference-aware image generation** (PR #1, `4e5658c`). Three relevance fixes + a tech-accuracy gate, built via a 3-agent team:
   - `recommended_products` field added to `StoryboardUnderstanding` (it was silently dropped on parse — also reactivated already-waiting reads in `quality_gate.py` + `demo/router.py`).
   - New `product_visual_specs.py` SSOT (verbatim Epiphan Knowledge MCP truth for 6 core products) injected into the image prompt so generated images depict the real hardware.
   - Image-to-image: uploaded reference photos now condition generation on both genai + OpenRouter paths (mime-sniffed).
   - New technical-accuracy quality gate (`find_tech_accuracy_violations`) flags false product claims with a one-shot corrective retry sharing the competitor gate's budget.
2. ✅ **Pearl Duo** (PR #2, `d60516d`) — new dual-channel product (InfoComm "Agent-ready AV" booth; ships Dec 2026) added to catalog + visual SSOT, wired into live_events/corporate/government/houses_of_worship, with tech-accuracy guards for its "no CMS/lecture-capture" boundary. PR #2 also **recovered the PR#1 observer fixes that `gh pr merge` dropped** at the pre-fix head (cherry-picked).

**Tests:** 1,600 → **1,658** (+58). mypy 372 baseline (0 new). gitleaks: no leaks.
**Deploy:** both live on https://epiphan-storyboard.vercel.app — /health 200, /demo/options 200.
**Observers:** 0 blockers across both PRs; all fixable RISK/WARNING items fixed in-sprint, INFO items → Backlog (DA-IMG1-3, DA-PD1-4).

---

## Sprint (2026-06-13, approved)

1. ✅ **Competitor-as-hero quality gate fix** (commit `4a801e5`, merged to main ff) — a Sony-focused source had produced an Epiphan-branded card *selling Sony*. Root causes fixed: (a) `run_quality_gate()` was dead code → now wired into `UnifiedStoryboardTool` with a one-shot corrective reframe retry; (b) all 4 extraction prompts now carry `_COMPETITOR_RULES_BLOCK` (competitor = before-state only) + `corrective_instruction` threaded through `gemini_client`; (c) `COMPETITOR_TOKENS` SSOT in `epiphan_presets.py` (28 vendors, CMS/LMS publish partners excluded) replaces the 4-name list; field-aware (hero=critical, contrast=allowed). Plus brand-voice check (hype words/exclamations), role-aware personal-name fix, demo copy polish (Production/Technical Director labels, "Who it's for", footer → THK ProAV). Tests **1,574 → 1,600** (+26). Quality report surfaced through `/demo/generate` → demo UI banner. See memory `competitor-as-hero-gate.md`.

**Deploy:** force-redeployed to https://epiphan-storyboard.vercel.app on 2026-06-13.

---

## Sprint (2026-06-12, approved)

1. ✅ State sync catch-up (commit `a1df5d0`)
2. ✅ fonts.py hardening: status-vs-network error granularity + per-key asyncio.Lock + 8 new tests (commit `3187555` — cleared audit CRITICAL + cache-race RISK + test-gap WARNING)
3. ✅ DA-A3 (expanded ×3): `should_run_two_pass()` SSOT + demo cap derived from config + text-path dispatch collapsed into `_call_text_model` (commit `8d74e24`, 7 new tests, mypy −1)
4. ✅ DA-R1.1.a: `two_pass_applied: bool = False` on `MeetingRecapResponse` (commit `92ff4c8`)
5. ✅ Vercel verification: plan=Pro, applied lambda = timeout 300 / memory 2048 — maxDuration IS honored (audit RISK cleared as non-issue); vercel.json memory set to actual 2048 (commit `7137314`). Deployed + smoke-verified.
6. ✅ (stretch) SSOT emoji/label sync (commit `6544dd7`, DA-A4 closed)

**Deploy:** all 6 commits live on https://epiphan-storyboard.vercel.app — /health 200, /demo/options shows synced labels + 17 personas, font proxy 200 font/otf (210KB) / 404 unknown key, /demo/generate 422 enum guard intact. Tests 1,548 → 1,574.

## Completed 2026-06-10 (session never closed via /end — reconstructed 2026-06-12)

- ✅ Demo brand re-skin + brand storyboard card with overlay text (commits `c5a4cb1`, `177b539`)
- ✅ /demo/generate timeout mitigation: vercel maxDuration 300 + live progress UI + 9K input cap (`23386f0`, `18e05ca`, `9236f4c`)
- ✅ Söhne font same-origin proxy `src/brand/fonts.py` (CORS workaround)
- ✅ meeting_recap: transcript compaction wired + low-confidence surfacing (inside `c5a4cb1`)
- ⚠️ Observer audit was skipped that day — run retroactively 2026-06-12: 1C/3W/2I quality, 0 blockers/3 risks/5 smells arch. See `.claude/observers/`.

## Completed 2026-05-08 (end of day)

- ✅ Fix A: SSOT for demo dropdowns — kills schema-drift bug class (commit `cc17762`)
- ✅ Fix B: End-to-end grounding integration test + 3 fixtures (commit `08e7344`)
- ✅ DA-R1: Wired two-pass narrative+schema Forces extraction into `gemini_client._understand` (commit `d1d62a6`, tag `v1.2-two-pass-extraction`)
- ✅ DA-R1.1: Wired two-pass into `meeting_recap.process_meeting_recap` (commit `2e27162`)
- ✅ DA-R1.1.b: Defensive parse + summary-list-to-string coercion (commit `ac4a7ac`, tag `v1.3-meeting-recap-unblock`)
- ✅ Bonus: surfaced + fixed three pre-existing prod bugs in `process_meeting_recap` that had been silently 500-ing the `/storyboard/meeting-recap` endpoint
- ✅ Live verified `POST /storyboard/meeting-recap` returns 200 with all fields populated (was 500 for weeks)

**Stats:** 10 commits, 3,192 insertions / 618 deletions, 1,540 → 1,548 tests (+8 net), 0 mypy delta (actually −1 from bug fix), endpoint reliability +∞% (0 → 100%).

## Active backlog (in `.claude/Backlog.md`, re-prioritized 2026-06-12 EOD)

| Priority | Item | Effort | Status |
|---|---|---|---|
| MEDIUM | **DA-R2**: Phase-2 vertical degradation visibility | 30 min | open since 2026-05-07 |
| LOW | **DA-A2**: Migrate `static/demo.html` to fetch `/demo/options` | 1 hr | would have prevented today's DA-A4 drift |
| LOW | **DA-A1**: Resolve `ArtistStyle` dual-nullability | 30 min | from 2026-05-08 |
| LOW | **DA-B2**: Repro html2canvas gradient-blank in PNG downloads | 15 min repro | NEW 2026-06-12 |
| LOW | **DA-B1**: fonts.py graceful degrade instead of 502 | 15 min | NEW 2026-06-12 |
| LOW | **DA-V1**: Integration test for maxDuration ↔ demo-cap coupling | 30 min | NEW 2026-06-12 |
| LOW | **DA-Q1**: Structured error codes on AgentSession | 1 hr | NEW 2026-06-12 |
| LOW | **DA-Q2**: `.strip()` sweep on remaining os.getenv callsites | 10 min | NEW 2026-06-12 |
| LOW | **DA-W2**: Tighten exception in `build_problem_statement_anchor` | 15 min | from 2026-05-07 |
| LOW | **DA-W4**: Edge-case tests for compactor | 30 min | from 2026-05-07 |
| LOW | **DA-I2**: Skip dup key_moments block | 10 min | from 2026-05-07 |
| LOW | **DA-W3 / S-2**: Phase-2 — extend `AudiencePersona` enum | 30 min | from 2026-05-07 |
| LOW | **DA-S3**: Vertical-aware Frankenstack blocks | 1 hr | from 2026-05-07 |
| LOW | **DA-R3**: Embedding fallback for compactor | 1 day | from 2026-05-07 |
| LOW | Vercel `/static/*` routing fix | 30 min | from 2026-05-07 |
| LOW | Pydantic Config → ConfigDict in gong/fireflies schemas | 15 min | from 2026-05-07 |
| LOW | Pre-existing mypy + integration test failures | unknown | from 2026-05-07 |

Closed 2026-06-12: ~~DA-R1.1.a~~ · ~~DA-A3~~ · ~~DA-A4~~ · ~~.gitleaksignore~~

## Tomorrow's recommended lead

**DA-R2 + DA-A2** (~1.5 hr) — DA-R2 is the only medium-impact item left (Phase-2 verticals silently degrade with no signal); DA-A2 kills the last dropdown-drift surface. Stack DA-A1 if energy is high.

## Phase 2 (sprint after this one)

- Surveys for the remaining 6 verticals (Government, Corporate AV, Healthcare, Houses of Worship, K-12, Channel/Integrators)
- Outbound HubSpot webhook to attach BDR brief to contact record
- Survey response persistence (Supabase / Redis)
