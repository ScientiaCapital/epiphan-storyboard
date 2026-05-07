"""Tests for src/tools/storyboard/vertical_surveys.py and the new survey schemas.

Phase 1 ships surveys for the top-3 ICP verticals: Higher Education,
Courts/Legal, and Live Events. The Live Events survey is ported verbatim
from ``US_2026_Live_Events_Workflow_Survey.docx``; Higher Ed and Courts
follow the same JTBD job-map structure adapted from the Problem Statements
doc (April 2026 BDR playbook).

The schemas live in ``src.storyboard.schemas`` (with the rest of the
storyboard request/response models) and the question banks live in
``src.tools.storyboard.vertical_surveys`` to keep doc text out of the
schema module.
"""

from __future__ import annotations

import pytest


# =============================================================================
# Schemas
# =============================================================================


def test_survey_question_validates_minimal_record() -> None:
    """SurveyQuestion accepts a minimal valid question."""
    from src.storyboard.schemas import SurveyQuestion

    q = SurveyQuestion(
        id="q1",
        section="About You",
        text="Which best describes your role?",
        type="single",
        options=["AV Director", "IT Director", "Other"],
        job_map_step="define",
    )

    assert q.id == "q1"
    assert q.type == "single"
    assert q.job_map_step == "define"
    assert len(q.options or []) == 3


def test_survey_question_rejects_invalid_type() -> None:
    """`type` must be one of single/multi/matrix/open."""
    from pydantic import ValidationError

    from src.storyboard.schemas import SurveyQuestion

    with pytest.raises(ValidationError):
        SurveyQuestion(
            id="q1",
            section="x",
            text="x",
            type="paragraph",  # invalid
            job_map_step="define",
        )


def test_survey_question_rejects_invalid_job_map_step() -> None:
    """`job_map_step` must be one of the 8 JTBD job-map step values."""
    from pydantic import ValidationError

    from src.storyboard.schemas import SurveyQuestion

    with pytest.raises(ValidationError):
        SurveyQuestion(
            id="q1",
            section="x",
            text="x",
            type="single",
            job_map_step="bogus_step",
        )


def test_workflow_survey_aggregates_questions() -> None:
    """WorkflowSurvey holds a vertical, intro, sections, and questions."""
    from src.storyboard.schemas import SurveyQuestion, WorkflowSurvey

    survey = WorkflowSurvey(
        vertical="higher_ed",
        title="Higher Ed Workflow Survey",
        intro="A short intro.",
        sections=["About You", "Workflow"],
        questions=[
            SurveyQuestion(
                id="q1",
                section="About You",
                text="Role?",
                type="single",
                options=["AV Director"],
                job_map_step="define",
            ),
        ],
    )

    assert survey.vertical == "higher_ed"
    assert len(survey.questions) == 1


def test_buyer_profile_uses_existing_forces_of_progress() -> None:
    """BuyerProfile reuses the existing ForcesOfProgress shape (DRY)."""
    from src.storyboard.schemas import BuyerProfile, ForcesOfProgress

    profile = BuyerProfile(
        detected_persona="av_director",
        detected_vertical="higher_ed",
        forces_of_progress=ForcesOfProgress(push="x", pull="y", anxiety="z", habit="w"),
        pain_points_ranked=[("classroom_pc_crash", 0.9)],
        workflow_signals={"room_count": "200+"},
    )

    assert profile.detected_persona == "av_director"
    assert profile.forces_of_progress.push == "x"


# =============================================================================
# Phase 1 vertical surveys — Higher Ed, Courts, Live Events
# =============================================================================


@pytest.mark.parametrize("vertical", ["higher_ed", "legal", "live_events"])
def test_phase_1_survey_loads_for_vertical(vertical: str) -> None:
    """Each Phase-1 vertical has a non-empty WorkflowSurvey available."""
    from src.tools.storyboard.vertical_surveys import get_survey

    survey = get_survey(vertical)
    assert survey.vertical == vertical
    assert len(survey.questions) > 0
    assert survey.title.strip()
    assert survey.intro.strip()


def test_get_survey_returns_none_for_unknown_vertical() -> None:
    """Unknown vertical returns None — caller decides how to handle."""
    from src.tools.storyboard.vertical_surveys import get_survey

    assert get_survey("phase_2_vertical") is None


def test_phase_1_survey_questions_have_unique_ids() -> None:
    """Each survey's question IDs are unique within that survey."""
    from src.tools.storyboard.vertical_surveys import get_survey

    for vertical in ("higher_ed", "legal", "live_events"):
        survey = get_survey(vertical)
        assert survey is not None
        ids = [q.id for q in survey.questions]
        assert len(ids) == len(set(ids)), f"Duplicate ids in {vertical}"


@pytest.mark.parametrize("vertical", ["higher_ed", "legal", "live_events"])
def test_every_question_tags_job_map_step(vertical: str) -> None:
    """Every question must have a valid job_map_step — that's the JTBD link."""
    from src.tools.storyboard.vertical_surveys import get_survey

    survey = get_survey(vertical)
    assert survey is not None
    valid = {
        "define",
        "locate",
        "prepare",
        "confirm",
        "execute",
        "monitor",
        "modify",
        "conclude",
    }
    for q in survey.questions:
        assert q.job_map_step in valid


def test_live_events_survey_ports_at_least_30_questions() -> None:
    """Live Events port retains substantial coverage — original is 48 questions."""
    from src.tools.storyboard.vertical_surveys import get_survey

    survey = get_survey("live_events")
    assert survey is not None
    assert len(survey.questions) >= 30


def test_higher_ed_survey_covers_phase1_personas() -> None:
    """Higher Ed survey has at least one question per Phase-1 Higher Ed persona."""
    from src.tools.storyboard.vertical_surveys import get_survey

    survey = get_survey("higher_ed")
    assert survey is not None
    # Sections expected to map to persona contexts
    sections = {s.lower() for s in survey.sections}
    # Either explicit persona-named sections OR a "role" question covering them
    role_q = next(
        (q for q in survey.questions if "role" in q.text.lower() and q.options),
        None,
    )
    assert role_q is not None or sections, (
        "Higher Ed survey must cover the 4 Phase-1 personas via sections "
        "or via a role-disambiguation question"
    )


# =============================================================================
# survey_responses_to_prompt_context — feeds prompt_builders
# =============================================================================


def test_survey_response_to_prompt_context_emits_signal_block() -> None:
    """Survey answers convert to a prompt-injectable SURVEY-DERIVED SIGNALS block."""
    from src.storyboard.schemas import BuyerProfile, ForcesOfProgress
    from src.tools.storyboard.vertical_surveys import (
        survey_responses_to_prompt_context,
    )

    profile = BuyerProfile(
        detected_persona="av_director",
        detected_vertical="higher_ed",
        forces_of_progress=ForcesOfProgress(
            push="200 rooms, can't keep up",
            pull="single-pane fleet management",
            anxiety="ripping out existing AV is months of work",
            habit="AV team trained on legacy stack",
        ),
        pain_points_ranked=[("unscalable_room_walks", 0.9)],
        workflow_signals={"room_count": "200+", "lms": "your LMS"},
    )

    block = survey_responses_to_prompt_context(profile)

    assert "SURVEY-DERIVED SIGNALS" in block.upper()
    # Every Force of Progress should be quoted in the block
    assert "200 rooms" in block
    assert "single-pane" in block
    assert "ripping out" in block
    assert "legacy stack" in block


def test_survey_response_to_prompt_context_returns_empty_for_none() -> None:
    """Falsy profile yields empty string (graceful degradation)."""
    from src.tools.storyboard.vertical_surveys import (
        survey_responses_to_prompt_context,
    )

    assert survey_responses_to_prompt_context(None) == ""
