# Backlog

## Security / Tooling

- **Add `.gitleaksignore` for historical test fixtures** (effort: 5 min, impact: low)
  - Gitleaks flags `tests/api/test_connectors.py:499` (commit `fe25349`, 2026-02-19) for `"fireflies_api_key_123"` — a placeholder test string. The file has since been deleted from HEAD but remains in history.
  - Action: add a `.gitleaksignore` entry pinning that finding so future security gates pass cleanly without manual triage.
  - Logged: 2026-05-05

## Tech Debt / Architecture

- **Single-source-of-truth for demo dropdowns** (effort: 1–2 hr, impact: medium)
  - Today's `b1d5789` regression happened because `static/demo.html` and `src/demo/router.py` keep two parallel lists of `visual_style` / `vertical` / `audience` Literals. Adding an option to one without the other 422s.
  - Options: (a) generate the HTML `<option>` list from a JSON manifest the backend exposes via `/demo/options`, OR (b) generate both files from a single Python source (codegen). Option (a) is preferred — UI stays declarative, backend becomes the source of truth.
  - Logged: 2026-05-05

- **Vercel `/static/*` routing is dead** (effort: 30 min, impact: low until it bites)
  - `app.mount("/static", StaticFiles(directory="static"))` returns 404 under `@vercel/python`. Demo only works because `@app.get("/")` does `FileResponse("static/demo.html")`. Any future static asset (CSS/JS file) referenced by URL will 404.
  - Action: either inline all CSS/JS into `demo.html`, or migrate routing to `vercel.ts` with explicit rewrites.
  - Logged: 2026-05-05 (see memory: vercel-static-mount-broken.md)

- **`av_integrator` may be missing from `audience` Literal** (effort: 5 min, impact: low)
  - Memory says 17 personas including `av_integrator`. `src/demo/router.py` audience Literal lists ~16. Verify and add if missing — same regression class as the Blueprint bug.
  - Logged: 2026-05-05

## Quality

- **Pre-existing integration test failures** (effort: unknown, impact: low — flaky)
  - 7 tests in `tests/integration/test_full.py` fail with `session.status == FAILED` instead of `COMPLETED`. They hit live LLM APIs. Not blocking deploys but adds noise to CI.
  - Action: investigate whether these are flaky-by-design (live API), need credentials in CI env, or genuinely broken.
  - Logged: 2026-05-05

- **Pre-existing mypy errors** (effort: 1 hr, impact: low)
  - 58 mypy errors across 11 files (e.g., `src/demo/router.py:487` — `GenerateResponse` "missing named arguments" warning, but the fields have defaults). Not introduced today; predates this session.
  - Logged: 2026-05-05
