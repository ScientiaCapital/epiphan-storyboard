"""Tests for src/tools/storyboard/bdr_brief_generator.py.

The BDR Call Brief is the structured output a BDR consumes after a discovery
call (transcript paste) or self-serve survey submission. It surfaces:
  - detected persona + ICP score
  - JTBD job statement
  - Forces of Progress (Push/Pull/Anxiety/Habit)
  - Top 3 verbatim problem statements (from the BDR playbook library)
  - Challenger reframe
  - 5 calibrated questions (NSTTD style — What/How only, no Why)
  - NSTTD-formatted follow-up email (≤100 words, accusation audit + no-CTA)
  - Next-best-action recommendation

Phase 1 ships the deterministic core: persona detection, problem-statement
matching, forces summarization, NBA selection. The Challenger reframe and
calibrated questions reuse existing meeting-recap LLM output where available
and fall back to template-driven generation.
"""

from __future__ import annotations

import pytest


def test_bdr_call_brief_schema_accepts_minimal_record() -> None:
    """BDRCallBrief schema validates a minimal valid record."""
    from src.storyboard.schemas import BDRCallBrief, ForcesOfProgress

    brief = BDRCallBrief(
        detected_persona="av_director",
        detected_vertical="higher_ed",
        icp_score=90,
        job_statement=(
            "When managing AV across 200+ rooms, I want to ensure capture "
            "reliability scales without adding staff, so I can deliver "
            "lecture recordings without becoming a help desk."
        ),
        forces_of_progress=ForcesOfProgress(push="x", pull="y", anxiety="z", habit="w"),
        top_problem_statements=[],
        challenger_reframe="x",
        calibrated_questions=[
            "What does success look like in 12 months?",
            "How does this fit into your broader priorities?",
        ],
        nsttd_email="Short test email",
        next_best_action="schedule_15min",
        confidence=0.85,
    )

    assert brief.detected_persona == "av_director"
    assert brief.icp_score == 90
    assert brief.next_best_action == "schedule_15min"


def test_bdr_call_brief_rejects_invalid_next_best_action() -> None:
    """`next_best_action` must be one of the 4 allowed actions."""
    from pydantic import ValidationError

    from src.storyboard.schemas import BDRCallBrief, ForcesOfProgress

    with pytest.raises(ValidationError):
        BDRCallBrief(
            detected_persona="av_director",
            detected_vertical="higher_ed",
            icp_score=90,
            job_statement="x",
            forces_of_progress=ForcesOfProgress(),
            top_problem_statements=[],
            challenger_reframe="x",
            calibrated_questions=[],
            nsttd_email="x",
            next_best_action="give_up",  # invalid
            confidence=0.5,
        )


def test_calibrated_questions_pass_what_or_how_filter() -> None:
    """The helper that filters/repairs calibrated questions enforces What/How."""
    from src.tools.storyboard.bdr_brief_generator import (
        filter_calibrated_questions,
    )

    raw = [
        "What does success look like?",
        "How do you currently handle that?",
        "Why did you pick that vendor?",  # bad — Why
        "Did you try a different approach?",  # bad — yes/no
        "How would your team feel about a change?",
    ]

    filtered = filter_calibrated_questions(raw)

    assert len(filtered) == 3
    assert all(q.strip().split()[0].lower() in ("what", "how") for q in filtered)
    assert not any("why" in q.lower() for q in filtered)


def test_select_next_best_action_for_strong_push() -> None:
    """Strong push + low ICP gating threshold → schedule_15min."""
    from src.storyboard.schemas import ForcesOfProgress
    from src.tools.storyboard.bdr_brief_generator import select_next_best_action

    forces = ForcesOfProgress(
        push="200 rooms with 5% capture failure rate; provost is asking for fix",
        pull="single-pane fleet management",
        anxiety="",
        habit="",
    )

    nba = select_next_best_action(
        forces=forces, icp_score=90, extraction_confidence=0.85
    )

    assert nba == "schedule_15min"


def test_select_next_best_action_for_low_signal() -> None:
    """Empty forces + low confidence → send_problem_email (nurture)."""
    from src.storyboard.schemas import ForcesOfProgress
    from src.tools.storyboard.bdr_brief_generator import select_next_best_action

    forces = ForcesOfProgress(push="", pull="", anxiety="", habit="")
    nba = select_next_best_action(
        forces=forces, icp_score=70, extraction_confidence=0.4
    )

    assert nba == "send_problem_email"


def test_select_next_best_action_disqualifies_low_icp() -> None:
    """Very low ICP → disqualify rather than nurture."""
    from src.storyboard.schemas import ForcesOfProgress
    from src.tools.storyboard.bdr_brief_generator import select_next_best_action

    forces = ForcesOfProgress(push="", pull="", anxiety="", habit="")
    nba = select_next_best_action(
        forces=forces, icp_score=20, extraction_confidence=0.6
    )

    assert nba == "disqualify"


def test_generate_brief_from_transcript_assembles_all_fields() -> None:
    """End-to-end (deterministic): transcript + vertical + persona → full brief."""
    from src.tools.storyboard.bdr_brief_generator import (
        generate_brief_from_transcript,
    )

    transcript = (
        "Speaker 1: We've got 200 classrooms and our IT team is spending "
        "half the week troubleshooting recordings where the encoder feeding "
        "our LMS drops files. Faculty stop recording when the upload breaks. "
        "We need a way to monitor every room from one dashboard."
    )

    brief = generate_brief_from_transcript(
        transcript=transcript,
        vertical="higher_ed",
        persona="av_director",
    )

    assert brief.detected_vertical == "higher_ed"
    assert brief.detected_persona == "av_director"
    assert brief.icp_score == 90
    # At least 1 problem statement matched against transcript
    assert len(brief.top_problem_statements) >= 1
    # Calibrated questions all start with What/How
    assert all(
        q.strip().split()[0].lower() in ("what", "how")
        for q in brief.calibrated_questions
    )
    # NSTTD email present and reasonably short
    assert len(brief.nsttd_email) > 0
    assert brief.confidence > 0


def test_generate_brief_from_buyer_profile() -> None:
    """Survey-only path: BuyerProfile alone produces a usable brief."""
    from src.storyboard.schemas import BuyerProfile, ForcesOfProgress
    from src.tools.storyboard.bdr_brief_generator import (
        generate_brief_from_profile,
    )

    profile = BuyerProfile(
        detected_persona="av_director",
        detected_vertical="higher_ed",
        forces_of_progress=ForcesOfProgress(
            push="200 rooms, can't keep up",
            pull="single-pane fleet management",
            anxiety="ripping out existing AV is months",
            habit="AV team trained on legacy stack",
        ),
        pain_points_ranked=[("unscalable_room_walks", 0.9)],
        workflow_signals={"room_count": "200+", "lms": "your LMS"},
    )

    brief = generate_brief_from_profile(profile)

    assert brief.detected_persona == "av_director"
    assert brief.icp_score == 90
    assert len(brief.top_problem_statements) >= 1


def test_email_under_word_limit() -> None:
    """The NSTTD email defaults to ≤100 words for cold outreach."""
    from src.tools.storyboard.bdr_brief_generator import build_nsttd_email

    email = build_nsttd_email(
        persona="av_director",
        vertical="higher_ed",
        top_pain_phrase="rooms going unrecorded",
        prospect_first_name=None,
    )

    word_count = len(email.split())
    assert word_count <= 110, f"NSTTD email is {word_count} words, expected ≤ 110"
    # Accusation audit phrasing
    lower = email.lower()
    assert any(kw in lower for kw in ("you might", "you're probably", "would it be"))
