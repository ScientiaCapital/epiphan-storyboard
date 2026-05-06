# Project Context: epiphan-storyboard

**Generated:** 2026-05-05 (end-of-day)
**Branch:** main @ 85ecf13
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

---

## Today's Work (2026-05-05)

- **`b1d5789` fix(demo): sync schema with 9930fad UI options + render 422 errors**
  - Added `"blueprint"` to `visual_style` Literal and `"broadcasting"` to `vertical` Literal in `src/demo/router.py` — these were added to the dropdowns in commit `9930fad` but never to the backend schema, causing every Blueprint generation request to return HTTP 422.
  - Refactored `extractErrorMessage` + the fetch error path in `static/demo.html` to render FastAPI 422 detail arrays as readable strings (was producing the literal text `[object Object]`).
  - Added 3 regression tests in `tests/demo/test_router.py` that fail-loud if the dropdowns drift from the schema again.
  - Verified end-to-end against production: HTTP 200 + real PNG returned.
- **`85ecf13` chore: end-of-day 2026-05-05 — backlog + observer archive**

## Recent Commits

```
85ecf13 chore: end-of-day 2026-05-05 — backlog + observer archive
b1d5789 fix(demo): sync schema with 9930fad UI options + render 422 errors
4ec0969 chore: update PROJECT_CONTEXT.md for end-of-day 2026-05-05
9930fad feat: add Broadcasting vertical, blueprint style, Frida Kahlo + Siqueiros artists
c544c4b feat: JTBD + Challenger + NSTTD sales frameworks, AV Integrator persona, meeting recap, quality gate
```

## Working Tree Status

```
clean — main pushed to origin/main, no worktrees
```

---

## Tomorrow

**Recommended next:** verify `av_integrator` is in the `audience` Literal in `src/demo/router.py` (Backlog item — same regression class as today's bug, 5-minute fix). Then consider the SSOT-for-dropdowns refactor (Backlog, ~1–2 hr) which would prevent this entire defect class permanently.

**Skill:** `feature-dev` for the SSOT refactor; just an `Edit` for the audience audit.

**Estimated cost:** $1–3 for the 5-minute fix; $5–10 for the SSOT refactor.

**Top unresolved observer/backlog flag:** None active — observers were not run this session. Highest-leverage backlog item is the SSOT refactor (medium impact, prevents recurrence of today's bug class).

---

_Auto-updated by /end workflow._
