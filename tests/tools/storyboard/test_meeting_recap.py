"""Tests for ``meeting_recap.process_meeting_recap``.

Background — DA-R1.1 (2026-05-09)
=================================
``process_meeting_recap`` previously called ``client.extract_content(prompt)`` —
a method that does NOT exist on ``GeminiStoryboardClient``. The endpoint
``POST /storyboard/meeting-recap`` was silently 500-ing in production every
time it was called. There were zero tests exercising this function, so CI
never caught it.

DA-R1.1 fixes the bug AND wires the two-pass narrative+schema augmentation
(shipped yesterday in DA-R1) so long discovery-call transcripts get the
richer Forces-of-Progress + Frankenstack overlay. The other 15 keys
(job_statement, challenger_reframe, follow_up_email, etc.) come from the
single-pass and are left untouched.

These tests would fail RED on main before today's diff:
- ``test_process_meeting_recap_uses_call_text_model`` — fails because
  ``extract_content`` doesn't exist.
- The five two-pass tests fail because the augmentation block doesn't exist.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.storyboard.gemini_client import GeminiConfig, GeminiStoryboardClient
from src.tools.storyboard.meeting_recap import process_meeting_recap


def _meeting_recap_payload(forces_push: str = "single-pass push") -> str:
    """Build a minimal-but-valid meeting-recap JSON the single-pass would emit.

    Includes all 17 keys the router expects, plus realistic values so test
    failures show meaningful diffs.
    """
    return json.dumps(
        {
            "job_statement": "When I walk into a courtroom, I want reliable capture.",
            "forces_of_progress": {
                "push": forces_push,
                "pull": "single-pass pull",
                "anxiety": "single-pass anxiety",
                "habit": "single-pass habit",
            },
            "hiring_firing": {
                "currently_hired": "PC + OBS",
                "fired_for": "missing recordings",
                "workarounds": "thumb drive walk",
            },
            "summary": "Court admin describes systemic recording loss.",
            "key_topics": ["chain of custody", "remote witness"],
            "participants": [{"role": "Court Administrator"}],
            "frankenstack_description": "single-pass frankenstack",
            "buyer_signals": {
                "pain": "wrongful-conviction inquiry",
                "need": "centralized monitoring",
                "timeline": "24-month phased",
                "authority": "court IT director",
                "proof": "peer reference",
            },
            "challenger_reframe": "Most courts believe...",
            "rational_drowning": "$48K/yr wasted on captioning",
            "emotional_impact": "reputation risk",
            "product_recommendations": [],
            "follow_up_email": "Subject: Court IT recap",
            "calibrated_questions": ["What would make this fail again?"],
            "thats_right_summary": "You've described a chain-of-custody risk.",
            "detected_vertical": "legal",
            "detected_persona": "court_admin",
        }
    )


def _two_pass_schema_payload(
    push: str = "two-pass push",
    frankenstack: str = "two-pass frankenstack",
) -> str:
    """Build a minimal-but-valid pass-2 JSON the schema-mapping prompt emits."""
    return json.dumps(
        {
            "forces_of_progress": {
                "push": push,
                "pull": "two-pass pull",
                "anxiety": "two-pass anxiety",
                "habit": "two-pass habit",
            },
            "frankenstack": frankenstack,
            "extraction_confidence": 0.9,
        }
    )


# ---------------------------------------------------------------------------
# 1. Bug fix — process_meeting_recap must call _call_text_model, not the
#    non-existent extract_content method.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_meeting_recap_uses_call_text_model() -> None:
    """Regression: ``extract_content`` does NOT exist on ``GeminiStoryboardClient``.

    Before DA-R1.1 the call site was ``await client.extract_content(prompt)``,
    which 500'd the meeting-recap endpoint in production. The fix routes
    through ``_call_text_model``, the same helper DA-R1's two-pass uses.
    """
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t")  # short trigger threshold elsewhere
    fake_client._call_text_model = AsyncMock(return_value=_meeting_recap_payload())

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="Short call about court recordings.",
            audience="court_admin",
            vertical="legal",
        )

    assert fake_client._call_text_model.await_count >= 1, (
        "process_meeting_recap must dispatch through _call_text_model. "
        "If this asserts 0, the bug is back: someone called a non-existent "
        "method on the client and the endpoint will 500."
    )
    assert result["job_statement"].startswith("When I walk into a courtroom")


# ---------------------------------------------------------------------------
# 2. Short transcripts skip the two-pass augmentation.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_short_transcript_skips_two_pass() -> None:
    """When ``len(transcript) < two_pass_threshold_chars``, the augmentation
    must not fire — only the single-pass meeting-recap call happens."""
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t")  # default threshold 10_000
    fake_client._call_text_model = AsyncMock(return_value=_meeting_recap_payload())

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="Short transcript.",
            audience="court_admin",
            vertical="legal",
        )

    assert fake_client._call_text_model.await_count == 1, (
        "Short transcripts must run exactly ONE LLM call (single-pass). "
        f"Got {fake_client._call_text_model.await_count}."
    )
    assert result["two_pass_applied"] is False
    assert result["forces_of_progress"]["push"] == "single-pass push"
    assert result["frankenstack_description"] == "single-pass frankenstack"


# ---------------------------------------------------------------------------
# 3. Long transcripts fire two-pass and overlay forces + frankenstack.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_long_transcript_triggers_two_pass_overlay() -> None:
    """Transcripts ≥ ``two_pass_threshold_chars`` must:
    - Run THREE LLM calls (single-pass + narrative + schema-mapping).
    - Overlay forces_of_progress + frankenstack_description from two-pass.
    - Mark ``two_pass_applied = True``.
    - Leave the other 15 keys untouched (sourced from single-pass).
    """
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t", two_pass_threshold_chars=100)
    # side_effect → three sequential responses: single-pass, narrative, schema.
    fake_client._call_text_model = AsyncMock(
        side_effect=[
            _meeting_recap_payload(),
            "PUSH: ... PULL: ... (narrative free-text)",
            _two_pass_schema_payload(),
        ]
    )

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="A" * 200,  # > 100-char threshold
            audience="court_admin",
            vertical="legal",
        )

    assert fake_client._call_text_model.await_count == 3, (
        "Long transcripts must run THREE LLM calls (single-pass + 2× "
        f"two-pass). Got {fake_client._call_text_model.await_count}."
    )
    assert result["two_pass_applied"] is True
    # Overlaid fields come from two-pass:
    assert result["forces_of_progress"]["push"] == "two-pass push"
    assert result["frankenstack_description"] == "two-pass frankenstack"
    # Non-overlaid fields stay from single-pass:
    assert result["job_statement"].startswith("When I walk into a courtroom")
    assert result["challenger_reframe"] == "Most courts believe..."
    assert result["follow_up_email"] == "Subject: Court IT recap"


# ---------------------------------------------------------------------------
# 4. Two-pass failure falls back gracefully — single-pass result preserved.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_pass_failure_falls_back_gracefully() -> None:
    """If the narrative LLM call (or schema parse) fails, the single-pass
    result is returned unchanged with ``two_pass_applied = False``. The
    function must never bubble the exception up to the router."""
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t", two_pass_threshold_chars=100)
    # First call succeeds (single-pass meeting-recap). Second call (narrative)
    # raises — simulates an upstream LLM blip.
    fake_client._call_text_model = AsyncMock(
        side_effect=[
            _meeting_recap_payload(),
            RuntimeError("upstream 503"),
        ]
    )

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="A" * 200,
            audience="court_admin",
            vertical="legal",
        )

    assert result["two_pass_applied"] is False
    # Single-pass values preserved (NOT replaced by a fallback or an empty dict)
    assert result["forces_of_progress"]["push"] == "single-pass push"
    assert result["frankenstack_description"] == "single-pass frankenstack"
    # Other keys still present
    assert result["job_statement"].startswith("When I walk into a courtroom")


# ---------------------------------------------------------------------------
# 5. Disabled flag — operator override skips two-pass even on long transcripts.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_flag_skips_two_pass_even_on_long_transcript() -> None:
    """``GeminiConfig(enable_two_pass_extraction=False)`` is the operator
    escape hatch. Even on a 200-char transcript with a 100-char threshold,
    only ONE LLM call must fire."""
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(
        api_key="t",
        two_pass_threshold_chars=100,
        enable_two_pass_extraction=False,
    )
    fake_client._call_text_model = AsyncMock(return_value=_meeting_recap_payload())

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="A" * 200,
            audience="court_admin",
            vertical="legal",
        )

    assert fake_client._call_text_model.await_count == 1
    assert result["two_pass_applied"] is False


# ---------------------------------------------------------------------------
# 6. Two-pass overlay is narrow — only forces + frankenstack are touched.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 7. DA-R1.1.b — Defensive coercion: LLM sometimes returns ``summary`` as a
#    list of bullets when MeetingRecapResponse expects a string. Coerce.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_list_is_coerced_to_string() -> None:
    """Regression: ``MeetingRecapResponse.summary: str`` blows up with a
    Pydantic ValidationError when the LLM returns a JSON array. The prompt
    asks for "3-5 bullet executive summary" and the LLM frequently obliges
    with ``["bullet 1", "bullet 2", ...]``. We coerce that to a multiline
    string so the router's response model validates.
    """
    payload = json.loads(_meeting_recap_payload())
    payload["summary"] = [
        "AV Director manages 47 lecture-capture rooms",
        "60% are PC-based with software encoders",
        "Loses 8-12 recordings per semester to PC failures",
    ]

    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t")
    fake_client._call_text_model = AsyncMock(return_value=json.dumps(payload))

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="Short transcript.",
            audience="av_director",
            vertical="higher_ed",
        )

    assert isinstance(result["summary"], str), (
        "summary must be coerced to str (was list)."
    )
    assert "AV Director manages" in result["summary"]
    assert "PC failures" in result["summary"]
    # All three bullets present in the multiline join
    assert result["summary"].count("\n") == 2


@pytest.mark.asyncio
async def test_summary_string_is_passed_through_unchanged() -> None:
    """When the LLM correctly returns a string, the coercion is a no-op."""
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t")
    fake_client._call_text_model = AsyncMock(return_value=_meeting_recap_payload())

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="Short transcript.",
            audience="court_admin",
            vertical="legal",
        )

    assert isinstance(result["summary"], str)
    assert result["summary"] == "Court admin describes systemic recording loss."


@pytest.mark.asyncio
async def test_two_pass_overlay_does_not_touch_other_meeting_recap_keys() -> None:
    """The 15 non-overlaid keys (job_statement, hiring_firing, summary,
    key_topics, participants, buyer_signals, challenger_reframe, rational_drowning,
    emotional_impact, product_recommendations, follow_up_email, calibrated_questions,
    thats_right_summary, detected_vertical, detected_persona) must come from
    the single-pass and stay untouched even when two-pass overlays the others.

    This is the contract the ``MeetingRecapResponse`` router mapping depends on.
    """
    fake_client = MagicMock(spec=GeminiStoryboardClient)
    fake_client.config = GeminiConfig(api_key="t", two_pass_threshold_chars=100)
    fake_client._call_text_model = AsyncMock(
        side_effect=[
            _meeting_recap_payload(),
            "narrative text",
            _two_pass_schema_payload(),
        ]
    )

    with patch(
        "src.tools.storyboard.gemini_client.GeminiStoryboardClient",
        return_value=fake_client,
    ):
        result = await process_meeting_recap(
            transcript="A" * 200,
            audience="court_admin",
            vertical="legal",
        )

    untouched = {
        "job_statement",
        "hiring_firing",
        "summary",
        "key_topics",
        "participants",
        "buyer_signals",
        "challenger_reframe",
        "rational_drowning",
        "emotional_impact",
        "product_recommendations",
        "follow_up_email",
        "calibrated_questions",
        "thats_right_summary",
        "detected_vertical",
        "detected_persona",
    }
    single_pass = json.loads(_meeting_recap_payload())
    for key in untouched:
        assert result[key] == single_pass[key], (
            f"Key {key!r} was modified by the two-pass overlay. "
            "Only forces_of_progress and frankenstack_description should be "
            "overlaid; the other 15 keys must stay from single-pass."
        )
