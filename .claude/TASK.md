# Active Tasks

**Updated:** 2026-05-08 (end of day)

## Completed today (2026-05-08)

- ✅ Fix A: SSOT for demo dropdowns — kills schema-drift bug class (commit `cc17762`)
- ✅ Fix B: End-to-end grounding integration test + 3 fixtures (commit `08e7344`)
- ✅ DA-R1: Wired two-pass narrative+schema Forces extraction into `gemini_client._understand` (commit `d1d62a6`, tag `v1.2-two-pass-extraction`)
- ✅ DA-R1.1: Wired two-pass into `meeting_recap.process_meeting_recap` (commit `2e27162`)
- ✅ DA-R1.1.b: Defensive parse + summary-list-to-string coercion (commit `ac4a7ac`, tag `v1.3-meeting-recap-unblock`)
- ✅ Bonus: surfaced + fixed three pre-existing prod bugs in `process_meeting_recap` that had been silently 500-ing the `/storyboard/meeting-recap` endpoint
- ✅ Live verified `POST /storyboard/meeting-recap` returns 200 with all fields populated (was 500 for weeks)

**Stats:** 10 commits, 3,192 insertions / 618 deletions, 1,540 → 1,548 tests (+8 net), 0 mypy delta (actually −1 from bug fix), endpoint reliability +∞% (0 → 100%).

## Active backlog (in `.claude/Backlog.md`, prioritized for tomorrow)

| Priority | Item | Effort | New today? |
|---|---|---|---|
| LOW | **DA-R1.1.a**: Decide `two_pass_applied` flag visibility | 10 min | ✅ |
| LOW | **DA-A3** (expanded): Consolidate text-path dispatch + two-pass trigger condition (`_should_two_pass` helper) | 30 min | ✅ |
| LOW | **DA-A1**: Resolve `ArtistStyle` dual-nullability | 30 min | from 2026-05-08 morning |
| LOW | **DA-A2**: Migrate `static/demo.html` to fetch `/demo/options` | 1 hr | from 2026-05-08 morning |
| MEDIUM | **DA-R2**: Phase-2 vertical degradation visibility | 30 min | from 2026-05-07 |
| LOW | **DA-W2**: Tighten exception in `build_problem_statement_anchor` | 15 min | from 2026-05-07 |
| LOW | **DA-W4**: Edge-case tests for compactor | 30 min | from 2026-05-07 |
| LOW | **DA-I2**: Skip dup key_moments block | 10 min | from 2026-05-07 |
| LOW | **DA-W3 / S-2**: Phase-2 — extend `AudiencePersona` enum | 30 min | from 2026-05-07 |
| LOW | **DA-S3**: Vertical-aware Frankenstack blocks | 1 hr | from 2026-05-07 |
| LOW | **DA-R3**: Embedding fallback for compactor | 1 day | from 2026-05-07 |
| LOW | `.gitleaksignore` for historical placeholder | 5 min | from 2026-05-05 |
| LOW | Vercel `/static/*` routing fix | 30 min | from 2026-05-07 |
| LOW | Pydantic Config → ConfigDict in gong/fireflies schemas | 15 min | from 2026-05-07 |
| LOW | Pre-existing mypy + integration test failures | unknown | from 2026-05-07 |

## Tomorrow's recommended lead

**DA-R1.1.a + DA-A3** — both quick (40 min combined), close out the threads opened by today's two-pass work, and get the codebase to a clean inflection point before the next feature push.

If user wants something bigger: **DA-S3** (Vertical-aware Frankenstack blocks, 1 hr) is a real product-quality win.

## Phase 2 (sprint after this one)

- Surveys for the remaining 6 verticals (Government, Corporate AV, Healthcare, Houses of Worship, K-12, Channel/Integrators)
- Outbound HubSpot webhook to attach BDR brief to contact record
- Survey response persistence (Supabase / Redis)
