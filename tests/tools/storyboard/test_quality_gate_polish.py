"""Tests for the Phase 1.7 quality-gate enhancements.

Three new checks added to ``src/tools/storyboard/quality_gate.py``:
  1. ``_check_problem_statement_resonance`` — pain_point shares ≥1 noun
     phrase with the BDR-validated problem statements for the (vertical,
     persona) combo.
  2. ``_check_calibrated_question_form`` — every entry starts with What/How,
     contains no "Why", and ends with "?".
  3. ``_check_brief_completeness`` — when ``next_best_action == "send_problem_email"``,
     the ``nsttd_email`` must include an accusation-audit phrase AND a
     no-oriented CTA.
"""

from __future__ import annotations


def test_problem_statement_resonance_warns_on_drift() -> None:
    """When the LLM-generated pain_point shares zero overlap with verbatim
    BDR statements for the persona, the check should warn."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_problem_statement_resonance,
    )

    report = QualityReport()
    understanding = {
        "pain_point_addressed": (
            "The team is exploring opportunities to leverage synergies"  # AI fluff
        )
    }
    _check_problem_statement_resonance(
        understanding=understanding,
        vertical="higher_ed",
        persona="av_director",
        report=report,
    )

    # At least one warning emitted
    assert report.warning_count >= 1
    msgs = [i.message for i in report.issues]
    assert any("verbatim" in m.lower() or "resonance" in m.lower() for m in msgs)


def test_problem_statement_resonance_passes_when_grounded() -> None:
    """When pain_point shares vocabulary with a verbatim statement, no warning."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_problem_statement_resonance,
    )

    report = QualityReport()
    understanding = {
        "pain_point_addressed": (
            "Faculty stop recording when the LMS upload breaks and rooms "
            "go unrecorded as a result."
        )
    }
    _check_problem_statement_resonance(
        understanding=understanding,
        vertical="higher_ed",
        persona="av_director",
        report=report,
    )

    # No problem-statement-resonance warnings raised
    msgs = [i.message for i in report.issues]
    assert not any(("verbatim" in m.lower() or "resonance" in m.lower()) for m in msgs)


def test_calibrated_question_form_flags_why() -> None:
    """A calibrated question containing 'Why' triggers a warning."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_calibrated_question_form,
    )

    report = QualityReport()
    questions = [
        "What does success look like?",
        "Why did you pick that vendor?",  # bad
    ]
    _check_calibrated_question_form(questions, report)

    assert report.warning_count >= 1


def test_calibrated_question_form_flags_yes_no() -> None:
    """A yes/no calibrated question (Did/Have/Do/Is) triggers a warning."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_calibrated_question_form,
    )

    report = QualityReport()
    questions = [
        "What does success look like?",
        "Did you try a different approach?",  # bad — yes/no
    ]
    _check_calibrated_question_form(questions, report)

    assert report.warning_count >= 1


def test_calibrated_question_form_passes_clean() -> None:
    """Well-formed What/How questions don't produce warnings."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_calibrated_question_form,
    )

    report = QualityReport()
    questions = [
        "What does success look like?",
        "How do you currently handle that?",
        "What would have to be true for one tech to cover three rooms?",
    ]
    _check_calibrated_question_form(questions, report)

    msgs = [i.message for i in report.issues]
    assert not any("calibrated" in m.lower() for m in msgs)


def test_brief_completeness_flags_missing_audit() -> None:
    """When NBA=send_problem_email but email lacks accusation audit, warn."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_brief_completeness,
    )

    report = QualityReport()
    _check_brief_completeness(
        next_best_action="send_problem_email",
        nsttd_email=("Hi there, I wanted to introduce our product. Best regards."),
        report=report,
    )

    assert report.warning_count >= 1


def test_brief_completeness_flags_missing_no_cta() -> None:
    """When NBA=send_problem_email but email lacks no-oriented CTA, warn."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_brief_completeness,
    )

    report = QualityReport()
    _check_brief_completeness(
        next_best_action="send_problem_email",
        nsttd_email=(
            "You probably get pitched every week. Fair enough. Let me know "
            "if you want to talk. Best regards."
        ),
        report=report,
    )

    assert report.warning_count >= 1


def test_brief_completeness_skips_when_nba_isnt_email() -> None:
    """When NBA is schedule_15min, the email-shape check doesn't run."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_brief_completeness,
    )

    report = QualityReport()
    _check_brief_completeness(
        next_best_action="schedule_15min",
        nsttd_email="",  # email body is empty — no warning expected
        report=report,
    )

    assert report.warning_count == 0


def test_brief_completeness_passes_well_formed_email() -> None:
    """A well-formed email passes both checks."""
    from src.tools.storyboard.quality_gate import (
        QualityReport,
        _check_brief_completeness,
    )

    report = QualityReport()
    well_formed = (
        "Hi there,\n\nYou probably get pitched every week. Fair enough.\n"
        "But the thing we keep hearing from teams like yours is the same "
        "frustration. Would it be ridiculous to spend 15 minutes comparing "
        "notes?\n\nEither way, no worries.\nTim"
    )
    _check_brief_completeness(
        next_best_action="send_problem_email",
        nsttd_email=well_formed,
        report=report,
    )

    msgs = [i.message for i in report.issues]
    assert not any("audit" in m.lower() or "no-oriented" in m.lower() for m in msgs)
