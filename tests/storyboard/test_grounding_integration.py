"""End-to-end grounding integration test (DA-S1 + DA-S4).

Why this exists
===============
Phase 1.1 — 1.7 each shipped well-unit-tested modules:

- ``problem_statements.py``     — the verbatim BDR pain-language library
- ``transcript_compactor.py``   — extractive 32K → ~10K compaction
- ``prompt_builders.py``        — the prompt-assembly chain with grounding hooks
- ``epiphan_presets.py``        — persona + product context

But there was no test exercising the full chain together. The failure mode the
unit tests can't see is **integration drift** — a refactor of one layer
silently breaking how it composes with the next. Examples that would have
slipped past unit tests:

- ``build_problem_statement_anchor`` returns the right block, but
  ``_build_transcript_prompt`` stops calling it after a refactor.
- A new persona is added to ``AudiencePersona`` enum but
  ``problem_statements`` still has no records keyed to it (silent grounding
  degradation — Phase-2 verticals are the worst case).
- The Frankenstack pattern block accidentally re-introduces a competitor
  brand name (Crestron / Extron / Q-SYS). Brand-agnosticism is a sales-rep
  contract, not a unit-tested invariant.

This module asserts the **full output of the prompt-assembly chain** against
realistic synthetic transcripts, with no LLM call required. It runs in <1s
in CI without API keys and catches every drift listed above.

Companion fixtures live in ``tests/fixtures/transcripts/`` — three synthetic
multi-speaker AV-pain transcripts, one per Phase-1 vertical with non-empty
problem-statement coverage (higher_ed, legal, live_events).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.storyboard.epiphan_presets import AudiencePersona
from src.tools.storyboard.problem_statements import get_problem_statements
from src.tools.storyboard.prompt_builders import build_extraction_prompt

# Project root anchored to this file so tests run from any cwd.
_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "transcripts"

# Phase-1 verticals with non-empty problem-statement coverage. Confirmed via
# ``get_problem_statements()`` returning >= 1 record. If a future change
# moves any of these into the empty-coverage bucket, the positive-path
# assertions in ``test_grounding_chain_injects_anchor`` will surface it.
GROUNDED_COMBOS = [
    pytest.param(
        "higher_ed",
        "av_director",
        "higher_ed_lecture_capture_synthetic.txt",
        id="higher_ed-av_director",
    ),
    pytest.param(
        "legal",
        "court_admin",
        "legal_court_recording_synthetic.txt",
        id="legal-court_admin",
    ),
    pytest.param(
        "live_events",
        "venue_manager",
        "live_events_venue_synthetic.txt",
        id="live_events-venue_manager",
    ),
]

# Brands the BDR team has explicitly committed to NOT name in prompts. The
# Phase-1.3 brand-agnosticism cleanup removed Crestron / Extron / Q-SYS from
# the Frankenstack block. If they reappear in the prompt, that's a
# regression of the brand-safety contract.
FORBIDDEN_BRAND_TOKENS = ["Crestron", "Extron", "Q-SYS"]

# Partner platforms the BDR team explicitly DOES name (Frankenstack reframe
# casts these as partners, not the broken layer). Their presence in the
# prompt is fine — we're not asserting against them.

# Tokens we expect to find in the assembled prompt for any (vertical,
# persona) combo with grounding coverage. These are stable structural
# headers that ``_build_transcript_prompt`` injects.
EXPECTED_PROMPT_HEADERS = [
    "VERBATIM PAIN LANGUAGE",  # from build_problem_statement_anchor
    "FRANKENSTACK DETECTION",  # from _FRANKENSTACK_PATTERN_BLOCK
]

# Personas declared in ``AudiencePersona`` that intentionally have no
# ``problem_statements`` records yet — i.e. defined for Phase-2 verticals or
# for prompt-routing only, with grounding planned later. The Phase-1.x work
# seeded statements for the personas NOT in this list. Adding a new persona:
#
#   1. Add it to ``AudiencePersona`` in ``epiphan_presets.py``.
#   2. EITHER seed at least one ``ProblemStatement`` referencing the new
#      persona in ``problem_statements.py`` AND remove it from this set,
#   3. OR add it to this set with a one-line rationale comment.
#
# ``test_every_persona_is_grounded_or_explicit_phase2`` enforces the choice.
# This makes Phase-2 backfill work visible in CI rather than landing as
# silent grounding-degradation in production.
PHASE_2_PERSONAS_NO_STATEMENTS_YET: set[str] = {
    AudiencePersona.LD_DIRECTOR.value,  # Phase-2 corporate L&D
    AudiencePersona.SIM_CENTER_DIRECTOR.value,  # Phase-2 healthcare
    AudiencePersona.CORP_COMMS.value,  # Phase-2 corporate
    AudiencePersona.EHS_MANAGER.value,  # Phase-2 industrial
    AudiencePersona.PROVOST.value,  # Phase-2 higher-ed exec layer
    AudiencePersona.UNIVERSITY_PRESIDENT.value,  # Phase-2 higher-ed exec layer
    AudiencePersona.UNIVERSITY_FINANCE.value,  # Phase-2 higher-ed exec layer
    AudiencePersona.DEALER_DAVE.value,  # Phase-2 channel
}

# Verticals checked when computing per-persona coverage. Updated in lockstep
# with ``epiphan_presets.AudiencePersona`` and ``demo._dropdowns.Vertical``.
ALL_VERTICALS = [
    "higher_ed",
    "legal",
    "live_events",
    "corporate",
    "government",
    "healthcare",
    "houses_of_worship",
    "industrial",
    "ux_research",
    "k12",
    "broadcasting",
]


def _read_fixture(filename: str) -> str:
    path = _FIXTURE_DIR / filename
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Positive path — grounding chain fires end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("vertical", "persona", "fixture"), GROUNDED_COMBOS)
def test_grounding_chain_injects_anchor(
    vertical: str, persona: str, fixture: str
) -> None:
    """For each (vertical, persona) with statements, the full prompt must contain
    the verbatim BDR-validated pain language as a structural anchor.

    This is the most important integration assertion in the suite — it proves
    the chain ``get_problem_statements → build_problem_statement_anchor →
    _build_transcript_prompt`` actually composes. If anyone refactors a layer
    and forgets to wire the anchor, this fails.
    """
    transcript = _read_fixture(fixture)

    # Step 1 (independent verification): the data layer has records.
    statements = get_problem_statements(vertical=vertical, persona=persona, limit=3)
    assert statements, (
        f"Precondition broken: ({vertical!r}, {persona!r}) has no problem "
        "statements. Either fixture choice is wrong or the data layer "
        "regressed."
    )

    # Step 2: assemble the full transcript prompt the way the unified
    # storyboard tool does in production.
    prompt = build_extraction_prompt(
        content_type="transcript",
        audience=persona,
        vertical=vertical,
        content=transcript,
    )

    # Step 3: the anchor block fired and carries the verbatim BDR language.
    for header in EXPECTED_PROMPT_HEADERS:
        assert header in prompt, (
            f"Prompt missing structural header {header!r} for "
            f"({vertical!r}, {persona!r}). The chain "
            f"{persona}→problem_statements→prompt_builder isn't composing. "
            "Inspect _build_transcript_prompt for the anchor injection."
        )

    # Step 4: at least one verbatim statement appears in the prompt. We use
    # the first 40 chars of the first statement (long enough to be unique,
    # short enough to be robust to whitespace re-flow).
    first_anchor = statements[0].statement[:40]
    assert first_anchor in prompt, (
        f"Prompt does not contain the verbatim opener {first_anchor!r} "
        f"from ({vertical!r}, {persona!r}). The anchor block fired but "
        "the content is wrong."
    )


# ---------------------------------------------------------------------------
# Negative path — graceful degradation on Phase-2 verticals
# ---------------------------------------------------------------------------


def test_grounding_chain_graceful_when_no_statements() -> None:
    """Phase-2 verticals (Government, K-12, etc.) have no problem statements
    yet. The chain must NOT raise and must NOT inject a malformed anchor —
    it should silently emit an empty anchor block and the rest of the prompt
    must still be well-formed.

    This guards against a future change that turns the graceful degradation
    in ``build_problem_statement_anchor`` into a hard failure for unseeded
    verticals — which would block Phase-2 demo traffic.
    """
    # Government / av_director currently has zero statements (confirmed by
    # the Backlog DA-R2 entry: Phase-2 verticals silently degrade).
    transcript = _read_fixture("higher_ed_lecture_capture_synthetic.txt")

    prompt = build_extraction_prompt(
        content_type="transcript",
        audience="av_director",
        vertical="government",
        content=transcript,
    )

    # The prompt must still assemble — no exception, non-empty.
    assert len(prompt) > 1000, "Prompt collapsed when grounding was empty."

    # The anchor header must NOT appear (anchor block was empty, so the
    # builder shouldn't have rendered the header). This catches a regression
    # where someone hardcodes the header outside the conditional.
    assert "VERBATIM PAIN LANGUAGE" not in prompt, (
        "VERBATIM PAIN LANGUAGE header rendered for a vertical with zero "
        "statements. The graceful-degradation path is leaking the header."
    )

    # Frankenstack block is global, so it should still appear.
    assert "FRANKENSTACK DETECTION" in prompt, (
        "Frankenstack block went missing for a Phase-2 vertical. The block "
        "is supposed to be vertical-independent."
    )


# ---------------------------------------------------------------------------
# Brand-agnosticism contract — no Crestron / Extron / Q-SYS in prompts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("vertical", "persona", "fixture"), GROUNDED_COMBOS)
def test_prompt_does_not_name_forbidden_brands(
    vertical: str, persona: str, fixture: str
) -> None:
    """Phase-1.3 cleanup (commit 06ef8e6) removed Crestron / Extron / Q-SYS
    from the Frankenstack pattern block. If they re-appear in the assembled
    prompt for any Phase-1 (vertical, persona, fixture) combo, the BDR-team
    brand-safety contract has regressed.

    LMS / CMS partners (Panopto, Kaltura, YuJa, Echo360, Canvas, Blackboard,
    Moodle, Zoom, Teams, WebEx) ARE allowed — they're explicitly framed as
    partners, not the broken layer. We don't assert against them.
    """
    transcript = _read_fixture(fixture)

    prompt = build_extraction_prompt(
        content_type="transcript",
        audience=persona,
        vertical=vertical,
        content=transcript,
    )

    # Strip the literal transcript content — we control it and we know it
    # doesn't name forbidden brands. We're checking what the BUILDER added.
    builder_added = prompt.replace(transcript, "")

    leaks = [b for b in FORBIDDEN_BRAND_TOKENS if b in builder_added]
    assert not leaks, (
        f"Brand-agnosticism contract broken: prompt builder injected "
        f"{leaks!r} into the prompt for ({vertical!r}, {persona!r}). "
        "See commit 06ef8e6 (Phase 1.3 brand-name cleanup)."
    )


# ---------------------------------------------------------------------------
# Persona context — the persona's name and value-angle make it through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("vertical", "persona", "fixture"), GROUNDED_COMBOS)
def test_prompt_carries_persona_signal(
    vertical: str, persona: str, fixture: str
) -> None:
    """The assembled prompt must clearly identify the target persona somewhere
    so the LLM can tailor extraction to their language. Stripping the
    persona signal accidentally is a silent quality regression.

    We strip the transcript before checking so a fixture that happens to
    mention the persona enum value verbatim can't false-positive. The
    builder must inject the signal independently of the input.
    """
    transcript = _read_fixture(fixture)

    prompt = build_extraction_prompt(
        content_type="transcript",
        audience=persona,
        vertical=vertical,
        content=transcript,
    )

    builder_added = prompt.replace(transcript, "")
    assert persona in builder_added, (
        f"Prompt for ({vertical!r}, {persona!r}) does not name the persona "
        "in builder-added content. The persona-conditional logic in "
        "build_extraction_prompt is no longer routing through to the output."
    )


# ---------------------------------------------------------------------------
# Fixture sanity — make sure we haven't accidentally shipped a transcript
# that itself violates the brand-agnosticism contract or is empty.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Coverage gate — every persona must be grounded or explicitly Phase-2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "persona",
    [pytest.param(p.value, id=p.value) for p in AudiencePersona],
)
def test_every_persona_is_grounded_or_explicit_phase2(persona: str) -> None:
    """For every member of ``AudiencePersona``, at least one (vertical,
    persona) combo must return non-empty problem statements OR the persona
    must be in ``PHASE_2_PERSONAS_NO_STATEMENTS_YET``.

    This closes the silent-degradation gap where adding a new persona to the
    enum without seeding statements lands them in the same Phase-2 bucket as
    Government/K-12 verticals — they get routed through the prompt builder
    but the anchor block silently emits "" and quality drops with no CI
    signal. Now the choice is explicit: seed statements OR document the
    deferral in the allowlist.

    This is the test Observer Fix B flagged as the missing leverage gate.
    """
    coverage = sum(
        len(get_problem_statements(vertical=v, persona=persona, limit=1))
        for v in ALL_VERTICALS
    )

    if persona in PHASE_2_PERSONAS_NO_STATEMENTS_YET:
        # Allowlisted as intentional deferral. If statements are added later,
        # remove the entry from the allowlist (the next assertion will catch
        # the inconsistency).
        if coverage > 0:
            pytest.fail(
                f"Persona {persona!r} is in PHASE_2_PERSONAS_NO_STATEMENTS_YET "
                f"but has {coverage} problem statements. Remove it from the "
                "allowlist now that grounding exists."
            )
        return

    assert coverage > 0, (
        f"Persona {persona!r} has zero problem statements across all "
        f"{len(ALL_VERTICALS)} verticals AND is not in the "
        "PHASE_2_PERSONAS_NO_STATEMENTS_YET allowlist. Either seed at least "
        "one ProblemStatement in src/tools/storyboard/problem_statements.py "
        "or add the persona to the allowlist with a rationale comment."
    )


# ---------------------------------------------------------------------------
# Fixture sanity — make sure we haven't accidentally shipped a transcript
# that itself violates the brand-agnosticism contract or is empty.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    [
        "higher_ed_lecture_capture_synthetic.txt",
        "legal_court_recording_synthetic.txt",
        "live_events_venue_synthetic.txt",
    ],
)
def test_fixture_is_realistic_and_clean(fixture: str) -> None:
    """The fixtures themselves should be substantial multi-speaker transcripts
    with realistic structure. They should NOT name forbidden brands (the
    point is to test the BUILDER, not to test our ability to scrub inputs)
    and they should be long enough to feel like a real call.
    """
    text = _read_fixture(fixture)
    assert len(text) > 1500, f"Fixture {fixture} is too short to be realistic."
    assert "[" in text, f"Fixture {fixture} has no timestamp markers."
    for token in FORBIDDEN_BRAND_TOKENS:
        assert token not in text, (
            f"Fixture {fixture} names a forbidden brand {token!r}. "
            "Rewrite the synthetic transcript to use Frankenstack-style "
            "language instead (see existing fixtures for examples)."
        )
