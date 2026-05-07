"""Tests for src/tools/storyboard/transcript_compactor.py.

The compactor replaces the current 32K hard-truncation in prompt_builders by
running extractive summarization: segment by speaker turn, score for
JTBD-relevant signal (pain phrases, vendor mentions, time/budget/authority
cues, workaround language), keep top-N highest-signal turns plus the first
and last 10 % of the call (intros and decisions live there).
"""

from __future__ import annotations

import pytest


def test_short_transcript_passes_through_unchanged() -> None:
    """A transcript already under the target length round-trips intact."""
    from src.tools.storyboard.transcript_compactor import compact_transcript

    text = "Speaker 1: Hi.\nSpeaker 2: Hi back."

    result = compact_transcript(text, target_chars=10_000)

    assert result.full_context == text
    assert result.key_moments
    # No reduction needed
    assert len(result.full_context) == len(text)
    assert result.compaction_ratio == 1.0


def test_long_transcript_is_reduced_to_target() -> None:
    """A transcript well above the target is compacted to ≤ target_chars."""
    from src.tools.storyboard.transcript_compactor import compact_transcript

    # Build a 60K-char transcript: 200 turns × 300 chars each.
    turns = [f"Speaker {i % 2 + 1}: " + ("filler line " * 25) for i in range(200)]
    text = "\n".join(turns)
    assert len(text) > 50_000

    result = compact_transcript(text, target_chars=20_000)

    assert len(result.full_context) <= 20_000
    assert result.compaction_ratio < 1.0
    # key_moments is the 8K subset
    assert len(result.key_moments) <= 8_000


def test_high_signal_turns_are_preserved() -> None:
    """JTBD-signal turns (pain phrases, vendor mentions) survive compaction."""
    from src.tools.storyboard.transcript_compactor import compact_transcript

    filler_turn = "Speaker 1: " + ("uh yeah okay so " * 80)  # ~1.3 K of filler
    pain_turn = (
        "Speaker 2: Honestly the biggest pain is that our Panopto upload "
        "fails about 30 percent of the time and it's burning our team's "
        "entire week troubleshooting it."
    )
    vendor_turn = (
        "Speaker 1: We've also been hacking around it with OBS and a "
        "classroom PC, but the workaround crashes mid-lecture."
    )

    # 80 filler turns wrapping the 2 high-signal turns
    parts = [filler_turn] * 40 + [pain_turn] + [filler_turn] * 39 + [vendor_turn]
    text = "\n".join(parts)

    result = compact_transcript(text, target_chars=15_000)

    # The high-signal lines must survive into key_moments.
    assert "Panopto upload" in result.key_moments
    assert "workaround" in result.key_moments


def test_first_and_last_segments_are_retained() -> None:
    """The first 10 % and last 10 % of the call are always kept."""
    from src.tools.storyboard.transcript_compactor import compact_transcript

    intro = "Speaker 1: Welcome to the call. We're discussing your AV setup."
    outro = "Speaker 2: Great, we'll send the proposal by Friday. Thanks."
    middle = "\n".join(
        [f"Speaker {i % 2 + 1}: filler middle content " * 20 for i in range(100)]
    )
    text = "\n".join([intro, middle, outro])

    result = compact_transcript(text, target_chars=12_000)

    assert "Welcome to the call" in result.full_context
    assert "send the proposal by Friday" in result.full_context


def test_compaction_falls_back_when_savings_below_threshold() -> None:
    """If extractive summarization can't reduce by ≥20 %, fall back to truncation."""
    from src.tools.storyboard.transcript_compactor import compact_transcript

    # All-high-signal transcript: every turn is pain language. Compactor
    # cannot drop turns without losing relevance, so it must fall back.
    high_signal_turn = (
        "Speaker 1: The Panopto upload fails, the encoder crashes, the "
        "recording is lost mid-lecture, our team is burning hours on "
        "workarounds — it is awful and we need help yesterday."
    )
    text = "\n".join([high_signal_turn] * 200)
    assert len(text) > 20_000

    result = compact_transcript(text, target_chars=10_000)

    # Either compacted to ≤ target or fallback flag set
    assert len(result.full_context) <= 10_000
    # Either way, result is structurally valid
    assert result.key_moments
    assert 0.0 < result.compaction_ratio <= 1.0


def test_compacted_transcript_is_pydantic_model() -> None:
    """Result is a CompactedTranscript Pydantic model with required fields."""
    from src.tools.storyboard.transcript_compactor import (
        CompactedTranscript,
        compact_transcript,
    )

    result = compact_transcript("Speaker 1: hi.", target_chars=1_000)

    assert isinstance(result, CompactedTranscript)
    assert hasattr(result, "key_moments")
    assert hasattr(result, "full_context")
    assert hasattr(result, "compaction_ratio")
    assert hasattr(result, "fallback_used")


@pytest.mark.parametrize(
    "phrase",
    [
        "we had to use",
        "we ended up",
        "workaround",
        "doesn't scale",
        "burning hours",
        "drops frames",
    ],
)
def test_pain_phrases_are_recognized(phrase: str) -> None:
    """Known pain phrases boost a turn's score above filler."""
    from src.tools.storyboard.transcript_compactor import score_turn

    pain = f"Speaker 1: Honestly {phrase} more than we want to admit."
    filler = "Speaker 1: yeah uh okay so um yeah."

    assert score_turn(pain) > score_turn(filler)
