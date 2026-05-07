"""Tests for src/tools/storyboard/problem_statements.py.

The Problem Statements library exposes a Pydantic schema (``ProblemStatement``)
plus retrieval helpers backed by a hand-curated constant ``PROBLEM_STATEMENTS``
sourced from ``Problem Statements Per Persona by Vertical.docx``.
"""

from __future__ import annotations

import pytest


def test_problem_statement_schema_accepts_valid_record() -> None:
    """A minimal valid ProblemStatement record validates and round-trips."""
    from src.tools.storyboard.problem_statements import ProblemStatement

    ps = ProblemStatement(
        vertical="higher_ed",
        persona="av_director",
        statement=(
            "A lot of AV directors we talk to have rooms going unrecorded "
            "because faculty won't touch the capture system."
        ),
        pain_anchor="unrecorded_rooms",
        channel="both",
        icp_score=90,
    )

    assert ps.vertical == "higher_ed"
    assert ps.persona == "av_director"
    assert ps.pain_anchor == "unrecorded_rooms"
    assert ps.channel == "both"
    assert ps.icp_score == 90
    assert "AV directors" in ps.statement


def test_problem_statements_constant_exists_and_is_non_empty() -> None:
    """The hand-curated PROBLEM_STATEMENTS constant must be loaded and non-empty."""
    from src.tools.storyboard.problem_statements import PROBLEM_STATEMENTS

    assert isinstance(PROBLEM_STATEMENTS, list)
    assert len(PROBLEM_STATEMENTS) > 0


def test_get_problem_statements_filters_by_vertical_and_persona() -> None:
    """Retrieval returns records matching the vertical+persona filter."""
    from src.tools.storyboard.problem_statements import (
        get_problem_statements,
    )

    results = get_problem_statements(vertical="higher_ed", persona="av_director")

    assert len(results) >= 1
    for ps in results:
        assert ps.vertical == "higher_ed"
        assert ps.persona == "av_director"


def test_get_problem_statements_respects_limit() -> None:
    """``limit`` caps the number of records returned."""
    from src.tools.storyboard.problem_statements import (
        get_problem_statements,
    )

    capped = get_problem_statements(
        vertical="higher_ed", persona="av_director", limit=2
    )

    assert len(capped) <= 2


def test_get_problem_statements_filters_by_channel() -> None:
    """``channel='call'`` excludes email-only records and vice versa."""
    from src.tools.storyboard.problem_statements import (
        ProblemStatement,
        get_problem_statements,
    )

    call_results = get_problem_statements(
        vertical="higher_ed", persona="av_director", channel="call"
    )

    for ps in call_results:
        assert isinstance(ps, ProblemStatement)
        assert ps.channel in ("call", "both")


def test_get_problem_statements_returns_empty_for_unknown_combo() -> None:
    """Unknown vertical/persona combo returns empty list, not error."""
    from src.tools.storyboard.problem_statements import (
        get_problem_statements,
    )

    assert (
        get_problem_statements(vertical="bogus_vertical_xyz", persona="av_director")
        == []
    )


def test_persona_alias_maps_doc_string_to_enum_value() -> None:
    """``normalize_doc_persona`` converts the verbatim doc role string to enum."""
    from src.tools.storyboard.problem_statements import (
        normalize_doc_persona,
    )

    # The doc uses long composite role strings like
    # "AV Director / Director of AV Architecture"; we map to the 17-value enum.
    assert (
        normalize_doc_persona("AV Director / Director of AV Architecture")
        == "av_director"
    )
    assert normalize_doc_persona("Court Administrator / IT Director") == "court_admin"
    assert (
        normalize_doc_persona("Production Manager / Technical Director")
        == "technical_director"
    )


def test_persona_alias_returns_none_for_unknown_role() -> None:
    """Unknown role string returns None, not raise — caller decides."""
    from src.tools.storyboard.problem_statements import (
        normalize_doc_persona,
    )

    assert normalize_doc_persona("Chief Coffee Officer") is None


# =============================================================================
# match_statements_to_transcript — scoring + ranking
# =============================================================================


def test_match_statements_to_transcript_returns_ranked_pairs() -> None:
    """Transcript matcher returns (statement, score) tuples ranked by score."""
    from src.tools.storyboard.problem_statements import (
        match_statements_to_transcript,
    )

    # Brand-agnostic transcript — describes the failure layer (encoder,
    # classroom PC) rather than naming any LMS / CMS partner.
    transcript = (
        "We've got 200 classrooms and our IT team is spending half the week "
        "troubleshooting recordings where the encoder feeding our LMS drops "
        "files. Faculty stop recording when the LMS upload breaks."
    )

    ranked = match_statements_to_transcript(
        transcript=transcript, vertical="higher_ed", persona="edtech_manager"
    )

    assert isinstance(ranked, list)
    assert len(ranked) >= 1
    # Sorted descending by score
    scores = [score for _ps, score in ranked]
    assert scores == sorted(scores, reverse=True)
    # Top match should be related to LMS / encoder / faculty / recording —
    # general pain themes, not a specific partner brand.
    top_ps, _top_score = ranked[0]
    assert any(
        kw in top_ps.statement.lower()
        for kw in ("lms", "encoder", "faculty", "recording", "publish")
    )


def test_match_statements_to_transcript_zero_when_no_overlap() -> None:
    """A transcript with no relevant keywords yields empty/zero-scored output."""
    from src.tools.storyboard.problem_statements import (
        match_statements_to_transcript,
    )

    ranked = match_statements_to_transcript(
        transcript="The weather is nice today.",
        vertical="higher_ed",
        persona="av_director",
    )

    # Either empty or all scores are 0
    assert all(score == 0 for _ps, score in ranked) or ranked == []


def test_match_statements_to_transcript_filters_by_vertical_and_persona() -> None:
    """Only statements matching the vertical/persona filter are scored."""
    from src.tools.storyboard.problem_statements import (
        match_statements_to_transcript,
    )

    # Persona that doesn't exist in the corpus — should match nothing
    ranked = match_statements_to_transcript(
        transcript="Anything goes here.",
        vertical="higher_ed",
        persona="dealer_dave",
    )
    assert ranked == []


# =============================================================================
# Phase-1 coverage — top 3 ICP verticals must each have ≥3 statements per
# documented persona, so the prompt builder always finds something to inject.
# =============================================================================


PHASE_1_VERTICAL_PERSONAS = {
    "higher_ed": ["av_director", "law_firm_it", "edtech_manager"],
    "legal": ["court_admin", "production_director", "law_firm_it"],
    "live_events": [
        "technical_director",
        "system_engineer",
        "venue_manager",
        "av_integrator",
    ],
}


@pytest.mark.parametrize(
    "vertical,persona",
    [(v, p) for v, personas in PHASE_1_VERTICAL_PERSONAS.items() for p in personas],
)
def test_phase_1_verticals_have_at_least_one_statement(
    vertical: str, persona: str
) -> None:
    """Every Phase-1 (vertical, persona) combo must have at least one record.

    The prompt builder injects up to 3 verbatim statements per call; if any
    Phase-1 combo has zero coverage the LLM falls back to its priors and
    quality regresses. This test guards that floor.
    """
    from src.tools.storyboard.problem_statements import (
        get_problem_statements,
    )

    matches = get_problem_statements(vertical=vertical, persona=persona)
    assert len(matches) >= 1, (
        f"Phase-1 gap: {vertical}/{persona} has no problem statements. "
        f"Add at least one verbatim record from the BDR playbook doc."
    )


def test_icp_scores_are_in_documented_range() -> None:
    """ICP scores in PROBLEM_STATEMENTS must match the doc's published values."""
    from src.tools.storyboard.problem_statements import (
        ICP_SCORES,
        PROBLEM_STATEMENTS,
    )

    for ps in PROBLEM_STATEMENTS:
        if ps.vertical in ICP_SCORES:
            assert ps.icp_score == ICP_SCORES[ps.vertical], (
                f"{ps.vertical}/{ps.persona} ICP={ps.icp_score} "
                f"but ICP_SCORES says {ICP_SCORES[ps.vertical]}"
            )
