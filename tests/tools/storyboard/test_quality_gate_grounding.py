"""Tests for the frankenstack-grounding quality-gate check.

``_check_frankenstack_grounding`` verifies the extracted frankenstack reflects
the stack actually discussed on the call:
  * workaround/pain signal present but frankenstack empty  -> warning
  * frankenstack present but names no real vendor           -> info
  * frankenstack names a real vendor                        -> clean
  * no workaround signal at all                             -> clean
"""

from __future__ import annotations

from src.tools.storyboard.quality_gate import (
    QualityReport,
    _check_frankenstack_grounding,
    run_quality_gate,
)

# A transcript dripping with workaround signals and a real vendor.
_TRANSCRIPT = (
    "AV Director: Honestly we had to duct-tape OBS to a capture card and it "
    "still drops frames every single lecture. We keep doing manual workarounds."
)


def _msgs(report: QualityReport) -> list[str]:
    return [i.message.lower() for i in report.issues]


def test_empty_frankenstack_with_workaround_signal_warns() -> None:
    report = QualityReport()
    _check_frankenstack_grounding(
        {"frankenstack_description": ""}, report, transcript=_TRANSCRIPT
    )
    assert any("frankenstack is" in m and "empty" in m for m in _msgs(report))


def test_generic_frankenstack_no_vendor_flags_info() -> None:
    report = QualityReport()
    _check_frankenstack_grounding(
        {"frankenstack_description": "a messy pile of legacy gear and scripts"},
        report,
        transcript=_TRANSCRIPT,
    )
    assert any("no specific vendor" in m for m in _msgs(report))


def test_grounded_frankenstack_passes() -> None:
    report = QualityReport()
    _check_frankenstack_grounding(
        {"frankenstack_description": "OBS feeding a Blackmagic card, no failover"},
        report,
        transcript=_TRANSCRIPT,
    )
    assert not any("frankenstack" in m for m in _msgs(report))


def test_no_workaround_signal_is_silent() -> None:
    report = QualityReport()
    _check_frankenstack_grounding(
        {"frankenstack_description": ""},
        report,
        transcript="AV Director: Everything is going great, no complaints.",
    )
    assert not any("frankenstack" in m for m in _msgs(report))


def test_falls_back_to_understanding_when_no_transcript() -> None:
    # No transcript provided -> scans the extracted fields for the signal.
    report = QualityReport()
    _check_frankenstack_grounding(
        {
            "pain_point_addressed": "We had to build a workaround that drops frames",
            "frankenstack_description": "",
        },
        report,
    )
    assert any("empty" in m for m in _msgs(report))


def test_run_quality_gate_accepts_transcript_kwarg() -> None:
    # End-to-end: the public entry point threads transcript through and the
    # grounding warning shows up in the report.
    report = run_quality_gate(
        understanding={"frankenstack_description": "", "who_benefits": "AV Director"},
        audience="av_director",
        transcript=_TRANSCRIPT,
    )
    assert any(i.category == "frankenstack" for i in report.issues)
