# Planning — epiphan-storyboard

**Last updated:** 2026-05-08 (end of day)

## Production state

`https://epiphan-storyboard.vercel.app` — main-aligned deploy, four releases live:

| Tag | What |
|---|---|
| `v1.0-bdr-workflow` | Phase 1 BDR Discovery Workflow (2026-05-07) |
| `v1.1-leverage-day` | SSOT for demo dropdowns + grounding integration test (2026-05-08 AM) |
| `v1.2-two-pass-extraction` | DA-R1 — narrative+schema two-pass in storyboard pipeline (2026-05-08 PM) |
| `v1.3-meeting-recap-unblock` | DA-R1.1 — wire two-pass into meeting-recap + 3 bundled bug fixes (2026-05-08 late PM) |

## Active sprint: cleanup + polish

After today's two-pass push, the natural next moves are short hygiene fixes that close out the threads we opened:

1. **DA-R1.1.a** — `two_pass_applied` flag visibility (10 min)
2. **DA-A3** — consolidate the duplicate text-path dispatch + duplicate two-pass trigger condition into a `_should_two_pass(content, config)` helper (30 min)
3. **DA-A1** — `ArtistStyle.NONE` dual-nullability cleanup (30 min)
4. **DA-A2** — migrate demo HTML to fetch `/demo/options` (1 hr) — closes the SSOT loop from Fix A

Total: ~2 hr. Leaves the codebase clean for Phase 2.

## Tomorrow's lead

**DA-R1.1.a + DA-A3** as a paired sprint (~40 min). Both are direct follow-ups to today's two-pass work, so context cost is minimal. Use the same skill stack: `brainstorming` (briefly — both decisions are narrow) → `agent-teams` (Builder + Observer, lightweight) → TDD red→green → ship.

If energy is high, stack **DA-S3** (Vertical-aware Frankenstack blocks) — that's a real product-quality lift, ~1 hr more.

## Phase 2 (multi-day)

When ready to push past hygiene:

- **Survey expansion** — 6 more verticals (Government, Corporate AV, Healthcare, Houses of Worship, K-12, Channel)
- **HubSpot webhook** — auto-attach BDR brief to contact record on creation
- **Persistence** — Supabase or Redis backing for survey responses + meeting recaps (currently in-memory)
- **Real Clari/Gong fixtures** — anonymize 1 transcript per vertical to replace synthetic ones (DA-S4 polish)

## Velocity notes

- 2026-05-07: Phase 1 — 9 plan-phases, ~4.5 dev-day estimate, compressed to 1 session via TDD + parallel subagent execution.
- 2026-05-08: Two leveraged debt-class kills (Fix A + Fix B) + DA-R1 + DA-R1.1 + 3 surface bug fixes. 10 commits, 4 prod releases, all live verified. Effective 2 dev-days of work.
- Pattern: brainstorm-first locks decisions early; TDD prevents rework; observer gates catch class-of-debt issues at PR-time not days later.
