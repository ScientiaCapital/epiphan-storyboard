"""Tests for the survey endpoints added in Phase 1.5.

- GET /storyboard/survey/templates/{vertical}
- POST /storyboard/survey/submit

These endpoints are intentionally simple and don't depend on Redis,
Supabase, or any LLM client — Phase 1 goal is structural plumbing,
not orchestration.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_client() -> TestClient:
    """Spin up a minimal FastAPI app wrapping just the storyboard router."""
    from src.storyboard.router import router as storyboard_router

    app = FastAPI()
    app.include_router(storyboard_router)
    return TestClient(app)


# =============================================================================
# GET /storyboard/survey/templates/{vertical}
# =============================================================================


def test_get_survey_template_for_higher_ed() -> None:
    """Higher Ed vertical returns a non-empty WorkflowSurvey."""
    client = _make_client()
    r = client.get("/storyboard/survey/templates/higher_ed")
    assert r.status_code == 200
    body = r.json()
    assert body["vertical"] == "higher_ed"
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 10
    assert body["title"]
    assert body["intro"]


def test_get_survey_template_for_legal() -> None:
    """Legal vertical returns its survey."""
    client = _make_client()
    r = client.get("/storyboard/survey/templates/legal")
    assert r.status_code == 200
    assert r.json()["vertical"] == "legal"


def test_get_survey_template_for_live_events() -> None:
    """Live Events vertical returns the 30+-question port."""
    client = _make_client()
    r = client.get("/storyboard/survey/templates/live_events")
    assert r.status_code == 200
    body = r.json()
    assert body["vertical"] == "live_events"
    assert len(body["questions"]) >= 30


def test_get_survey_template_unknown_returns_404() -> None:
    """Unknown vertical returns 404 with a helpful message."""
    client = _make_client()
    r = client.get("/storyboard/survey/templates/phase_2_vertical")
    assert r.status_code == 404
    detail = r.json().get("detail", "")
    assert "vertical" in detail.lower() or "phase 2" in detail.lower()


# =============================================================================
# POST /storyboard/survey/submit
# =============================================================================


def test_submit_survey_with_minimal_response() -> None:
    """Survey-only submission returns a BDR brief without a transcript."""
    client = _make_client()
    payload = {
        "vertical": "higher_ed",
        "responses": {
            "survey_id": "higher_ed",
            "answers": {
                "he_q1": "AV Director / Director of AV Architecture",
                "he_q2": "200 to 499",
            },
        },
    }
    r = client.post("/storyboard/survey/submit", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    # Brief is the headline artifact
    assert "bdr_call_brief" in body
    brief = body["bdr_call_brief"]
    assert brief["detected_vertical"] == "higher_ed"
    assert brief["detected_persona"] == "av_director"
    assert brief["icp_score"] == 90
    assert len(brief["top_problem_statements"]) >= 1


def test_submit_survey_with_transcript() -> None:
    """Survey + transcript submission returns brief grounded on transcript."""
    client = _make_client()
    payload = {
        "vertical": "higher_ed",
        "responses": {
            "survey_id": "higher_ed",
            "answers": {
                "he_q1": "AV Director / Director of AV Architecture",
            },
        },
        "transcript": (
            "Speaker 1: We've got 200 classrooms and our IT team is "
            "spending half the week troubleshooting recordings where the "
            "encoder feeding our LMS drops files."
        ),
    }
    r = client.post("/storyboard/survey/submit", json=payload)
    assert r.status_code == 200, r.text
    brief = r.json()["bdr_call_brief"]
    assert brief["detected_vertical"] == "higher_ed"
    # Calibrated questions discipline
    assert all(
        q.strip().split()[0].lower() in ("what", "how")
        for q in brief["calibrated_questions"]
    )


def test_submit_unknown_vertical_returns_400() -> None:
    """Unknown vertical → 400 (not 404; this is a payload validation issue)."""
    client = _make_client()
    payload = {
        "vertical": "phase_2_vertical",
        "responses": {"survey_id": "phase_2_vertical", "answers": {}},
    }
    r = client.post("/storyboard/survey/submit", json=payload)
    assert r.status_code in (400, 404, 422), r.text
