# Observer: Code Quality Report

**Date:** 2026-05-08
**Session:** leverage-day Fix A (SSOT demo dropdowns)
**Project:** epiphan-storyboard
**Observer Model:** claude-sonnet-4-6

---

## Critical (must fix before merge)

None.

---

## Warnings (fix or log to backlog)

**[WARNING] — src/demo/router.py:431 — ArtistStyle.NONE passes truthy string "none" to tool layer**

With `use_enum_values=True`, `ArtistStyle.NONE` becomes the plain string `"none"` at runtime. The guard on line 431 (`if request.artist_style:`) evaluates `"none"` as truthy, so it is injected into `tool_args` and forwarded to `unified_storyboard.run()`. Downstream, `prompts.get_artist_style_instructions("none")` does `artists.get("none", "")` — since `"none"` is not a dict key, it returns `""` and is harmless. But the intent (no overlay) leaks an unnecessary key into `tool_args` every time the user selects "None" in the UI.

Suggested fix: Either (a) normalize at the router boundary — `if request.artist_style and request.artist_style != "none":` — or (b) keep `artist_style: ArtistStyle | None = None` in `GenerateRequest` and treat `NONE` as a UI-only sentinel that maps to Python `None` in a validator (`@field_validator`). Option (b) is cleaner and removes the dual-nullability ambiguity (`None` vs `"none"`).

---

**[WARNING] — tests/demo/test_dropdown_parity.py:51 — HTML path is relative, not anchored**

`Path("static/demo.html").read_text()` uses a relative path. If pytest is invoked from a directory other than the project root, the test silently returns `set()` (see the helper's fallback), and the assertion `html_values == ssot_values` becomes `set() == ssot_values`, which fails loudly — but with a confusing error message rather than a clear "file not found." Better to anchor: `Path(__file__).parents[2] / "static" / "demo.html"`.

---

## Info (nice to have)

**[INFO] — src/demo/_dropdowns.py — optgroup labels are not tested**

The `Option.group` field (e.g., "ATL — Decision Makers", "CHANNEL — Partners") is display metadata that lives only in `_dropdowns.py` and is replicated as `<optgroup label="...">` in `static/demo.html`. The parity tests guard `<option value>` but not `<optgroup label>`. If an optgroup label changes in the HTML, no test fails. Low risk (labels are cosmetic), but worth noting as an untested surface.

**[INFO] — No new TODO/FIXME/HACK/XXX/TEMP markers introduced**

Zero tech-debt markers found in the three changed files (`src/demo/router.py`, `src/demo/_dropdowns.py`, `tests/demo/test_dropdown_parity.py`). The existing `# NEW ARTIST STYLE` and `# MX/LATAM ARTIST STYLES` comments in `src/tools/storyboard/prompts.py` pre-date this change.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned | 5 (router.py, _dropdowns.py, test_dropdown_parity.py, prompts.py, unified_storyboard.py) |
| Critical findings | 0 |
| Warnings | 2 |
| Info items | 2 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1-1.3 | 6 | 7 (0C/4W/3I) | archived to .claude/archive/2026-05-07-OBSERVER-QUALITY.md |
| 2026-05-08 | leverage-day Fix A (SSOT demo dropdowns) | Read-only audit of GenerateRequest SSOT refactor | 5 | 4 (0C/2W/2I) | OPEN |
