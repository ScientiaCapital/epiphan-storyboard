# Planning — epiphan-storyboard

**Last updated:** 2026-06-12 (end of day)

## Production state

`https://epiphan-storyboard.vercel.app` — main-aligned deploy, smoke-verified:

| Tag / commit | What |
|---|---|
| `v1.0-bdr-workflow` | Phase 1 BDR Discovery Workflow (2026-05-07) |
| `v1.1-leverage-day` | SSOT for demo dropdowns + grounding integration test (2026-05-08 AM) |
| `v1.2-two-pass-extraction` | DA-R1 — narrative+schema two-pass in storyboard pipeline (2026-05-08 PM) |
| `v1.3-meeting-recap-unblock` | DA-R1.1 — wire two-pass into meeting-recap + 3 bundled bug fixes (2026-05-08 late PM) |
| `177b539` (untagged) | Demo brand re-skin + storyboard card + timeout mitigations + Söhne font proxy (2026-06-10) |
| `7137314` (untagged) | Debt-paydown sprint: fonts hardening, two-pass trigger SSOT, two_pass_applied exposure, vercel config truth (2026-06-12) |

## Active sprint: remaining hygiene + Phase 2 prep

DA-R1.1.a and DA-A3 are **DONE** (2026-06-12). Remaining, in priority order:

1. **DA-R2** — Phase-2 vertical degradation visibility (30 min, MEDIUM — highest-impact open item)
2. **DA-A2** — migrate demo HTML to fetch `/demo/options` (1 hr) — closes the SSOT loop; would also have prevented the emoji drift fixed today (DA-A4)
3. **DA-A1** — `ArtistStyle.NONE` dual-nullability cleanup (30 min)
4. **DA-B2** — 15-min manual repro of the html2canvas gradient-blank risk before deciding on a fix

## Tomorrow's lead

**DA-R2 + DA-A2** (~1.5 hr): DA-R2 is the only medium-impact item left (silent quality degradation when users pick Phase-2 verticals), and DA-A2 kills the last dropdown-drift surface. Stack DA-A1 if energy is high. Same stack: TDD red→green → observer signoff → single deploy + smoke.

## Phase 2 (multi-day)

When ready to push past hygiene:

- **Survey expansion** — 6 more verticals (Government, Corporate AV, Healthcare, Houses of Worship, K-12, Channel)
- **HubSpot webhook** — auto-attach BDR brief to contact record on creation
- **Persistence** — Supabase or Redis backing for survey responses + meeting recaps (currently in-memory)
- **Real Clari/Gong fixtures** — anonymize 1 transcript per vertical to replace synthetic ones (DA-S4 polish)

## Velocity notes

- 2026-05-07: Phase 1 — 9 plan-phases, ~4.5 dev-day estimate, compressed to 1 session via TDD + parallel subagent execution.
- 2026-05-08: Two leveraged debt-class kills (Fix A + Fix B) + DA-R1 + DA-R1.1 + 3 surface bug fixes. 10 commits, 4 prod releases, all live verified. Effective 2 dev-days of work.
- 2026-06-12: The "~2 hr" cleanup sprint planned 05-08 executed on estimate — but only after a stale-docs catch-up phase, because the 06-10 session skipped /end. **Cost of a skipped /end ≈ 30 min of state reconstruction next session.** Also: a retroactive observer audit found 1C/3R the day-of audit would have caught at commit time.
- Pattern: brainstorm-first locks decisions early; TDD prevents rework; observer gates catch class-of-debt issues at PR-time not days later.
